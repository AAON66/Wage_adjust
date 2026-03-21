from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import shutil

from openpyxl import Workbook
from sqlalchemy import delete

from backend.app.core.config import get_settings
from backend.app.core.database import create_session_factory
from backend.app.core.security import get_password_hash
from backend.app.core.storage import LocalStorageService
from backend.app.models import load_model_modules
from backend.app.models.approval import ApprovalRecord
from backend.app.models.audit_log import AuditLog
from backend.app.models.certification import Certification
from backend.app.models.dimension_score import DimensionScore
from backend.app.models.employee import Employee
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.evidence import EvidenceItem
from backend.app.models.import_job import ImportJob
from backend.app.models.salary_recommendation import SalaryRecommendation
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.uploaded_file import UploadedFile
from backend.app.models.user import User


PASSWORD = 'Password123!'
DIMENSION_WEIGHTS = {
    'TOOL': 0.25,
    'DEPTH': 0.20,
    'LEARN': 0.20,
    'SHARE': 0.15,
    'IMPACT': 0.20,
}


def make_workbook_bytes(employee_name: str, cycle_name: str, highlights: list[str]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = '评估材料'
    sheet['A1'] = '员工姓名'
    sheet['B1'] = employee_name
    sheet['A2'] = '评估周期'
    sheet['B2'] = cycle_name
    sheet['A4'] = '关键成果'
    for index, item in enumerate(highlights, start=5):
        sheet[f'A{index}'] = f'事项 {index - 4}'
        sheet[f'B{index}'] = item
    from io import BytesIO
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def seed_dimension_scores(db, evaluation_id: str, values: dict[str, tuple[float, str]]) -> None:
    for code, (raw_score, rationale) in values.items():
        weight = DIMENSION_WEIGHTS[code]
        db.add(
            DimensionScore(
                evaluation_id=evaluation_id,
                dimension_code=code,
                weight=weight,
                raw_score=raw_score,
                weighted_score=round(raw_score * weight, 2),
                rationale=rationale,
            )
        )


def main() -> None:
    load_model_modules()
    settings = get_settings()
    session_factory = create_session_factory(settings)
    storage = LocalStorageService(settings)
    base_dir = Path(settings.storage_base_dir).resolve()

    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    db = session_factory()
    try:
        for model in [
            ApprovalRecord,
            AuditLog,
            DimensionScore,
            EvidenceItem,
            UploadedFile,
            Certification,
            SalaryRecommendation,
            AIEvaluation,
            EmployeeSubmission,
            ImportJob,
            User,
            Employee,
            EvaluationCycle,
        ]:
            db.execute(delete(model))
        db.commit()

        now = datetime.now(UTC)

        users = {
            'admin': User(email='admin@zhdemo.com', hashed_password=get_password_hash(PASSWORD), role='admin'),
            'hrbp': User(email='hrbp@zhdemo.com', hashed_password=get_password_hash(PASSWORD), role='hrbp'),
            'manager': User(email='manager@zhdemo.com', hashed_password=get_password_hash(PASSWORD), role='manager'),
            'employee1': User(email='chenxi@zhdemo.com', hashed_password=get_password_hash(PASSWORD), role='employee'),
            'employee2': User(email='yutong@zhdemo.com', hashed_password=get_password_hash(PASSWORD), role='employee'),
            'employee3': User(email='haoran@zhdemo.com', hashed_password=get_password_hash(PASSWORD), role='employee'),
            'employee4': User(email='jingyi@zhdemo.com', hashed_password=get_password_hash(PASSWORD), role='employee'),
        }
        db.add_all(users.values())
        db.flush()

        manager_employee = Employee(employee_no='EMP-CN-001', name='周明远', department='研发中心', job_family='平台研发', job_level='M2', status='active')
        hrbp_employee = Employee(employee_no='EMP-CN-002', name='林书妍', department='人力资源', job_family='HRBP', job_level='P7', status='active')
        employees = {
            'chenxi': Employee(employee_no='EMP-CN-101', name='陈曦', department='研发中心', job_family='平台研发', job_level='P6', manager=manager_employee, status='active'),
            'yutong': Employee(employee_no='EMP-CN-102', name='李雨桐', department='产品中心', job_family='产品策划', job_level='P5', manager=manager_employee, status='active'),
            'haoran': Employee(employee_no='EMP-CN-103', name='王浩然', department='设计中心', job_family='体验设计', job_level='P5', manager=manager_employee, status='active'),
            'jingyi': Employee(employee_no='EMP-CN-104', name='赵静怡', department='研发中心', job_family='数据智能', job_level='P6', manager=manager_employee, status='active'),
        }
        db.add_all([manager_employee, hrbp_employee, *employees.values()])
        db.flush()

        cycles = {
            'spring': EvaluationCycle(name='2026 年春季调薪评估', review_period='2026 H1', budget_amount=Decimal('156000.00'), status='published'),
            'midyear': EvaluationCycle(name='2026 年年中人才盘点', review_period='2026 Midyear', budget_amount=Decimal('80000.00'), status='draft'),
        }
        db.add_all(cycles.values())
        db.flush()

        db.add_all([
            Certification(employee_id=employees['chenxi'].id, certification_type='AI 应用认证', certification_stage='高级', bonus_rate=0.03, issued_at=now - timedelta(days=90), expires_at=now + timedelta(days=275)),
            Certification(employee_id=employees['jingyi'].id, certification_type='数据分析认证', certification_stage='中级', bonus_rate=0.02, issued_at=now - timedelta(days=120), expires_at=now + timedelta(days=240)),
        ])

        submission_specs = [
            {
                'key': 'chenxi',
                'cycle': 'spring',
                'self_summary': '主导完成智能质检能力上线，推动客服场景问题识别准确率提升。',
                'manager_summary': '交付稳定，协作主动，具备带动团队沉淀方法论的能力。',
                'status': 'evaluated',
                'submitted_at': now - timedelta(days=9),
                'evaluation': {
                    'overall_score': 91,
                    'ai_level': 'Level 5',
                    'confidence_score': 0.93,
                    'explanation': '员工在 AI 工具使用深度、业务落地和团队分享方面表现突出，适合作为高潜重点培养对象。',
                    'status': 'confirmed',
                    'dimensions': {
                        'TOOL': (94, '熟练使用多类 AI 工具构建日常工作流。'),
                        'DEPTH': (92, '将 AI 能力嵌入关键业务流程并持续优化。'),
                        'LEARN': (90, '能快速学习新模型与新工具并形成可复用方案。'),
                        'SHARE': (88, '定期在团队内部做经验分享与操作培训。'),
                        'IMPACT': (93, '直接带来业务质量与效率双提升。'),
                    },
                },
                'salary': {
                    'current_salary': Decimal('52000.00'),
                    'recommended_ratio': 0.16,
                    'recommended_salary': Decimal('60320.00'),
                    'ai_multiplier': 1.22,
                    'certification_bonus': 0.03,
                    'final_adjustment_ratio': 0.16,
                    'status': 'approved',
                },
                'approval': [
                    ('用人经理审批', users['manager'], 'approved', '建议通过，符合高绩效高潜标准。', now - timedelta(days=5)),
                    ('HRBP 审批', users['hrbp'], 'approved', '预算可承接，建议进入发布环节。', now - timedelta(days=4)),
                ],
                'files': [
                    ('陈曦_春季评估材料.xlsx', 'xlsx', 'parsed', make_workbook_bytes('陈曦', '2026 年春季调薪评估', ['完成智能质检能力上线', '知识库助手月活提升 46%', '主导两次 AI 最佳实践分享'])),
                    ('陈曦_项目复盘.md', 'md', 'parsed', '## 项目复盘\n- 上线智能质检\n- 降低人工质检成本\n- 输出操作手册\n'.encode('utf-8')),
                ],
                'evidence': [
                    ('system_summary', '智能质检项目上线', '主导智能质检项目从方案到上线，准确率提升 18%，覆盖客服核心问题识别。', 0.94, {'theme': '业务成果', 'employee_name': '陈曦'}),
                    ('manager_note', '团队知识分享', '连续两个月组织 AI 工具分享会，帮助团队完成工作流标准化。', 0.88, {'theme': '知识沉淀', 'employee_name': '陈曦'}),
                ],
            },
            {
                'key': 'jingyi',
                'cycle': 'spring',
                'self_summary': '搭建数据分析自动化报表，缩短周报出具时间并提升异常识别效率。',
                'manager_summary': '对业务理解较深，具备较强的数据建模与 AI 分析能力。',
                'status': 'evaluated',
                'submitted_at': now - timedelta(days=7),
                'evaluation': {
                    'overall_score': 87,
                    'ai_level': 'Level 4',
                    'confidence_score': 0.89,
                    'explanation': '员工在数据分析和业务洞察方面表现稳定，适合进入重点提升序列。',
                    'status': 'reviewed',
                    'dimensions': {
                        'TOOL': (90, '能够熟练使用分析和自动化工具。'),
                        'DEPTH': (86, '分析结论能较好支撑业务动作。'),
                        'LEARN': (85, '学习节奏稳定，落地速度较快。'),
                        'SHARE': (82, '能够输出分析模板供团队复用。'),
                        'IMPACT': (88, '对经营数据质量改进贡献明显。'),
                    },
                },
                'salary': {
                    'current_salary': Decimal('48000.00'),
                    'recommended_ratio': 0.13,
                    'recommended_salary': Decimal('54240.00'),
                    'ai_multiplier': 1.15,
                    'certification_bonus': 0.02,
                    'final_adjustment_ratio': 0.13,
                    'status': 'pending_approval',
                },
                'approval': [
                    ('HRBP 审批', users['hrbp'], 'pending', '待确认部门预算平衡。', None),
                ],
                'files': [
                    ('赵静怡_分析成果.xlsx', 'xlsx', 'parsed', make_workbook_bytes('赵静怡', '2026 年春季调薪评估', ['经营周报自动化覆盖 8 个业务看板', '异常监控响应时长缩短 35%', '推动指标口径统一']))],
                'evidence': [
                    ('dashboard_extract', '自动化报表效率提升', '自动化报表上线后，周报制作时间从 4 小时缩短到 40 分钟。', 0.91, {'theme': '效率提升', 'employee_name': '赵静怡'}),
                ],
            },
            {
                'key': 'yutong',
                'cycle': 'spring',
                'self_summary': '推动 AI 助手在需求分析阶段落地，提升需求澄清效率和文档质量。',
                'manager_summary': '对流程优化有明显帮助，建议继续观察业务影响扩大情况。',
                'status': 'evaluated',
                'submitted_at': now - timedelta(days=6),
                'evaluation': {
                    'overall_score': 82,
                    'ai_level': 'Level 4',
                    'confidence_score': 0.84,
                    'explanation': '员工已形成稳定的 AI 需求分析工作流，但业务影响仍有进一步放大空间。',
                    'status': 'needs_review',
                    'dimensions': {
                        'TOOL': (86, '能稳定使用 AI 进行需求拆解与初稿撰写。'),
                        'DEPTH': (80, '落地深度较好，但跨团队推广仍有限。'),
                        'LEARN': (83, '能持续迭代提示词与流程。'),
                        'SHARE': (79, '已有分享，但沉淀仍待加强。'),
                        'IMPACT': (82, '需求质量和沟通效率均有提升。'),
                    },
                },
                'salary': {
                    'current_salary': Decimal('43000.00'),
                    'recommended_ratio': 0.09,
                    'recommended_salary': Decimal('46870.00'),
                    'ai_multiplier': 1.10,
                    'certification_bonus': 0.00,
                    'final_adjustment_ratio': 0.09,
                    'status': 'recommended',
                },
                'approval': [],
                'files': [
                    ('李雨桐_需求分析记录.md', 'md', 'parsed', '## 需求分析记录\n- 引入 AI 进行需求归纳\n- 输出统一 PRD 初稿模板\n'.encode('utf-8'))],
                'evidence': [
                    ('self_report', '需求澄清效率提升', '将需求澄清会议纪要自动整理为 PRD 草稿，需求讨论往返次数减少。', 0.83, {'theme': '流程优化', 'employee_name': '李雨桐'}),
                ],
            },
            {
                'key': 'haoran',
                'cycle': 'spring',
                'self_summary': '基于 AI 辅助完成多轮界面方案探索，提高交互稿输出效率。',
                'manager_summary': '方案产出速度提升明显，建议进一步加强对业务目标的绑定。',
                'status': 'submitted',
                'submitted_at': now - timedelta(days=4),
                'evaluation': None,
                'salary': None,
                'approval': [],
                'files': [
                    ('王浩然_设计探索.md', 'md', 'pending', '## 设计探索\n- 登录流程改版\n- 审批中心信息层级梳理\n'.encode('utf-8'))],
                'evidence': [],
            },
        ]

        for spec in submission_specs:
            submission = EmployeeSubmission(
                employee_id=employees[spec['key']].id,
                cycle_id=cycles[spec['cycle']].id,
                self_summary=spec['self_summary'],
                manager_summary=spec['manager_summary'],
                status=spec['status'],
                submitted_at=spec['submitted_at'],
            )
            db.add(submission)
            db.flush()

            for file_name, file_type, parse_status, content in spec['files']:
                storage_key = storage.save_bytes(submission_id=submission.id, file_name=file_name, content=content)
                db.add(
                    UploadedFile(
                        submission_id=submission.id,
                        file_name=file_name,
                        file_type=file_type,
                        storage_key=storage_key,
                        parse_status=parse_status,
                    )
                )

            for source_type, title, content, confidence_score, metadata_json in spec['evidence']:
                db.add(
                    EvidenceItem(
                        submission_id=submission.id,
                        source_type=source_type,
                        title=title,
                        content=content,
                        confidence_score=confidence_score,
                        metadata_json=metadata_json,
                    )
                )

            if spec['evaluation'] is None:
                continue

            evaluation_spec = spec['evaluation']
            evaluation = AIEvaluation(
                submission_id=submission.id,
                overall_score=evaluation_spec['overall_score'],
                ai_level=evaluation_spec['ai_level'],
                confidence_score=evaluation_spec['confidence_score'],
                explanation=evaluation_spec['explanation'],
                status=evaluation_spec['status'],
            )
            db.add(evaluation)
            db.flush()
            seed_dimension_scores(db, evaluation.id, evaluation_spec['dimensions'])

            salary_spec = spec['salary']
            if salary_spec is not None:
                recommendation = SalaryRecommendation(
                    evaluation_id=evaluation.id,
                    current_salary=salary_spec['current_salary'],
                    recommended_ratio=salary_spec['recommended_ratio'],
                    recommended_salary=salary_spec['recommended_salary'],
                    ai_multiplier=salary_spec['ai_multiplier'],
                    certification_bonus=salary_spec['certification_bonus'],
                    final_adjustment_ratio=salary_spec['final_adjustment_ratio'],
                    status=salary_spec['status'],
                )
                db.add(recommendation)
                db.flush()

                for step_name, approver, decision, comment, decided_at in spec['approval']:
                    db.add(
                        ApprovalRecord(
                            recommendation_id=recommendation.id,
                            approver_id=approver.id,
                            step_name=step_name,
                            decision=decision,
                            comment=comment,
                            decided_at=decided_at,
                        )
                    )

        db.add_all([
            ImportJob(
                file_name='员工信息导入_中文样例.csv',
                import_type='employees',
                status='completed',
                total_rows=24,
                success_rows=24,
                failed_rows=0,
                result_summary={'说明': '全部员工信息导入成功', '导入批次': '中文样例-001'},
            ),
            ImportJob(
                file_name='评估材料导入_异常样例.csv',
                import_type='submissions',
                status='failed',
                total_rows=12,
                success_rows=9,
                failed_rows=3,
                result_summary={'失败原因': '有 3 行缺少员工编号', '建议': '补全员工编号后重新上传'},
            ),
        ])

        db.add_all([
            AuditLog(operator_id=users['admin'].id, action='seed_demo_data', target_type='system', target_id='seed-cn-demo', detail={'说明': '重置旧测试数据并写入中文样例'}),
            AuditLog(operator_id=users['hrbp'].id, action='submit_approval', target_type='salary_recommendation', target_id='pending-approval-demo', detail={'说明': '创建待审批中文样例'}),
        ])

        db.commit()

        print('中文测试数据已重建完成。')
        print('默认登录密码: Password123!')
        print('管理员: admin@zhdemo.com')
        print('HRBP: hrbp@zhdemo.com')
        print('主管: manager@zhdemo.com')
        print('员工: chenxi@zhdemo.com / yutong@zhdemo.com / haoran@zhdemo.com / jingyi@zhdemo.com')
    finally:
        db.close()


if __name__ == '__main__':
    main()
