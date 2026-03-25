from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, create_session_factory, init_database
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.evidence import EvidenceItem
from backend.app.models.submission import EmployeeSubmission
from backend.app.services.evaluation_service import EvaluationService
from backend.app.services.llm_service import DeepSeekCallResult


def build_context() -> tuple[Settings, object]:
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'evaluation-{uuid4().hex}.db').as_posix()
    settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}', deepseek_api_key='your_deepseek_api_key')
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    return settings, create_session_factory(settings)


def seed_submission(
    session_factory,
    *,
    department: str = 'Engineering',
    job_family: str = 'Platform',
) -> tuple[object, object, object]:
    db = session_factory()
    employee = Employee(
        employee_no=f'EMP-{uuid4().hex[:6]}',
        name='Eval User',
        department=department,
        job_family=job_family,
        job_level='P6',
        status='active',
    )
    cycle = EvaluationCycle(name='2026 Review', review_period='2026', budget_amount='3000.00', status='draft')
    db.add_all([employee, cycle])
    db.commit()
    db.refresh(employee)
    db.refresh(cycle)

    submission = EmployeeSubmission(employee_id=employee.id, cycle_id=cycle.id, status='reviewing')
    db.add(submission)
    db.commit()
    db.refresh(submission)

    db.add_all(
        [
            EvidenceItem(
                submission_id=submission.id,
                source_type='self_report',
                title='Impact',
                content='Delivered strong AI workflow improvements.',
                confidence_score=0.82,
                metadata_json={},
            ),
            EvidenceItem(
                submission_id=submission.id,
                source_type='file_parse',
                title='Docs',
                content='Evidence from uploaded files confirms repeated delivery gains.',
                confidence_score=0.77,
                metadata_json={},
            ),
        ]
    )
    db.commit()
    return db, employee, submission


def weighted_total_by_code(evaluation, overrides: dict[str, float] | None = None) -> float:
    overrides = overrides or {}
    total = 0.0
    for dimension in evaluation.dimension_scores:
        raw_score = overrides.get(dimension.dimension_code, dimension.raw_score)
        total += raw_score * dimension.weight
    return round(total, 2)


def test_evaluation_service_uses_weighted_dimension_review_total() -> None:
    settings, session_factory = build_context()
    db, _, submission = seed_submission(session_factory)
    try:
        service = EvaluationService(db, settings)
        evaluation = service.generate_evaluation(submission.id)

        reviewed = service.manual_review(
            evaluation.id,
            ai_level=None,
            overall_score=99,
            explanation='主管按维度复核。',
            dimension_updates=[{'dimension_code': 'IMPACT', 'raw_score': 92, 'rationale': 'Validated by reviewer.'}],
        )

        assert reviewed is not None
        expected_manager_score = weighted_total_by_code(reviewed, {'IMPACT': 92})
        assert abs(reviewed.manager_score - expected_manager_score) < 0.02
        assert abs(reviewed.overall_score - expected_manager_score) < 0.02
        assert abs(reviewed.score_gap - round(abs(evaluation.ai_overall_score - expected_manager_score), 2)) < 0.02
        impact_dimension = next(item for item in reviewed.dimension_scores if item.dimension_code == 'IMPACT')
        assert impact_dimension.ai_raw_score != impact_dimension.raw_score
        assert impact_dimension.ai_rationale
    finally:
        db.close()


def test_evaluation_service_auto_confirms_when_weighted_gap_is_small() -> None:
    settings, session_factory = build_context()
    db, _, submission = seed_submission(session_factory)
    try:
        service = EvaluationService(db, settings)
        evaluation = service.generate_evaluation(submission.id)
        impact_dimension = next(item for item in evaluation.dimension_scores if item.dimension_code == 'IMPACT')
        reviewed = service.manual_review(
            evaluation.id,
            ai_level=None,
            overall_score=None,
            explanation='主管评分与 AI 接近。',
            dimension_updates=[
                {
                    'dimension_code': 'IMPACT',
                    'raw_score': min(100, round(impact_dimension.raw_score + 6, 2)),
                    'rationale': 'Validated by reviewer.',
                }
            ],
        )

        assert reviewed is not None
        assert reviewed.status == 'confirmed'
        assert reviewed.hr_decision == 'not_required'
        assert reviewed.score_gap is not None and reviewed.score_gap <= 10
        assert reviewed.overall_score == reviewed.manager_score
    finally:
        db.close()


