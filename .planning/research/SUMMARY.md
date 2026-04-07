# Research Summary: v1.2 生产就绪与数据管理完善

**Domain:** Enterprise HR salary adjustment platform -- production readiness and data management
**Researched:** 2026-04-07
**Overall confidence:** HIGH

## Executive Summary

v1.2 is a 5-feature milestone focused on production hardening and data management gaps. The core stack finding: **Python 3.9 compatibility requires exactly 2 dependency version downgrades (numpy 2.0.2, Pillow 10.4.0) and 1 recommended upgrade (Celery 5.5.1)**. **However, source code changes ARE required:** although all files use `from __future__ import annotations`, SQLAlchemy 2.0 and Pydantic v2 both `eval()` type annotations at runtime, bypassing the `__future__` import. `Mapped[str | None]` (80+ occurrences in models) and `str | None` (361+ occurrences in schemas across 81 files) will crash on Python 3.9. All must be replaced with `Optional[X]`. No Python 3.10+ runtime features (match/case, ExceptionGroup, etc.) exist in the codebase.

The Celery activation path is clean: Celery 5.4.0 and Redis 5.2.1 are already in requirements.txt, and upgrading to Celery 5.5.1 adds native SQLAlchemy 2.0 and Pydantic 2.x task serialization support. The existing `scheduler/feishu_scheduler.py` already demonstrates the isolated-session pattern that Celery tasks need. The key risk is ensuring the Celery worker process starts alongside the FastAPI server in deployment.

For production deployment, the standard gunicorn + uvicorn worker pattern applies. gunicorn 23.0.0 should go in a separate `requirements-prod.txt`, not in the main requirements.txt. Worker count should equal CPU cores (async workers handle concurrency internally).

The Feishu bitable integration for eligibility import needs **no new packages**. The existing `FeishuService` already handles token management, paginated bitable search, field mapping, and retry -- extending it for eligibility data follows the established `sync_performance_records()` pattern.

**Critical deadline:** boto3's Python 3.9 support ends 2026-04-29 (3 weeks away). Python 3.9 should be treated as transitional; plan migration to 3.10+ within 6 months.

## Key Findings

**Stack:** 2 version downgrades (numpy, Pillow), 1 upgrade (Celery), 1 new prod-only dep (gunicorn). No new application libraries.
**Architecture:** One new package (`tasks/`), one new model column (`company`), service composition for rejection auto-delete, frontend tab additions.
**Critical pitfall:** numpy 2.2.1 and Pillow 11.0.0 will crash on import under Python 3.9 -- must be caught before any other work.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Python 3.9 Compatibility** - Foundational: pin numpy==2.0.2, Pillow==10.4.0, verify all deps
   - Addresses: Deployment target verification, dependency compat audit
   - Avoids: Discovering 3.9 incompatibilities after building features

2. **Celery+Redis Async Infrastructure** - Infrastructure that enables future phases
   - Addresses: Replace threading.Thread with proper task queue, upgrade Celery to 5.5.1
   - Avoids: Celery tasks importing FastAPI DI, async/sync mixing

3. **Employee Company Field** - Quick win, self-contained
   - Addresses: Company field on employee profile
   - Avoids: Schema drift (uses established Alembic migration pattern)

4. **Sharing Rejection Auto-Delete** - Self-contained service modification
   - Addresses: Requester file cleanup on rejection/expiry + pending status labels
   - Avoids: Orphaned files, breaking existing delete cascade

5. **Unified Eligibility Import Management** - Most complex, benefits from Celery
   - Addresses: Centralized eligibility data import (Excel + Feishu)
   - Avoids: Duplicating import logic (reuses ImportService + FeishuService)

**Phase ordering rationale:**
- Python 3.9 first because it validates the deployment target and fixes blocking dependency versions
- Celery second because it's infrastructure that Phase 5 can optionally use
- Company field third because it's trivial and provides quick progress
- Rejection auto-delete fourth because it's isolated and well-scoped
- Eligibility import last because it's the most complex frontend integration

**Research flags for phases:**
- Phase 1 (Python 3.9): Needs actual 3.9 interpreter testing -- numpy/Pillow downgrades verified via PyPI but runtime testing needed
- Phase 2 (Celery): Standard patterns, Celery 5.5.1 upgrade verified; deployment scripts need attention
- Phase 5 (Eligibility Import): UX design decisions needed for tab layout and Feishu sync integration

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All dependency versions verified via PyPI metadata; numpy/Pillow 3.9 breakage confirmed by official release notes |
| Features | HIGH | Backend endpoints largely exist; work is configuration and frontend |
| Architecture | HIGH | Follows established patterns (isolated session, service composition) |
| Pitfalls | HIGH | Python 3.9 dep matrix verified; Celery patterns well-documented |

## Gaps to Address

- Python 3.9 runtime testing cannot be done via code analysis alone -- needs actual interpreter
- boto3 Python 3.9 support ending 2026-04-29 -- evaluate impact on MinIO/S3 storage path
- Celery worker deployment strategy (systemd service? Docker compose?) not defined
- Pillow 10.4.0 may miss security patches available only in Pillow 11+ -- evaluate risk
- numpy 2.0.2 vs 2.2.1 API differences in pandas operations -- needs testing
