from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1.approvals import router as approvals_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.cycles import router as cycles_router
from backend.app.api.v1.dashboard import router as dashboard_router
from backend.app.api.v1.departments import router as departments_router
from backend.app.api.v1.employees import router as employees_router
from backend.app.api.v1.evaluations import router as evaluations_router
from backend.app.api.v1.files import router as files_router
from backend.app.api.v1.handbooks import router as handbooks_router
from backend.app.api.v1.imports import router as imports_router
from backend.app.api.v1.public import router as public_router
from backend.app.api.v1.salary import router as salary_router
from backend.app.api.v1.submissions import router as submissions_router
from backend.app.api.v1.system import router as system_router
from backend.app.api.v1.users import router as users_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(departments_router)
api_router.include_router(employees_router)
api_router.include_router(cycles_router)
api_router.include_router(submissions_router)
api_router.include_router(files_router)
api_router.include_router(evaluations_router)
api_router.include_router(salary_router)
api_router.include_router(approvals_router)
api_router.include_router(dashboard_router)
api_router.include_router(imports_router)
api_router.include_router(handbooks_router)
api_router.include_router(public_router)
