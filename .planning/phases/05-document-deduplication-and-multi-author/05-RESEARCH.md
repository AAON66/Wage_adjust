# Phase 5: Document Deduplication and Multi-Author - Research

**Researched:** 2026-03-27
**Domain:** SQLAlchemy association tables, content hashing, weighted score attribution, FastAPI/React file upload flow
**Confidence:** HIGH

## Summary

Phase 5 introduces two tightly coupled features onto the existing `UploadedFile` / `EmployeeSubmission` / `EvidenceItem` stack. The first is duplicate detection: when an employee uploads a file, the system computes a SHA-256 hash of the file bytes and checks whether any existing `UploadedFile` row for the same employee already carries the same `(file_name, content_hash)` pair. If so, the upload is rejected with a 409 referencing the existing record. The second is multi-author attribution: a new `ProjectContributor` join table links a canonical "project" `UploadedFile` to multiple `EmployeeSubmission` rows with a `contribution_pct` decimal, and the evaluation engine applies that ratio when computing effective dimension scores for each contributor.

The key architectural insight is that the current model treats every `UploadedFile` as privately owned by one `submission_id`. Multi-author requires promoting a file to a shared resource: one canonical owner submission holds the file, and co-contributors reference it via the join table. The `EvaluationService` must be taught to load shared files from co-contributor records and scale their dimension scores by `contribution_pct / 100` before aggregation. The approval schema already carries `dimension_scores`; it needs a `contributors` list added.

**Primary recommendation:** Add `content_hash` to `UploadedFile`, add `ProjectContributor` association table, extend `FileService.upload_files` with a hash-check guard, extend `EvaluationService._build_employee_profile` to merge shared-project evidence with scaled scores, and surface contributors in the approval `ApprovalRecordRead` schema.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SUB-01 | Duplicate detection on (file_name + content hash) per employee; reject with reference to existing record | SHA-256 hash stored on `UploadedFile`; check in `FileService.upload_files` before `_create_file_record` |
| SUB-02 | Upload UI allows assigning co-contributors with contribution percentages summing to 100% | New `ProjectContributor` table; `POST /submissions/{id}/files` accepts contributor payload; frontend contributor picker |
| SUB-03 | Co-contributor sees shared project in their materials list; can upload supplementary files | `list_files` query joins `ProjectContributor`; supplementary files attach to contributor's own submission |
| SUB-04 | AI evaluation scales shared-project dimension scores by contributor's contribution_pct | `EvaluationService` loads contributor records; multiplies `weighted_score * (pct/100)` per shared file |
| SUB-05 | Approval screen shows all co-contributors and their percentages for shared projects | `ApprovalRecordRead` gains `contributors: list[ContributorRead]`; populated from `ProjectContributor` join |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.36 (already installed) | `ProjectContributor` association table, relationship loading | Already the ORM; `relationship()` with `secondary` handles M2M cleanly |
| Alembic | 1.14.0 (already installed) | Schema migration for new columns and table | Established as sole migration path since Phase 1 |
| hashlib | stdlib | SHA-256 content hashing | No dependency; `hashlib.sha256(content).hexdigest()` is the standard |
| Pydantic v2 | 2.10.3 (already installed) | New request/response schemas for contributors | Already used for all schemas |
| React + Axios | 18.3.1 / 1.8.4 (already installed) | Contributor picker UI, upload form extension | Already the frontend stack |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.3.5 (already installed) | Unit tests for hash check, contributor score scaling | All new service logic needs test coverage |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SHA-256 (hashlib) | MD5 or xxHash | SHA-256 is already used for prompt hashing (Phase 2); consistent, collision-resistant, no extra dep |
| Association table with `contribution_pct` | JSON column on `UploadedFile` | Normalized table is queryable, indexable, and enforces FK integrity |
| Scaling in `EvaluationService` | Scaling in `EvaluationEngine` | Engine is pure/stateless with no DB access; service layer is the right place for DB-aware attribution |

**Installation:** No new packages required. All dependencies already present.

---

## Architecture Patterns

