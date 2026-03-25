from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.certification import Certification
from backend.app.models.employee import Employee
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.user import User
from backend.app.services.llm_service import DeepSeekCallResult
from backend.app.services.salary_service import SalaryService


class StubSalaryExplanationLLM:
    def generate_salary_explanation(self, evaluation_context, salary_context, fallback_payload):  # noqa: ANN001, ANN201
        return DeepSeekCallResult(
            payload={
                'explanation': (
                    f"{evaluation_context['employee_name']}在本次评估中已达到当前岗位的 AI 应用要求，"
                    f"建议按 {salary_context['final_adjustment_ratio'] * 100:.2f}% 的比例进行调薪。"
                ),
                'budget_commentary': '建议与部门同批次调薪方案一起校准，整体预算压力可控。',
                'fairness_commentary': '该结果与同层级员工的能力表现和岗位贡献口径基本一致。',
                'risk_flags': ['建议关注后续持续产出稳定性'],
            },
            used_fallback=False,
            provider='deepseek',
        )


def build_context() -> object:
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'salary-{uuid4().hex}.db').as_posix()
    settings = Settings(
        database_url=f'sqlite+pysqlite:///{database_path}',
        deepseek_api_key='your_deepseek_api_key',
    )
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    return create_session_factory(settings)


def test_salary_service_recommend_simulate_and_lock() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        employee = Employee(
            employee_no='EMP-6001',
            name='Salary User',
            department='Engineering',
            job_family='Platform',
            job_level='P6',
            status='active',
        )
        cycle = EvaluationCycle(name='2026 Review', review_period='2026', budget_amount='15000.00', status='draft')
        user = User(email='hr@example.com', hashed_password='hash', role='admin')
        db.add_all([employee, cycle, user])
        db.commit()
        db.refresh(employee)
        db.refresh(cycle)
        db.refresh(user)

        submission = EmployeeSubmission(employee_id=employee.id, cycle_id=cycle.id, status='evaluated')
        db.add(submission)
        db.commit()
        db.refresh(submission)

        evaluation = AIEvaluation(
            submission_id=submission.id,
            overall_score=86,
            ai_level='Level 4',
            confidence_score=0.82,
            explanation='Confirmed evaluation.',
            status='confirmed',
        )
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)

        certification = Certification(
            employee_id=employee.id,
            certification_type='ai_skill',
            certification_stage='advanced',
            bonus_rate=0.02,
            issued_at=datetime.now(timezone.utc),
            expires_at=None,
        )
        db.add(certification)
        db.commit()

        service = SalaryService(
            db,
            settings=Settings(deepseek_api_key='your_deepseek_api_key'),
            llm_service=StubSalaryExplanationLLM(),
        )
        recommendation = service.recommend_salary(evaluation.id)
        assert recommendation.status == 'recommended'
        assert recommendation.final_adjustment_ratio > 0
        assert recommendation.explanation is not None
        assert '建议按' in recommendation.explanation
        assert '预算视角' in recommendation.explanation
        assert '公平性判断' in recommendation.explanation
        assert '风险提示' in recommendation.explanation

        updated = service.update_recommendation(recommendation.id, final_adjustment_ratio=0.18, status='adjusted')
        assert updated is not None
        assert updated.status == 'adjusted'
        assert '18.00%' in updated.explanation

        items, budget, total, over_budget = service.simulate_cycle(
            current_user=user,
            cycle_id=cycle.id,
            department=None,
            job_family=None,
            budget_amount=None,
        )
        assert len(items) == 1
        assert budget >= total
        assert over_budget is False

        locked = service.lock_recommendation(recommendation.id, user)
        assert locked is not None
        assert locked.status == 'locked'
        assert len(locked.approval_records) == 1
    finally:
        db.close()