def test_evaluation_service_routes_large_gap_to_hr_review() -> None:
    settings, session_factory = build_context()
    db, _, submission = seed_submission(session_factory)
    try:
        service = EvaluationService(db, settings)
        evaluation = service.generate_evaluation(submission.id)
        reviewed = service.manual_review(
            evaluation.id,
            ai_level=None,
            overall_score=evaluation.ai_overall_score + 18,
            explanation='主管认为本次表现显著高于 AI 结果，需要 HR 审核。',
            dimension_updates=[],
        )
        assert reviewed is not None
        assert reviewed.status == 'pending_hr'
        assert reviewed.hr_decision == 'pending'
        assert reviewed.score_gap == 18.0

        returned = service.hr_review(
            evaluation.id,
            decision='returned',
            comment='请补充更多客观证据。',
            final_score=None,
        )
        assert returned is not None
        assert returned.status == 'returned'

        approved = service.hr_review(
            evaluation.id,
            decision='approved',
            comment='HR 同意，沿用主管复核总分。',
            final_score=None,
        )
        assert approved is not None
        assert approved.status == 'confirmed'
        assert approved.hr_decision == 'approved'
        assert approved.overall_score == reviewed.manager_score
    finally:
        db.close()


def test_evaluation_service_prefers_llm_dimension_scores_when_available() -> None:
    settings, session_factory = build_context()
    db = session_factory()
    try:
        employee = Employee(
            employee_no='EMP-4003',
            name='LLM Eval User',
            department='Engineering',
            job_family='Platform',
            job_level='P6',
            status='active',
        )
        cycle = EvaluationCycle(name='2026 Review', review_period='2026', budget_amount='3000.00', status='draft')
        db.add_all([employee, cycle])
        db.commit()
        db.refresh(employee)
        db.refresh(cycle)

        submission = EmployeeSubmission(employee_id=employee.id, cycle_id=cycle.id, status='reviewing')
        db.add(submission)
        db.commit()
        db.refresh(submission)

        db.add_all(
            [
                EvidenceItem(
                    submission_id=submission.id,
                    source_type='file_parse',
                    title='README',
                    content='Built AI workflow platform with reusable agents.',
                    confidence_score=0.91,
                    metadata_json={},
                ),
                EvidenceItem(
                    submission_id=submission.id,
                    source_type='code_artifact',
                    title='salary_service.py',
                    content='Implemented salary recommendation engine and review flow.',
                    confidence_score=0.88,
                    metadata_json={},
                ),
            ]
        )
        db.commit()

        class StubLLM:
            def generate_evaluation(self, employee_profile, evidence_items, fallback_payload):
                return DeepSeekCallResult(
                    payload={
                        'overall_score': 84,
                        'ai_level': 'Level 4',
                        'confidence_score': 0.86,
                        'explanation': 'LLM 结合岗位画像和项目材料判断，该员工在业务影响和知识沉淀方面表现突出。',
                        'needs_manual_review': False,
                        'dimensions': [
                            {'code': 'TOOL', 'label': 'AI 工具掌握度', 'weight': 0.20, 'raw_score': 80, 'weighted_score': 16, 'rationale': '从 README 和代码实现可见，员工能够熟练组合 AI 工作流与服务接口。'},
                            {'code': 'DEPTH', 'label': 'AI 应用深度', 'weight': 0.25, 'raw_score': 82, 'weighted_score': 20.5, 'rationale': 'salary_service.py 展示了从评估到调薪的链路设计，说明 AI 已进入核心业务流程。'},
                            {'code': 'LEARN', 'label': 'AI 学习速度', 'weight': 0.15, 'raw_score': 78, 'weighted_score': 11.7, 'rationale': '现有材料里关于持续学习的直接证据偏少，但从多模块实现可看出较快吸收能力。'},
                            {'code': 'SHARE', 'label': '知识分享', 'weight': 0.10, 'raw_score': 85, 'weighted_score': 8.5, 'rationale': 'README 体现了较完整的项目说明和知识沉淀，能帮助他人理解系统结构。'},
                            {'code': 'IMPACT', 'label': '业务影响力', 'weight': 0.30, 'raw_score': 88, 'weighted_score': 26.4, 'rationale': '项目直接覆盖评估和调薪流程，业务价值明确，对核心业务链路有实质推动。'},
                        ],
                    },
                    used_fallback=False,
                    provider='deepseek',
                )

        service = EvaluationService(db, settings, llm_service=StubLLM())
        evaluation = service.generate_evaluation(submission.id)
        assert evaluation.ai_level == 'Level 4'
        assert evaluation.overall_score > 80
        assert len(evaluation.dimension_scores) == 5
        assert any('README' in item.rationale for item in evaluation.dimension_scores)
        assert any(item.raw_score == 88 for item in evaluation.dimension_scores if item.dimension_code == 'IMPACT')
        assert next(item for item in evaluation.dimension_scores if item.dimension_code == 'DEPTH').weight == 0.25
    finally:
        db.close()


