# Phase 16: File Sharing Workflow - Research

**Researched:** 2026-04-04
**Domain:** File deduplication, sharing request workflow, contribution allocation
**Confidence:** HIGH

## Summary

Phase 16 transforms the existing file deduplication mechanism from a hard-block (raises ValueError) into a warn-and-continue flow, adding a sharing request approval workflow between file uploaders. The core changes span four areas: (1) backend FileService dedup logic change from reject to warn, (2) new SharingRequest model and SharingService, (3) new backend API endpoints for duplicate checking and sharing requests, (4) frontend hash-before-upload flow with modal warning and a new sharing requests page.

The existing codebase already has all the building blocks: `content_hash` is indexed on `UploadedFile`, `_compute_hash()` uses SHA-256, `ProjectContributor` handles contribution relationships, and `owner_contribution_pct` tracks share allocation. The primary challenge is refactoring 4 call sites in `FileService` that currently raise on duplicate, plus coordinating the frontend pre-upload hash check via Web Crypto API.

**Primary recommendation:** Build a new `SharingRequest` model and `SharingService` as a separate domain, modify `FileService._check_duplicate()` to match on `content_hash` only (drop `file_name`), and change the upload API from 409-reject to a two-step flow: check-duplicate endpoint returns warning info, then upload endpoint accepts a `force=true` flag.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Dedup uses content_hash (SHA-256) only, not filename. Current code uses filename+content_hash -- must change to content_hash only
- **D-02:** Frontend Modal warning: "此文件已由 [姓名] 于 [日期] 提交", options "继续上传" or "取消"
- **D-03:** Detection timing: after file selection, before upload button -- frontend computes hash, calls backend check endpoint
- **D-04:** Batch upload: per-file modal warning, user chooses continue or skip per file
- **D-05:** On "继续上传", file saved as new independent UploadedFile copy (not a reference to original)
- **D-06:** After confirming duplicate upload, system auto-creates sharing request to original uploader (no manual step)
- **D-07:** Sharing requests shown on dedicated page (new sidebar menu item), listing all pending/processed requests
- **D-08:** Approval page shows: requester name + filename + request date + suggested ratio + approve/reject buttons
- **D-09:** New SharingRequest model with fields: requester_file_id, original_file_id, requester_submission_id, original_submission_id, status(pending/approved/rejected/expired), proposed_pct, final_pct, created_at, resolved_at
- **D-10:** On approval, auto-create ProjectContributor linking requester as contributor; scores apply automatically
- **D-11:** Default suggested ratio: 50:50 (requester 50%, original uploader 50%)
- **D-12:** Original uploader can adjust ratio 1%-99% on approval
- **D-13:** After approval, EvidenceItem scores weighted by contribution_pct (reuse existing owner_contribution_pct mechanism)
- **D-14:** On rejection, requester's file stays as independent file, no sharing relationship
- **D-15:** Same content_hash + same original uploader = one request only; rejection is final, no re-apply
- **D-16:** Already-evaluated files allow sharing requests; new ratio applies on next evaluation, no retroactive adjustment
- **D-17:** 72h timeout via lazy detection: check created_at + 72h on each list query, update status to expired
- **D-18:** Timeout only changes status to expired, no notifications; both parties see in list
- **D-19:** After timeout, requester can re-upload same file to trigger new sharing request (timeout != rejection)

### Claude's Discretion
- Frontend hash computation library (Web Crypto API etc.)
- Sharing request API route design
- Modal UI component implementation
- Sidebar "共享申请" page routing and navigation integration
- SharingRequest database migration strategy

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SHARE-01 | Upload duplicate file: system warns but allows continue | FileService._check_duplicate() refactor + new check-duplicate API + frontend hash-before-upload + modal warning |
| SHARE-02 | After duplicate upload, auto-send sharing request to original uploader | SharingService.create_request() called from upload flow; SharingRequest model |
| SHARE-03 | Original uploader can approve/reject sharing requests in notification list | New sharing requests page + SharingService.approve/reject + API endpoints |
| SHARE-04 | Sharing request includes adjustable contribution ratio field | SharingRequest.proposed_pct/final_pct fields; approval endpoint accepts final_pct |
| SHARE-05 | 72h timeout auto-marks as expired | Lazy detection in SharingService.list_requests() checking created_at + 72h |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.0 | API endpoints for sharing requests | Already in use |
| SQLAlchemy | 2.0.36 | SharingRequest ORM model | Already in use |
| Alembic | 1.14.0 | Database migration for new table | Already in use |
| Pydantic | 2.10.3 | Request/response schemas | Already in use |
| React | 18.3.1 | Frontend sharing request page + modal | Already in use |
| Web Crypto API | Browser native | SHA-256 hash computation on frontend | Zero-dependency, available in all modern browsers |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| React Router DOM | 7.6.0 | New /sharing-requests route | Already in use |
| Axios | 1.8.4 | API calls for check-duplicate and sharing CRUD | Already in use |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Web Crypto API | crypto-js npm package | Adds dependency; Web Crypto is native, async, and performant -- use Web Crypto |
| Lazy timeout detection | Celery scheduled task | Over-engineered for this use case; lazy detection is simpler and matches D-17 |