### Recommended Project Structure additions
```
backend/app/models/
└── project_contributor.py   # new: ProjectContributor association table

backend/app/services/
└── file_service.py          # extend: hash check + contributor assignment
└── evaluation_service.py    # extend: shared-project score scaling

backend/app/schemas/
└── file.py                  # extend: ContributorRead, upload request with contributors
└── approval.py              # extend: ApprovalRecordRead.contributors

backend/app/api/v1/
└── files.py                 # extend: upload endpoint accepts contributor list

migrations/versions/
└── xxxx_phase05_content_hash_and_contributors.py

frontend/src/components/review/
└── ContributorPanel.tsx     # new: shows contributors in approval screen

frontend/src/components/employee/
└── ContributorPicker.tsx    # new: multi-select employee picker with pct inputs
```

### Pattern 1: Content Hash Deduplication

**What:** Store `content_hash = hashlib.sha256(content).hexdigest()` on every `UploadedFile` at write time. Before creating a new record, query for any existing file belonging to the same employee (via submission join) with matching `file_name` and `content_hash`. Reject with HTTP 409 if found.

**When to use:** Every upload path — `upload_files`, `import_github_file`, `replace_file`.

**Scope of deduplication:** Per-employee, not global. Two different employees can upload the same file. The check is: does THIS employee already have a file with this name+hash in any submission for the current cycle?

**Example:**
```python
# In FileService, before _create_file_record
import hashlib

def _compute_hash(self, content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def _check_duplicate(self, employee_id: str, file_name: str, content_hash: str) -> UploadedFile | None:
    # Join through EmployeeSubmission to reach employee
    query = (
        select(UploadedFile)
        .join(EmployeeSubmission, UploadedFile.submission_id == EmployeeSubmission.id)
        .where(
            EmployeeSubmission.employee_id == employee_id,
            UploadedFile.file_name == file_name,
            UploadedFile.content_hash == content_hash,
        )
    )
    return self.db.scalar(query)
```

**Rejection response:** HTTP 409 with `{"error": "duplicate_file", "existing_file_id": "<id>", "message": "..."}`.

### Pattern 2: ProjectContributor Association Table

