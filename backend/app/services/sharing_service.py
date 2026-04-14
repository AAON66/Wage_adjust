from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.project_contributor import ProjectContributor
from backend.app.models.sharing_request import SharingRequest
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.uploaded_file import UploadedFile
from backend.app.services.file_service import FileService
from backend.app.utils.helpers import utc_now


class SharingService:
    def __init__(self, db: Session, settings: Settings | None = None):
        self.db = db
        self.settings = settings or get_settings()

    def _expire_stale_requests(self) -> None:
        """Lazily expire stale requests and clean up requester copies."""
        self.expire_and_cleanup_stale_requests()

    def _snapshot_requester_metadata(self, sr: SharingRequest) -> UploadedFile | None:
        requester_file = self.db.get(UploadedFile, sr.requester_file_id) if sr.requester_file_id else None
        if requester_file is not None:
            sr.requester_content_hash = requester_file.content_hash or sr.requester_content_hash
            sr.requester_file_name_snapshot = requester_file.file_name or sr.requester_file_name_snapshot
        return requester_file

    def _finalize_request_with_cleanup(self, sr: SharingRequest, *, status: str) -> SharingRequest:
        requester_file = self._snapshot_requester_metadata(sr)
        sr.status = status
        sr.resolved_at = utc_now()

        if requester_file is not None and sr.requester_file_id is not None:
            FileService(self.db, self.settings).delete_file_without_commit(sr.requester_file_id)

        sr.requester_file_id = None
        self.db.flush()
        return sr

    def expire_and_cleanup_stale_requests(self, *, submission_id: str | None = None) -> list[SharingRequest]:
        cutoff = utc_now() - timedelta(hours=72)
        query = (
            select(SharingRequest)
            .where(SharingRequest.status == 'pending', SharingRequest.created_at < cutoff)
            .order_by(SharingRequest.created_at.asc())
        )
        if submission_id is not None:
            query = query.where(SharingRequest.requester_submission_id == submission_id)

        stale_requests = list(self.db.scalars(query).all())
        for sr in stale_requests:
            self._finalize_request_with_cleanup(sr, status='expired')
        return stale_requests

    def _find_conflicting_request(
        self,
        *,
        original_submission_id: str,
        requester_content_hash: str,
    ) -> SharingRequest | None:
        return self.db.scalars(
            select(SharingRequest)
            .where(
                SharingRequest.requester_content_hash == requester_content_hash,
                SharingRequest.original_submission_id == original_submission_id,
                SharingRequest.status.in_(['pending', 'approved', 'rejected']),
            )
        ).first()

    def check_can_create_request(
        self,
        *,
        submission_id: str,
        original_submission_id: str,
        content_hash_hint: str,
    ) -> None:
        """Pre-check whether a sharing request can be created (D-15).

        Raises ValueError if a non-expired request already exists for the same
        content_hash + original submission. Called BEFORE upload so the file
        is not persisted when the request would be blocked.
        """
        existing = self._find_conflicting_request(
            original_submission_id=original_submission_id,
            requester_content_hash=content_hash_hint,
        )
        if existing:
            raise ValueError('该文件已存在共享申请，无法重复发起。')

    def create_request(
        self,
        *,
        requester_file_id: str,
        original_file_id: str,
        requester_submission_id: str,
        original_submission_id: str,
        proposed_pct: float = 50.0,
    ) -> SharingRequest:
        """Create sharing request atomically with upload (review fix #2).

        Per D-15, block if non-expired request exists for same content_hash + original uploader.
        Per D-19, expired status is excluded — allows re-request after expiry.
        """
        requester_file = self.db.get(UploadedFile, requester_file_id)
        if requester_file is None:
            raise ValueError('Requester file not found.')
        self.check_can_create_request(
            submission_id=requester_submission_id,
            original_submission_id=original_submission_id,
            content_hash_hint=requester_file.content_hash,
        )

        sr = SharingRequest(
            requester_file_id=requester_file_id,
            original_file_id=original_file_id,
            requester_submission_id=requester_submission_id,
            original_submission_id=original_submission_id,
            requester_content_hash=requester_file.content_hash,
            requester_file_name_snapshot=requester_file.file_name,
            proposed_pct=proposed_pct,
        )
        self.db.add(sr)
        self.db.flush()
        return sr

    def list_requests(self, *, employee_id: str, direction: str = 'incoming') -> list[SharingRequest]:
        """List requests with lazy expiry first (D-17)."""
        self._expire_stale_requests()
        if direction == 'incoming':
            query = (
                select(SharingRequest)
                .join(EmployeeSubmission, SharingRequest.original_submission_id == EmployeeSubmission.id)
                .where(EmployeeSubmission.employee_id == employee_id)
                .order_by(SharingRequest.created_at.desc())
            )
        else:
            query = (
                select(SharingRequest)
                .join(EmployeeSubmission, SharingRequest.requester_submission_id == EmployeeSubmission.id)
                .where(EmployeeSubmission.employee_id == employee_id)
                .order_by(SharingRequest.created_at.desc())
            )
        return list(self.db.scalars(query).all())

    def approve_request(
        self,
        request_id: str,
        *,
        approver_employee_id: str,
        final_pct: float,
    ) -> SharingRequest:
        """Approve: set status, final_pct, resolved_at. Create ProjectContributor (D-10). Update owner_contribution_pct (D-13)."""
        sr = self.db.get(SharingRequest, request_id)
        if sr is None:
            raise ValueError('Sharing request not found')
        if sr.status != 'pending':
            raise ValueError(f'Cannot approve request with status {sr.status}')
        # Verify approver owns the original file
        original_file = self.db.get(UploadedFile, sr.original_file_id)
        original_sub = self.db.get(EmployeeSubmission, original_file.submission_id)
        if original_sub.employee_id != approver_employee_id:
            raise PermissionError('Only original uploader can approve')

        sr.status = 'approved'
        sr.final_pct = final_pct
        sr.resolved_at = utc_now()

        # Create ProjectContributor for requester on original file (D-10)
        pc = ProjectContributor(
            uploaded_file_id=sr.original_file_id,
            submission_id=sr.requester_submission_id,
            contribution_pct=final_pct,
            status='accepted',
        )
        self.db.add(pc)

        # Update owner_contribution_pct (D-13)
        original_file.owner_contribution_pct = 100.0 - final_pct
        self.db.flush()
        return sr

    def reject_request(
        self,
        request_id: str,
        *,
        rejector_employee_id: str,
    ) -> SharingRequest:
        """Reject and atomically clean up the requester copy."""
        sr = self.db.get(SharingRequest, request_id)
        if sr is None:
            raise ValueError('Sharing request not found')
        if sr.status != 'pending':
            raise ValueError(f'Cannot reject request with status {sr.status}')
        original_file = self.db.get(UploadedFile, sr.original_file_id)
        original_sub = self.db.get(EmployeeSubmission, original_file.submission_id)
        if original_sub.employee_id != rejector_employee_id:
            raise PermissionError('Only original uploader can reject')
        return self._finalize_request_with_cleanup(sr, status='rejected')

    def revoke_rejection(
        self,
        request_id: str,
        *,
        revoker_employee_id: str,
    ) -> SharingRequest:
        """Rejected requests are terminal and cannot return to pending."""
        sr = self.db.get(SharingRequest, request_id)
        if sr is None:
            raise ValueError('Sharing request not found')
        original_file = self.db.get(UploadedFile, sr.original_file_id)
        original_sub = self.db.get(EmployeeSubmission, original_file.submission_id)
        if original_sub.employee_id != revoker_employee_id:
            raise PermissionError('Only original uploader can revoke rejection')
        raise ValueError('拒绝后的共享申请已是终态，不支持撤销。')

    def revoke_approval(
        self,
        request_id: str,
        *,
        revoker_employee_id: str,
    ) -> SharingRequest:
        """Revoke a previously approved sharing request: status back to pending,
        remove ProjectContributor, restore owner_contribution_pct."""
        sr = self.db.get(SharingRequest, request_id)
        if sr is None:
            raise ValueError('Sharing request not found')
        if sr.status != 'approved':
            raise ValueError(f'Cannot revoke request with status {sr.status}')
        original_file = self.db.get(UploadedFile, sr.original_file_id)
        original_sub = self.db.get(EmployeeSubmission, original_file.submission_id)
        if original_sub.employee_id != revoker_employee_id:
            raise PermissionError('Only original uploader can revoke approval')

        # Block revoke if the evaluation cycle has been archived (下架)
        cycle = self.db.get(EvaluationCycle, original_sub.cycle_id)
        if cycle is not None and cycle.status == 'archived':
            raise ValueError('评估周期已下架，无法撤销审批')

        # Remove the ProjectContributor that was created on approval
        pc = self.db.scalar(
            select(ProjectContributor).where(
                ProjectContributor.uploaded_file_id == sr.original_file_id,
                ProjectContributor.submission_id == sr.requester_submission_id,
            )
        )
        if pc is not None:
            self.db.delete(pc)

        # Restore owner_contribution_pct to 100 (no contributors remain from this request)
        # Recompute from remaining contributors to be safe
        remaining_total = self.db.scalar(
            select(func.coalesce(func.sum(ProjectContributor.contribution_pct), 0.0))
            .where(
                ProjectContributor.uploaded_file_id == sr.original_file_id,
                ProjectContributor.id != (pc.id if pc else ''),
            )
        ) or 0.0
        original_file.owner_contribution_pct = 100.0 - float(remaining_total)

        sr.status = 'pending'
        sr.final_pct = None
        sr.resolved_at = None
        self.db.flush()
        return sr

    def get_pending_count(self, *, employee_id: str) -> int:
        """Run lazy expiry before counting (review fix #6)."""
        self._expire_stale_requests()
        count = self.db.scalar(
            select(func.count(SharingRequest.id))
            .join(EmployeeSubmission, SharingRequest.original_submission_id == EmployeeSubmission.id)
            .where(EmployeeSubmission.employee_id == employee_id, SharingRequest.status == 'pending')
        )
        return count or 0