**Installation:**
No new packages needed. All dependencies already installed.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── models/sharing_request.py       # New SharingRequest model
├── schemas/sharing.py              # New Pydantic schemas
├── services/sharing_service.py     # New SharingService
├── api/v1/sharing.py               # New sharing API router
frontend/src/
├── pages/SharingRequests.tsx        # New sharing requests page
├── services/sharingService.ts       # New API client
├── components/evaluation/
│   └── DuplicateWarningModal.tsx    # New modal component
```

### Pattern 1: Two-Step Upload with Pre-Check
**What:** Frontend computes SHA-256 hash of selected file, calls `/files/check-duplicate` with hash, receives duplicate info or "clean" response, shows modal if duplicate, then proceeds with normal upload endpoint.
**When to use:** Every file upload (local files and GitHub import).
**Example:**
```typescript
// Frontend: hash computation using Web Crypto API
async function computeSHA256(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}
```

### Pattern 2: Lazy Timeout Detection
**What:** On every query to list sharing requests, run an UPDATE that sets status='expired' for records where created_at + 72h < now AND status='pending'.
**When to use:** SharingService.list_requests() method.
**Example:**
```python
from datetime import timedelta
from backend.app.utils.helpers import utc_now

def _expire_stale_requests(self) -> None:
    cutoff = utc_now() - timedelta(hours=72)
    self.db.execute(
        update(SharingRequest)
        .where(SharingRequest.status == 'pending', SharingRequest.created_at < cutoff)
        .values(status='expired', resolved_at=utc_now())
    )