def test_evaluation_service_applies_department_specific_weights() -> None:
    settings, session_factory = build_context()
    db, employee, submission = seed_submission(session_factory, department='Sales', job_family='Commercial')
    try:
        service = EvaluationService(db, settings)
        evaluation = service.generate_evaluation(submission.id)
        impact_dimension = next(item for item in evaluation.dimension_scores if item.dimension_code == 'IMPACT')
        depth_dimension = next(item for item in evaluation.dimension_scores if item.dimension_code == 'DEPTH')

        assert employee.department == 'Sales'
        assert impact_dimension.weight == 0.45
        assert depth_dimension.weight == 0.1
        assert '销售与增长画像' in evaluation.explanation
    finally:
        db.close()


def test_evaluation_service_softens_abnormally_low_llm_dimension_scores() -> None:
    settings, session_factory = build_context()
    db = session_factory()
    try:
        employee = Employee(
            employee_no='EMP-5010',
            name='Stable User',
            department='Operations',
            job_family='Service Delivery',
            job_level='P5',
            status='active',
        )
        cycle = EvaluationCycle(name='2026 Review', review_period='2026', budget_amount='3000.00', status='draft')
        db.add_all([employee, cycle])
        db.commit()
        db.refresh(employee)
        db.refresh(cycle)

        submission = EmployeeSubmission(employee_id=employee.id, cycle_id=cycle.id, status='reviewing')
        db.add(submission)
        db.commit()
        db.refresh(submission)

        db.add_all(
            [
                EvidenceItem(
                    submission_id=submission.id,
                    source_type='self_report',
                    title='Weekly AI usage',
                    content='Used AI workflow every week to process tickets and summarize recurring issues.',
                    confidence_score=0.84,
                    metadata_json={'tags': ['workflow', 'ticket']},
                ),
                EvidenceItem(
                    submission_id=submission.id,
                    source_type='manager_review',
                    title='Manager validation',
                    content='The employee uses AI steadily and has clear improvements in response time and delivery quality.',
                    confidence_score=0.86,
                    metadata_json={'tags': ['delivery', 'quality']},
                ),
            ]
        )
        db.commit()

        class StubLLM:
            def generate_evaluation(self, employee_profile, evidence_items, fallback_payload):
                return DeepSeekCallResult(
                    payload={
                        'overall_score': 58,
                        'ai_level': 'Level 2',
                        'confidence_score': 0.82,
                        'explanation': 'LLM scored this too conservatively.',
                        'needs_manual_review': False,
                        'dimensions': [
                            {'code': 'TOOL', 'label': 'AI Tool Mastery', 'weight': 0.20, 'raw_score': 52, 'weighted_score': 10.4, 'rationale': 'LLM judged this conservatively.'},
                            {'code': 'DEPTH', 'label': 'AI Application Depth', 'weight': 0.15, 'raw_score': 54, 'weighted_score': 8.1, 'rationale': 'LLM judged this conservatively.'},
                            {'code': 'LEARN', 'label': 'AI Learning Speed', 'weight': 0.15, 'raw_score': 55, 'weighted_score': 8.25, 'rationale': 'LLM judged this conservatively.'},
                            {'code': 'SHARE', 'label': 'Knowledge Sharing', 'weight': 0.15, 'raw_score': 53, 'weighted_score': 7.95, 'rationale': 'LLM judged this conservatively.'},
                            {'code': 'IMPACT', 'label': 'Business Impact', 'weight': 0.35, 'raw_score': 56, 'weighted_score': 19.6, 'rationale': 'LLM judged this conservatively.'},
                        ],
                    },
                    used_fallback=False,
                    provider='deepseek',
                )

        service = EvaluationService(db, settings, llm_service=StubLLM())
        evaluation = service.generate_evaluation(submission.id)

        assert evaluation.overall_score >= 65
        assert max(item.raw_score for item in evaluation.dimension_scores) > 56
    finally:
        db.close()
