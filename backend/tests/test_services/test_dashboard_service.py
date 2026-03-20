from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.salary_recommendation import SalaryRecommendation
from backend.app.models.submission import EmployeeSubmission
from backend.app.services.dashboard_service import DashboardService


def build_context() -> object:
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'dashboard-{uuid4().hex}.db').as_posix()
    settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}')
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    return create_session_factory(settings)


def test_dashboard_service_returns_overview_distribution_and_heatmap() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        cycle = EvaluationCycle(name='2026 Dashboard', review_period='2026', budget_amount='10000.00', status='published')
        db.add(cycle)
        db.commit()
        db.refresh(cycle)

        employees = [
            Employee(employee_no='EMP-9001', name='Alice', department='Engineering', job_family='Platform', job_level='P6', status='active'),
            Employee(employee_no='EMP-9002', name='Bob', department='Engineering', job_family='Platform', job_level='P5', status='active'),
            Employee(employee_no='EMP-9003', name='Cara', department='Product', job_family='Product', job_level='P5', status='active'),
        ]
        db.add_all(employees)
        db.commit()
        for employee in employees:
            db.refresh(employee)

        submissions = [EmployeeSubmission(employee_id=employee.id, cycle_id=cycle.id, status='evaluated') for employee in employees]
        db.add_all(submissions)
        db.commit()
        for submission in submissions:
            db.refresh(submission)

        evaluations = [
            AIEvaluation(submission_id=submissions[0].id, overall_score=92, ai_level='Level 5', confidence_score=0.91, explanation='Top impact', status='confirmed'),
            AIEvaluation(submission_id=submissions[1].id, overall_score=84, ai_level='Level 4', confidence_score=0.82, explanation='Strong contributor', status='reviewed'),
            AIEvaluation(submission_id=submissions[2].id, overall_score=68, ai_level='Level 3', confidence_score=0.73, explanation='Solid outcome', status='needs_review'),
        ]
        db.add_all(evaluations)
        db.commit()
        for evaluation in evaluations:
            db.refresh(evaluation)

        recommendations = [
            SalaryRecommendation(evaluation_id=evaluations[0].id, current_salary='60000.00', recommended_ratio=0.15, recommended_salary='69000.00', ai_multiplier=1.18, certification_bonus=0.0, final_adjustment_ratio=0.15, status='approved'),
            SalaryRecommendation(evaluation_id=evaluations[1].id, current_salary='45000.00', recommended_ratio=0.10, recommended_salary='49500.00', ai_multiplier=1.13, certification_bonus=0.0, final_adjustment_ratio=0.10, status='pending_approval'),
            SalaryRecommendation(evaluation_id=evaluations[2].id, current_salary='45000.00', recommended_ratio=0.06, recommended_salary='47700.00', ai_multiplier=1.08, certification_bonus=0.0, final_adjustment_ratio=0.06, status='recommended'),
        ]
        db.add_all(recommendations)
        db.commit()

        service = DashboardService(db)
        overview = service.get_overview(cycle.id)
        assert overview[0]['value'] == '3'
        assert overview[2]['value'] == '2'
        assert overview[3]['value'] == '2'

        ai_distribution = service.get_ai_level_distribution(cycle.id)
        assert {item['label']: item['value'] for item in ai_distribution}['Level 4'] == 1
        assert {item['label']: item['value'] for item in ai_distribution}['Level 5'] == 1

        heatmap = service.get_heatmap(cycle.id)
        assert len(heatmap) == 2
        assert heatmap[0]['department'] == 'Engineering'

        roi_distribution = service.get_roi_distribution(cycle.id)
        assert sum(int(item['value']) for item in roi_distribution) == 3
    finally:
        db.close()