**What:** A new table `project_contributors` links a canonical `uploaded_file_id` (the shared project file) to a `submission_id` (the co-contributor's submission) with a `contribution_pct` decimal. The file owner's own submission is NOT in this table — only co-contributors are.

**Schema:**
```python
class ProjectContributor(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "project_contributors"
    __table_args__ = (
        UniqueConstraint("uploaded_file_id", "submission_id"),
        CheckConstraint("contribution_pct > 0 AND contribution_pct <= 100"),
    )

    uploaded_file_id: Mapped[str] = mapped_column(
        ForeignKey("uploaded_files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("employee_submissions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contribution_pct: Mapped[float] = mapped_column(Float, nullable=False)

    uploaded_file = relationship("UploadedFile", back_populates="contributors")
    submission = relationship("EmployeeSubmission", back_populates="contributed_files")
```

**Contribution pct validation:** The sum of all contributor percentages plus the owner's implicit share must equal 100. This is enforced at the service layer, not DB layer (DB only enforces per-row range). The owner's share = 100 - sum(contributor pcts).

**Example upload request with contributors:**
```python
class ContributorInput(BaseModel):
    employee_id: str
    contribution_pct: float = Field(gt=0, le=100)

class FileUploadWithContributorsRequest(BaseModel):
    contributors: list[ContributorInput] = []
```

Since the upload endpoint uses `multipart/form-data`, contributors are passed as a JSON string field alongside the file bytes, parsed with `Form(...)` + `json.loads`.

### Pattern 3: Shared-Project Score Scaling in EvaluationService

**What:** When building evidence for a co-contributor's evaluation, load `ProjectContributor` records for that employee's submission. For each shared file, fetch its `EvidenceItem` rows (parsed from the owner's submission), then multiply each `weighted_score` by `contribution_pct / 100` before including them in the evaluation.

**Critical detail:** The `EvidenceItem` rows belong to the owner's `submission_id`. The co-contributor's evaluation must load them via the `ProjectContributor` join, not directly from their own submission. This means `EvaluationService.generate_evaluation` needs to merge two evidence sets: the employee's own evidence + scaled shared-project evidence.

**Score scaling:**
```python
# effective_weighted_score = original_weighted_score * (contribution_pct / 100)
# e.g. 80 points * 60% = 48 effective points
effective_score = round(dimension.weighted_score * (contributor.contribution_pct / 100), 2)
```

**Where to apply:** In `EvaluationService._build_evidence_for_submission()` (new helper), not in `EvaluationEngine` (which stays pure/stateless).

### Pattern 4: Co-Contributor Materials List (SUB-03)

**What:** `FileService.list_files(submission_id)` currently returns only files directly owned by that submission. It must also return files where the submission appears as a co-contributor in `project_contributors`, marked with a `is_shared: bool` flag and `owner_submission_id`.

**Supplementary files:** A co-contributor uploading additional files to a shared project attaches them to their OWN submission (normal upload flow). The shared project file itself is not duplicated — only the co-contributor's supplementary materials live in their submission.

### Pattern 5: Contributors in Approval Screen (SUB-05)

**What:** `ApprovalRecordRead` gains a `contributors` field. This is populated by joining through the submission's uploaded files → `project_contributors` → employee names. The approval service query must eagerly load this data.

**Schema addition:**
```python
class ContributorRead(BaseModel):
    employee_id: str
    employee_name: str
    contribution_pct: float
    uploaded_file_id: str
    file_name: str

# In ApprovalRecordRead:
contributors: list[ContributorRead] = []
```

### Anti-Patterns to Avoid

- **Global deduplication:** Don't reject uploads because another employee already uploaded the same file. Dedup is per-employee only.
- **Storing contributor pcts as JSON on UploadedFile:** Unqueryable, not FK-enforced, hard to update. Use the normalized join table.
- **Scaling in EvaluationEngine:** The engine is pure/stateless. DB-aware attribution belongs in the service layer.
- **Duplicating EvidenceItem rows for co-contributors:** Don't copy evidence rows into the co-contributor's submission. Reference the owner's evidence via the join table and scale at evaluation time.
- **Enforcing pct sum at DB level:** A CHECK constraint can't sum across rows. Enforce at service layer with a clear error message.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Content hashing | Custom rolling hash | `hashlib.sha256(content).hexdigest()` | stdlib, collision-resistant, already used in Phase 2 for prompt hashing |
| M2M with payload | JSON column or repeated FK columns | SQLAlchemy association table with extra columns | Queryable, indexable, FK-enforced, standard ORM pattern |
| Pct sum validation | DB trigger | Service-layer check before commit | SQLite has no triggers in this stack; service layer is the established validation point |
| Multipart + JSON contributors | Custom body parser | FastAPI `Form(...)` field containing JSON string | Standard FastAPI pattern for mixed multipart+JSON |

---

## Common Pitfalls

### Pitfall 1: Dedup scope too broad
**What goes wrong:** Rejecting uploads because a different employee already has the same file, blocking legitimate parallel submissions.
**Why it happens:** Hash check joins only on `content_hash` without filtering by `employee_id`.
**How to avoid:** Always join through `EmployeeSubmission.employee_id` in the dedup query.
**Warning signs:** Test where two employees upload the same template file — should succeed for both.

### Pitfall 2: Contribution percentages don't sum to 100
**What goes wrong:** Owner gets 100% credit AND contributors get their share, inflating total scores.
**Why it happens:** Owner's implicit share is not tracked; validation only checks contributor inputs.
**How to avoid:** Validate that `sum(contributor_pcts) < 100` (owner gets the remainder). If contributors are provided, owner_pct = 100 - sum(contributor_pcts). If no contributors, owner_pct = 100.
**Warning signs:** An employee with 60% contributor share on an 80-point project gets 48 points; the owner should get `80 * (100 - 60) / 100 = 32` points from that project.

### Pitfall 3: Co-contributor evaluation misses shared evidence
**What goes wrong:** Co-contributor's evaluation only uses their own uploaded files, ignoring the shared project entirely.
**Why it happens:** `generate_evaluation` only loads `submission.evidence_items` without checking `ProjectContributor`.
**How to avoid:** Add a `_load_shared_evidence(submission_id)` step that queries `ProjectContributor` and fetches the owner's `EvidenceItem` rows with scaling applied.
**Warning signs:** SUB-04 test: contributor with 60% share on 80-point project gets 80 points instead of 48.

### Pitfall 4: Alembic migration column default
**What goes wrong:** Adding `content_hash NOT NULL` to existing `uploaded_files` rows fails because existing rows have no hash.
**Why it happens:** SQLite `ALTER TABLE ADD COLUMN` with NOT NULL and no default is rejected.
**How to avoid:** Add column as nullable first, backfill with a sentinel value (e.g. empty string or `'legacy'`), then add NOT NULL constraint in a second migration step — or use `server_default=''` in the migration.
**Warning signs:** `alembic upgrade head` fails on existing DB with rows.

### Pitfall 5: Multipart form + JSON contributors
**What goes wrong:** FastAPI can't parse a JSON list from a `multipart/form-data` field directly.
**Why it happens:** Form fields are strings; Pydantic can't auto-coerce a JSON string to `list[ContributorInput]`.
**How to avoid:** Accept contributors as `contributors: str = Form(default='[]')` and parse with `json.loads(contributors)` inside the endpoint, then validate with Pydantic manually.
**Warning signs:** 422 validation error on upload with contributors.

### Pitfall 6: replace_file bypasses hash check
**What goes wrong:** An employee replaces a file with a duplicate, bypassing the dedup guard.
**Why it happens:** `replace_file` in `FileService` doesn't call the hash check.
**How to avoid:** Apply the same `_check_duplicate` guard in `replace_file`, excluding the file being replaced from the check.

---

## Code Examples

### SHA-256 hash on upload
```python
# Source: Python stdlib hashlib docs
import hashlib

content_hash = hashlib.sha256(content).hexdigest()
# Returns 64-char hex string, e.g. "a3f5..."
```

### SQLAlchemy association table with extra column
```python
# Source: SQLAlchemy 2.0 docs — association object pattern
from sqlalchemy import Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

class ProjectContributor(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "project_contributors"
    __table_args__ = (UniqueConstraint("uploaded_file_id", "submission_id"),)

    uploaded_file_id: Mapped[str] = mapped_column(
        ForeignKey("uploaded_files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("employee_submissions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contribution_pct: Mapped[float] = mapped_column(Float, nullable=False)
```

### Alembic migration — nullable-first pattern for existing rows
```python
# In migration upgrade():
op.add_column("uploaded_files", sa.Column("content_hash", sa.String(64), nullable=True))
op.execute("UPDATE uploaded_files SET content_hash = '' WHERE content_hash IS NULL")
op.alter_column("uploaded_files", "content_hash", nullable=False, server_default="")
op.create_index("ix_uploaded_files_content_hash", "uploaded_files", ["content_hash"])
```

### Contributor pct validation at service layer
```python
def _validate_contributor_pcts(self, contributors: list[ContributorInput]) -> None:
    total = sum(c.contribution_pct for c in contributors)
    if total >= 100:
        raise ValueError(
            f'合作者贡献比例之和为 {total}%，必须小于 100%（上传者保留剩余比例）。'
        )
    if any(c.contribution_pct <= 0 for c in contributors):
        raise ValueError('每位合作者的贡献比例必须大于 0%。')
```

### Score scaling in EvaluationService
```python
def _scale_evidence_by_contribution(
    self,
    evidence_items: list[EvidenceItem],
    contribution_pct: float,
) -> list[EvidenceItem]:
    """Return evidence items with confidence_score scaled by contribution ratio."""
    ratio = contribution_pct / 100.0
    scaled = []
    for item in evidence_items:
        # Shallow-copy the item with scaled confidence
        scaled_item = EvidenceItem(
            submission_id=item.submission_id,
            source_type=item.source_type,
            title=item.title,
            content=item.content,
            confidence_score=round(item.confidence_score * ratio, 4),
            metadata_json={**item.metadata_json, 'contribution_pct': contribution_pct},
        )
        scaled.append(scaled_item)
    return scaled
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No hash on UploadedFile | Add `content_hash` column | Phase 5 | Enables O(1) dedup check via index |
| Single-owner file | `ProjectContributor` join table | Phase 5 | Files become shared resources |
| Flat evidence list per submission | Merged own + scaled shared evidence | Phase 5 | Evaluation correctly attributes collaborative work |

---

## Open Questions

1. **Cycle scoping for dedup (SUB-01)**
   - What we know: The requirement says "same name + file content hash" — no explicit cycle scope mentioned.
   - What's unclear: Should dedup be per-cycle or across all cycles? An employee might legitimately resubmit the same project in a new cycle.
   - Recommendation: Scope dedup to the current cycle only. Join through `EmployeeSubmission.cycle_id` matching the target submission's cycle. This is the safest interpretation — cross-cycle resubmission is a valid scenario.

2. **Owner's contribution percentage display**
   - What we know: SUB-05 says "all co-contributors and their contribution percentages." The owner is not a co-contributor in the `project_contributors` table.
   - What's unclear: Should the owner also appear in the contributors list in the approval screen?
   - Recommendation: Yes — compute `owner_pct = 100 - sum(contributor_pcts)` and include the owner as the first entry in `contributors` list with their computed percentage.

3. **Supplementary file dedup (SUB-03)**
   - What we know: Co-contributors can upload supplementary files to a shared project.
   - What's unclear: Should supplementary files also be subject to the dedup check?
   - Recommendation: Yes — apply the same hash check to supplementary uploads. A co-contributor uploading the same supplementary file twice should be rejected.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 5 is purely code/schema changes. No new external services, CLIs, or runtimes required. All dependencies (SQLAlchemy, Alembic, hashlib, pytest) are already installed and verified in prior phases.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | none (pytest auto-discovers `backend/tests/`) |
| Quick run command | `pytest backend/tests/test_services/test_file_service.py backend/tests/test_api/test_file_api.py -x` |
| Full suite command | `pytest backend/tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SUB-01 | Duplicate upload rejected with 409 + existing_file_id | unit + API | `pytest backend/tests/test_services/test_file_service.py::test_duplicate_upload_rejected -x` | ❌ Wave 0 |
| SUB-01 | Same file by different employee is accepted | unit | `pytest backend/tests/test_services/test_file_service.py::test_duplicate_different_employee_allowed -x` | ❌ Wave 0 |
| SUB-02 | Contributors with pcts summing to ≥100 rejected | unit | `pytest backend/tests/test_services/test_file_service.py::test_contributor_pct_validation -x` | ❌ Wave 0 |
| SUB-02 | Valid contributors saved to project_contributors table | unit | `pytest backend/tests/test_services/test_file_service.py::test_contributors_saved -x` | ❌ Wave 0 |
| SUB-03 | Co-contributor sees shared file in list_files | unit | `pytest backend/tests/test_services/test_file_service.py::test_contributor_sees_shared_file -x` | ❌ Wave 0 |
| SUB-04 | Shared project score scaled by contribution_pct | unit | `pytest backend/tests/test_services/test_evaluation_service.py::test_shared_project_score_scaling -x` | ❌ Wave 0 |
| SUB-05 | ApprovalRecordRead includes contributors list | unit | `pytest backend/tests/test_services/test_approval_service.py::test_approval_shows_contributors -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/test_services/test_file_service.py backend/tests/test_services/test_evaluation_service.py -x`
- **Per wave merge:** `pytest backend/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_services/test_file_service.py` — covers SUB-01, SUB-02, SUB-03 (file service unit tests)
- [ ] `backend/tests/test_api/test_file_api.py` — extend existing file with SUB-01 API-level 409 test
- [ ] `backend/tests/test_services/test_evaluation_service.py` — extend with SUB-04 score scaling test
- [ ] `backend/tests/test_services/test_approval_service.py` — extend with SUB-05 contributors in approval

---

## Sources

### Primary (HIGH confidence)
- Python stdlib `hashlib` docs — SHA-256 hex digest pattern
- SQLAlchemy 2.0 docs — association object pattern with extra columns, `ondelete="CASCADE"`, `UniqueConstraint`
- Alembic docs — `batch_alter_table`, nullable-first column addition for SQLite compatibility
- FastAPI docs — `Form(...)` for multipart fields, mixing file upload with form data

### Secondary (MEDIUM confidence)
- Existing codebase patterns — `UUIDPrimaryKeyMixin`, `CreatedAtMixin`, `batch_alter_table` usage in Phase 1 migrations, `AccessScopeService` pattern for permission checks
- Phase 2 research — SHA-256 already used for `prompt_hash` on `DimensionScore`; consistent to use same algorithm here

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and in active use
- Architecture: HIGH — patterns derived directly from existing codebase conventions
- Pitfalls: HIGH — derived from reading actual model/service/migration code, not speculation
- Score scaling logic: HIGH — requirement is explicit (80 pts × 60% = 48 pts)

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable stack, no fast-moving dependencies)