def test_salary_service_returns_employee_history_in_cycle_order() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        employee = Employee(
            employee_no='EMP-6002',
            name='History User',
            department='Engineering',
            job_family='Platform',
            job_level='P5',
            status='active',
        )
        first_cycle = EvaluationCycle(name='2025 Annual', review_period='2025', budget_amount='5000.00', status='closed')
        second_cycle = EvaluationCycle(name='2026 Midyear', review_period='2026 H1', budget_amount='6000.00', status='active')
        db.add_all([employee, first_cycle, second_cycle])
        db.commit()
        db.refresh(employee)
        db.refresh(first_cycle)
        db.refresh(second_cycle)

        first_submission = EmployeeSubmission(employee_id=employee.id, cycle_id=first_cycle.id, status='evaluated')
        second_submission = EmployeeSubmission(employee_id=employee.id, cycle_id=second_cycle.id, status='evaluated')
        db.add_all([first_submission, second_submission])
        db.commit()
        db.refresh(first_submission)
        db.refresh(second_submission)

        first_evaluation = AIEvaluation(
            submission_id=first_submission.id,
            overall_score=78,
            ai_level='Level 3',
            confidence_score=0.76,
            explanation='First cycle confirmed evaluation.',
            status='confirmed',
        )
        second_evaluation = AIEvaluation(
            submission_id=second_submission.id,
            overall_score=88,
            ai_level='Level 4',
            confidence_score=0.83,
            explanation='Second cycle confirmed evaluation.',
            status='confirmed',
        )
        db.add_all([first_evaluation, second_evaluation])
        db.commit()
        db.refresh(first_evaluation)
        db.refresh(second_evaluation)

        service = SalaryService(db, settings=Settings(deepseek_api_key='your_deepseek_api_key'))
        first_recommendation = service.recommend_salary(first_evaluation.id)
        second_recommendation = service.recommend_salary(second_evaluation.id)
        service.update_recommendation(first_recommendation.id, final_adjustment_ratio=0.08, status='approved')
        service.update_recommendation(second_recommendation.id, final_adjustment_ratio=0.12, status='adjusted')

        history = service.get_salary_history_by_employee(employee.id)

        assert len(history) == 2
        assert [item['cycle_name'] for item in history] == ['2025 Annual', '2026 Midyear']
        assert history[0]['adjustment_amount'] == history[0]['recommended_salary'] - history[0]['current_salary']
        assert history[1]['final_adjustment_ratio'] == 0.12
        assert history[1]['ai_level'] == 'Level 4'
    finally:
        db.close()


def test_salary_service_backfills_legacy_english_explanation_to_chinese() -> None:
    session_factory = build_context()
    db = session_factory()
    try:
        employee = Employee(
            employee_no='EMP-6003',
            name='Legacy User',
            department='Engineering',
            job_family='Platform',
            job_level='P5',
            status='active',
        )
        cycle = EvaluationCycle(name='2026 Review', review_period='2026', budget_amount='6000.00', status='draft')
        db.add_all([employee, cycle])
        db.commit()
        db.refresh(employee)
        db.refresh(cycle)

        submission = EmployeeSubmission(employee_id=employee.id, cycle_id=cycle.id, status='evaluated')
        db.add(submission)
        db.commit()
        db.refresh(submission)

        evaluation = AIEvaluation(
            submission_id=submission.id,
            overall_score=84,
            ai_level='Level 4',
            confidence_score=0.80,
            explanation='Legacy evaluation.',
            status='confirmed',
        )
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)

        service = SalaryService(
            db,
            settings=Settings(deepseek_api_key='your_deepseek_api_key'),
            llm_service=StubSalaryExplanationLLM(),
        )
        recommendation = service.recommend_salary(evaluation.id)
        recommendation.explanation = 'Recommendation built from Level 4, overall score 84.00.'
        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)

        refreshed = service.get_recommendation(recommendation.id)

        assert refreshed is not None
        assert refreshed.explanation is not None
        assert '当前岗位的 AI 应用要求' in refreshed.explanation
        assert 'Recommendation built from' not in refreshed.explanation
    finally:
        db.close()