```

### Pattern 3: Service Layer with Session Injection
**What:** Follow existing `__init__(self, db: Session, settings: Settings | None = None)` pattern.
**When to use:** All new service classes in this project.

### Anti-Patterns to Avoid
- **Hard-coding status strings across files:** Use a single module-level constant or enum for SharingRequest statuses (`pending`, `approved`, `rejected`, `expired`).
- **Coupling SharingService into FileService:** Keep SharingService separate. The API layer orchestrates: call FileService.upload_files(), then call SharingService.create_request(). Do NOT import SharingService inside FileService.
- **Frontend polling for timeout:** D-17 explicitly requires lazy server-side detection. Do NOT implement client-side countdown or periodic polling.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SHA-256 in browser | Custom hash implementation | `crypto.subtle.digest('SHA-256', buffer)` | Native, fast, streaming-capable |
| File content comparison | Byte-by-byte comparison | SHA-256 content_hash comparison | Already indexed in DB, O(1) lookup |
| Request timeout scheduling | Celery/cron job | Lazy detection on query | D-17 specifies this approach; no infrastructure overhead |
| Contribution ratio enforcement | Manual percentage math | Reuse `owner_contribution_pct` + `ProjectContributor.contribution_pct` pattern | Already proven in existing contributor flow |

## Common Pitfalls

### Pitfall 1: Large File Hash Performance
**What goes wrong:** Computing SHA-256 of large files (up to 200MB) in the browser can freeze the UI thread.
**Why it happens:** `file.arrayBuffer()` loads entire file into memory, then `crypto.subtle.digest()` processes it synchronously within the async call.
**How to avoid:** For files under 50MB, direct `arrayBuffer()` + `digest()` is fine. For larger files, consider chunked reading with a `ReadableStream`. However, given the 200MB upload limit and modern browser capabilities, the simple approach should work for most cases.
**Warning signs:** Browser tab becomes unresponsive during file selection.

### Pitfall 2: Race Condition Between Check and Upload
**What goes wrong:** User A checks for duplicate (clean), User B uploads same file, User A uploads -- now duplicate exists without warning.
**Why it happens:** Time gap between check-duplicate call and actual upload.
**How to avoid:** This is acceptable per the design (D-05 says "save as new independent copy"). The sharing request will still be created post-upload. The check is a UX convenience, not a hard constraint.
**Warning signs:** N/A -- this is by design.

### Pitfall 3: _check_duplicate Refactor Breaks Existing Tests
**What goes wrong:** Removing `file_name` from `_check_duplicate()` WHERE clause changes behavior for all 4 call sites (upload_files, upload_file, import_github_file, replace_file).
**Why it happens:** Existing tests may assert on filename+hash combination.
**How to avoid:** Update `test_file_dedup.py` tests simultaneously. The refactored method should only match on `content_hash`.
**Warning signs:** Existing dedup tests fail after removing filename condition.

### Pitfall 4: Unique Constraint for One-Time Request (D-15)
**What goes wrong:** Without a unique constraint, multiple sharing requests can be created for the same file pair.
**Why it happens:** Concurrent uploads or retry logic.
**How to avoid:** Add a UniqueConstraint on `(requester_file_id, original_file_id)` in the SharingRequest model, plus application-level check before insert.
**Warning signs:** Duplicate SharingRequest rows in database.

### Pitfall 5: Expired Request vs Rejected Request Semantics (D-19)
**What goes wrong:** Treating expired the same as rejected blocks re-application.
**Why it happens:** Overly broad "already applied" check.
**How to avoid:** The D-15 "one request only" rule applies to rejection only. For expired requests, D-19 allows re-upload to trigger a new request. The uniqueness check must exclude expired status: only block if an existing request has status in ('pending', 'approved', 'rejected').
**Warning signs:** Users cannot re-apply after timeout.

## Code Examples

### Backend: SharingRequest Model
```python
# backend/app/models/sharing_request.py
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class SharingRequest(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = 'sharing_requests'
    __table_args__ = (
        UniqueConstraint(
            'requester_file_id',
            'original_file_id',
            name='uq_sharing_request_file_pair',
        ),
    )

    requester_file_id: Mapped[str] = mapped_column(
        ForeignKey('uploaded_files.id', ondelete='CASCADE'), nullable=False, index=True,
    )
    original_file_id: Mapped[str] = mapped_column(
        ForeignKey('uploaded_files.id', ondelete='CASCADE'), nullable=False, index=True,
    )
    requester_submission_id: Mapped[str] = mapped_column(
        ForeignKey('employee_submissions.id', ondelete='CASCADE'), nullable=False,
    )
    original_submission_id: Mapped[str] = mapped_column(
        ForeignKey('employee_submissions.id', ondelete='CASCADE'), nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default='pending',
    )  # pending, approved, rejected, expired
    proposed_pct: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    final_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

### Backend: Check Duplicate Endpoint
```python
# New endpoint in backend/app/api/v1/files.py (or sharing.py)
@router.post('/files/check-duplicate')
def check_file_duplicate(
    payload: CheckDuplicateRequest,  # { content_hash: str }
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CheckDuplicateResponse:
    existing = db.scalars(
        select(UploadedFile).where(UploadedFile.content_hash == payload.content_hash)
    ).first()
    if existing is None:
        return CheckDuplicateResponse(is_duplicate=False)
    # Resolve uploader info
    uploader_name = ''
    uploaded_at = ''
    if existing.submission and existing.submission.employee:
        uploader_name = existing.submission.employee.name or ''
        uploaded_at = existing.created_at.strftime('%Y-%m-%d') if existing.created_at else ''
    return CheckDuplicateResponse(
        is_duplicate=True,
        original_file_id=existing.id,
        uploader_name=uploader_name,
        uploaded_at=uploaded_at,
    )
```

### Frontend: SHA-256 Hash Computation
```typescript
// Utility function for frontend hash computation
export async function computeFileSHA256(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}
```

### Backend: Refactored _check_duplicate (D-01)
```python
# Change from filename+hash to hash-only
def _check_duplicate(
    self,
    content_hash: str,
    *,
    exclude_file_id: str | None = None,
) -> UploadedFile | None:
    query = select(UploadedFile).where(
        UploadedFile.content_hash == content_hash,
    )
    if exclude_file_id is not None:
        query = query.where(UploadedFile.id != exclude_file_id)
    return self.db.scalars(query).first()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| filename+hash dedup | hash-only dedup | Phase 16 | Files with same content but different names now detected as duplicates |
| Hard reject on duplicate | Warn + allow continue | Phase 16 | Users can upload duplicate files; sharing workflow initiated |
| No sharing requests | SharingRequest approval flow | Phase 16 | Original uploaders control contribution sharing |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | None (default discovery) |
| Quick run command | `python -m pytest backend/tests/test_submission/test_file_dedup.py -x` |
| Full suite command | `python -m pytest backend/tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SHARE-01 | Duplicate detection warns (not blocks), hash-only matching | unit | `python -m pytest backend/tests/test_submission/test_sharing_request.py::test_check_duplicate_hash_only -x` | Wave 0 |
| SHARE-02 | Auto-create sharing request on duplicate upload | unit | `python -m pytest backend/tests/test_submission/test_sharing_request.py::test_auto_create_sharing_request -x` | Wave 0 |
| SHARE-03 | Approve/reject sharing request | unit | `python -m pytest backend/tests/test_submission/test_sharing_request.py::test_approve_reject -x` | Wave 0 |
| SHARE-04 | Contribution ratio adjustable on approval | unit | `python -m pytest backend/tests/test_submission/test_sharing_request.py::test_ratio_adjustment -x` | Wave 0 |
| SHARE-05 | 72h lazy timeout detection | unit | `python -m pytest backend/tests/test_submission/test_sharing_request.py::test_lazy_expiry -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest backend/tests/test_submission/test_sharing_request.py -x`
- **Per wave merge:** `python -m pytest backend/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_submission/test_sharing_request.py` -- covers SHARE-01 through SHARE-05
- [ ] Update `backend/tests/test_submission/test_file_dedup.py` -- existing tests must be updated for hash-only matching

## Open Questions

1. **Duplicate check across submissions by same employee**
   - What we know: D-05 saves as independent copy. D-15 prevents re-apply after rejection for same content_hash + same original uploader.
   - What's unclear: Should a user be warned when re-uploading their own file (same employee, different submission/cycle)?
   - Recommendation: Exclude own files from duplicate check (filter by `UploadedFile.submission.employee_id != current_employee_id`). This avoids self-sharing requests which make no sense.

2. **GitHub import duplicate check timing**
   - What we know: D-03 specifies check at file selection. GitHub imports download first, then check.
   - What's unclear: Should GitHub imports also use the two-step check flow?
   - Recommendation: For GitHub imports, check after download but before save. If duplicate, return duplicate info in the response and let frontend show modal before confirming. This may require a separate two-step API for GitHub imports or accept that GitHub imports will use the existing post-upload sharing request creation without pre-warning.

## Sources

### Primary (HIGH confidence)
- `backend/app/services/file_service.py` -- current dedup implementation, all 4 call sites identified
- `backend/app/models/uploaded_file.py` -- UploadedFile schema with content_hash and owner_contribution_pct
- `backend/app/models/project_contributor.py` -- existing contributor model pattern
- `backend/app/api/v1/files.py` -- current API endpoints and 409 error handling
- `frontend/src/services/fileService.ts` -- current DuplicateFileException handling
- `frontend/src/components/evaluation/FileUploadPanel.tsx` -- current upload UI
- `frontend/src/pages/EvaluationDetail.tsx` -- handleFilesSelected flow
- `frontend/src/utils/roleAccess.ts` -- sidebar menu structure
- `backend/app/models/mixins.py` -- UUIDPrimaryKeyMixin, CreatedAtMixin patterns

### Secondary (MEDIUM confidence)
- Web Crypto API `crypto.subtle.digest` -- browser-native SHA-256, widely supported
- MDN Web Docs on SubtleCrypto.digest() -- standard API documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all tools already in project, no new dependencies
- Architecture: HIGH -- follows existing patterns exactly (service/model/schema/router)
- Pitfalls: HIGH -- identified from direct code inspection of 4 call sites and existing test suite

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable, internal project)
