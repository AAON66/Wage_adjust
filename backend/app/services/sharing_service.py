from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.project_contributor import ProjectContributor
from backend.app.models.sharing_request import SharingRequest
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.uploaded_file import UploadedFile
from backend.app.utils.helpers import utc_now


class SharingService:
    def __init__(self, db: Session, settings: Settings | None = None):
        self.db = db
        self.settings = settings or get_settings()

    def _expire_stale_requests(self) -> None:
        """Lazily mark pending requests older than 72h as expired (D-17).

        Called by BOTH list_requests AND get_pending_count (review fix #6).
        Uses a subquery approach to avoid SQLAlchemy evaluator timezone issues.
        """
        cutoff = utc_now() - timedelta(hours=72)
        now = utc_now()
        stale_ids = list(self.db.scalars(
            select(SharingRequest.id)
            .where(SharingRequest.status == 'pending', SharingRequest.created_at < cutoff)
        ).all())
        if stale_ids:
            self.db.execute(
                update(SharingRequest)
                .where(SharingRequest.id.in_(stale_ids))
                .values(status='expired', resolved_at=now)
            )

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
        existing = self.db.scalars(
            select(SharingRequest)
            .join(UploadedFile, SharingRequest.requester_file_id == UploadedFile.id)
            .where(
                UploadedFile.content_hash == content_hash_hint,
                SharingRequest.original_submission_id == original_submission_id,
                SharingRequest.status.in_(['pending', 'approved', 'rejected']),
            )
        ).first()
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
        # D-15: check for existing non-expired request with same hash + same original submission
        existing = self.db.scalars(
            select(SharingRequest)
            .join(UploadedFile, SharingRequest.requester_file_id == UploadedFile.id)
            .where(
                UploadedFile.content_hash == requester_file.content_hash,
                SharingRequest.original_submission_id == original_submission_id,
                SharingRequest.status.in_(['pending', 'approved', 'rejected']),
            )
        ).first()
        if existing:
            raise ValueError('该文件已存在共享申请，无法重复发起。')

        sr = SharingRequest(
            requester_file_id=requester_file_id,
            original_file_id=original_file_id,
            requester_submission_id=requester_submission_id,
            original_submission_id=original_submission_id,
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
                .join(UploadedFile, SharingRequest.original_file_id == UploadedFile.id)
                .join(EmployeeSubmission, UploadedFile.submission_id == EmployeeSubmission.id)
                .where(EmployeeSubmission.employee_id == employee_id)
                .order_by(SharingRequest.created_at.desc())
            )
        else:
            query = (
                select(SharingRequest)
                .join(UploadedFile, SharingRequest.requester_file_id == UploadedFile.id)
                .join(EmployeeSubmission, UploadedFile.submission_id == EmployeeSubmission.id)
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
        """Reject: set status, resolved_at (D-14)."""
        sr = self.db.get(SharingRequest, request_id)
        if sr is None:
            raise ValueError('Sharing request not found')
        if sr.status != 'pending':
            raise ValueError(f'Cannot reject request with status {sr.status}')
        original_file = self.db.get(UploadedFile, sr.original_file_id)
        original_sub = self.db.get(EmployeeSubmission, original_file.submission_id)
        if original_sub.employee_id != rejector_employee_id:
            raise PermissionError('Only original uploader can reject')

        sr.status = 'rejected'
        sr.resolved_at = utc_now()
        self.db.flush()
        return sr

    def revoke_rejection(
        self,
        request_id: str,
        *,
        revoker_employee_id: str,
    ) -> SharingRequest:
        """Revoke a previously rejected sharing request: status back to pending."""
        sr = self.db.get(SharingRequest, request_id)
        if sr is None:
            raise ValueError('Sharing request not found')
        if sr.status != 'rejected':
            raise ValueError(f'Cannot revoke rejection with status {sr.status}')
        original_file = self.db.get(UploadedFile, sr.original_file_id)
        original_sub = self.db.get(EmployeeSubmission, original_file.submission_id)
        if original_sub.employee_id != revoker_employee_id:
            raise PermissionError('Only original uploader can revoke rejection')

        cycle = self.db.get(EvaluationCycle, original_sub.cycle_id)
        if cycle is not None and cycle.status == 'archived':
            raise ValueError('评估周期已下架，无法撤销拒绝')

        sr.status = 'pending'
        sr.resolved_at = None
        self.db.flush()
        return sr

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
            .join(UploadedFile, SharingRequest.original_file_id == UploadedFile.id)
            .join(EmployeeSubmission, UploadedFile.submission_id == EmployeeSubmission.id)
            .where(EmployeeSubmission.employee_id == employee_id, SharingRequest.status == 'pending')
        )
        return count or 0
