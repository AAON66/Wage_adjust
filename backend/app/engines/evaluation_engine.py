from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from backend.app.models.evidence import EvidenceItem
from backend.app.utils.prompt_safety import scan_for_prompt_manipulation


@dataclass(frozen=True)
class DimensionDefinition:
    code: str
    label: str
    weight: float
    keywords: tuple[str, ...]
    focus: str
    profile_keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class DepartmentProfile:
    code: str
    label: str
    match_keywords: tuple[str, ...]
    summary: str
    focus_points: tuple[str, ...]
    dimension_weights: Mapping[str, float]
    dimension_keywords: Mapping[str, tuple[str, ...]]
    dimension_focuses: Mapping[str, str]


DEPARTMENT_DIMENSION_EXAMPLES: dict[str, dict[str, dict[str, tuple[str, ...]]]] = {
    'GENERAL': {
        'TOOL': {
            'meets': (
                '能够把 AI 工具稳定用于本岗位的日常任务，输出质量和效率都有明确提升。',
            ),
            'strong': (
                '不仅会使用常见工具，还能根据任务场景组合提示词、工作流或多种工具，形成稳定打法。',
            ),
        },
        'DEPTH': {
            'meets': (
                'AI 已进入实际工作流程，不再停留在零散试用，能够支持关键任务交付。',
            ),
            'strong': (
                'AI 已嵌入复杂流程或跨团队协作场景，对关键流程的推进有明显支撑作用。',
            ),
        },
        'LEARN': {
            'meets': (
                '能够主动学习新工具、新方法，并较快转化到本岗位实践中。',
            ),
            'strong': (
                '学习速度快，能持续迭代使用方式，并把新能力快速变成稳定产出。',
            ),
        },
        'SHARE': {
            'meets': (
                '会沉淀基本文档、模板或经验，帮助团队理解并复用相关做法。',
            ),
            'strong': (
                '能够形成系统化的知识沉淀和推广材料，带动团队整体应用水平提升。',
            ),
        },
        'IMPACT': {
            'meets': (
                'AI 应用已经带来明确的效率、质量或交付改善，结果基本可验证。',
            ),
            'strong': (
                '业务价值清晰，不仅有提效，还对关键指标、核心交付或成本优化形成持续影响。',
            ),
        },
    },
    'ENGINEERING': {
        'TOOL': {
            'meets': (
                '能够把 AI 用在编码、调试、测试或脚本处理等研发日常工作中，并形成稳定效率收益。',
            ),
            'strong': (
                '能根据研发场景组合代码生成、排障、测试和自动化工具链，体现较强工程化使用能力。',
            ),
        },
        'DEPTH': {
            'meets': (
                'AI 已进入研发主流程，如开发、测试、发布或问题处理，而非只停留在零散辅助。',
            ),
            'strong': (
                'AI 已嵌入架构设计、发布链路或稳定性治理，对核心工程流程产生持续影响。',
            ),
        },
        'LEARN': {
            'meets': (
                '能够跟进模型、框架或工具更新，并较快转化成代码或工程实践。',
            ),
            'strong': (
                '不仅学习快，还能通过实验、评估和迭代快速验证新方案并落入研发流程。',
            ),
        },
        'SHARE': {
            'meets': (
                '会通过 README、方案文档或开发规范沉淀 AI 实践，便于团队复用。',
            ),
            'strong': (
                '能够形成工程规范、最佳实践或分享材料，带动团队整体研发效率提升。',
            ),
        },
        'IMPACT': {
            'meets': (
                '对研发效率、交付节奏或代码质量有可感知提升，价值较明确。',
            ),
            'strong': (
                '在交付周期、稳定性、缺陷率或自动化率等核心工程指标上形成明显改善。',
            ),
        },
    },
    'PRODUCT': {
        'TOOL': {
            'meets': (
                '能够把 AI 用在需求分析、用户洞察、原型或方案整理中，帮助提升产出质量。',
            ),
            'strong': (
                '能熟练组合调研、分析和原型工具，显著提升产品方案形成效率和质量。',
            ),
        },
        'DEPTH': {
            'meets': (
                'AI 已进入需求定义、方案设计或实验验证流程，对关键产品环节有实际支撑。',
            ),
            'strong': (
                'AI 已深度融入产品闭环，从洞察、方案到验证都能看到持续使用痕迹。',
            ),
        },
        'LEARN': {
            'meets': (
                '能持续吸收用户反馈、竞品信息和新方法，并较快转成产品动作。',
            ),
            'strong': (
                '学习和迭代速度快，能快速把新认知转化成更优的产品方案和决策依据。',
            ),
        },
        'SHARE': {
            'meets': (
                '会沉淀 PRD、分析模板或对齐材料，帮助团队复用 AI 相关方法。',
            ),
            'strong': (
                '能够输出高质量模板和共识材料，帮助跨团队高效理解并复用产品方法。',
            ),
        },
        'IMPACT': {
            'meets': (
                '对用户体验、转化效率或项目推进带来明确改善，结果较为合理。',
            ),
            'strong': (
                '在转化、留存、满意度或关键项目推进上形成明显的业务价值。',
            ),
        },
    },
    'SALES': {
        'TOOL': {
            'meets': (
                '能够把 AI 用在客户分析、方案准备、线索整理或销售沟通中，提升跟进效率。',
            ),
            'strong': (
                '能把 AI 稳定用于客户画像、话术优化和商机推进，体现较强销售打法意识。',
            ),
        },
        'DEPTH': {
            'meets': (
                'AI 已进入线索管理、方案输出或销售流程，而不是只偶尔生成文案。',
            ),
            'strong': (
                'AI 已嵌入客户旅程、投标或销售预测等关键流程，形成持续支撑。',
            ),
        },
        'LEARN': {
            'meets': (
                '能够跟进市场、产品和客户变化，并快速调整使用 AI 的销售方法。',
            ),
            'strong': (
                '学习速度快，能把外部市场信息和客户反馈迅速转化成新的成交打法。',
            ),
        },
        'SHARE': {
            'meets': (
                '会沉淀案例、话术或销售模板，帮助团队更快复制有效做法。',
            ),
            'strong': (
                '能够形成高质量销售手册和案例库，对团队复制和培训价值明显。',
            ),
        },
        'IMPACT': {
            'meets': (
                'AI 应用对客户跟进、转化效率或签约结果有明确帮助，业务价值可感知。',
            ),
            'strong': (
                '在签约、回款、转化率或重点商机推进上形成明显结果，是高价值业务贡献。',
            ),
        },
    },
    'OPERATIONS': {
        'TOOL': {
            'meets': (
                '能够把 AI 用在工单处理、知识检索、流程执行或交付准备中，提升日常运营效率。',
            ),
            'strong': (
                '能稳定把 AI 用进工单、知识库和流程自动化，说明工具使用已进入运营主场景。',
            ),
        },
        'DEPTH': {
            'meets': (
                'AI 已进入交付执行或问题闭环流程，不再只是零散辅助。',
            ),
            'strong': (
                'AI 能支撑跨角色协作、流程编排和服务闭环，对运营交付链路帮助明显。',
            ),
        },
        'LEARN': {
            'meets': (
                '能够根据问题复盘和现场反馈持续调整 AI 用法，学习转化较及时。',
            ),
            'strong': (
                '能快速把复盘经验沉淀到流程和工具中，体现较强的运营迭代能力。',
            ),
        },
        'SHARE': {
            'meets': (
                '会沉淀 FAQ、作业指引或操作手册，帮助团队标准化处理问题。',
            ),
            'strong': (
                '能够输出系统化 SOP 和培训资料，显著提升团队处理一致性和效率。',
            ),
        },
        'IMPACT': {
            'meets': (
                '对响应时效、处理效率、交付质量或服务体验带来明确改善。',
            ),
            'strong': (
                '在履约质量、一次解决率或客户满意度等关键指标上形成持续提升。',
            ),
        },
    },
    'CORP_SUPPORT': {
        'TOOL': {
            'meets': (
                '能够把 AI 用在分析、审批、查询或标准化处理上，提升职能工作效率。',
            ),
            'strong': (
                '能稳定把 AI 用进制度执行、分析支持和标准模板处理，体现较强职能适配度。',
            ),
        },
        'DEPTH': {
            'meets': (
                'AI 已进入制度执行、分析判断或流程处理，而非停留在简单问答层面。',
            ),
            'strong': (
                'AI 能支撑合规、预算、风险控制或跨部门服务等关键职能链路。',
            ),
        },
        'LEARN': {
            'meets': (
                '能够跟进政策、制度或行业变化，并较快把新要求转化到工作实践中。',
            ),
            'strong': (
                '学习转化速度快，能持续把新制度、新政策和外部经验融入工作方法。',
            ),
        },
        'SHARE': {
            'meets': (
                '会沉淀模板、制度指引或培训材料，帮助相关团队更高效协作。',
            ),
            'strong': (
                '能够通过制度宣导、标准模板和培训扩大全组织的复用和合规一致性。',
            ),
        },
        'IMPACT': {
            'meets': (
                '对时效、准确率、成本控制或内部服务体验带来明确提升。',
            ),
            'strong': (
                '在风险下降、预算控制、准确率提升或组织赋能方面形成明显价值。',
            ),
        },
    },
}


@dataclass
class DimensionSignals:
    definition: DimensionDefinition
    matched_evidence_count: int
    matched_source_count: int
    distinct_keyword_count: int
    total_keyword_hits: int
    profile_keyword_count: int
    average_confidence: float
    average_reliability: float
    average_text_richness: float
    suspicious_count: int
    top_titles: list[str]
    matched_keywords: list[str]
    matched_profile_keywords: list[str]


BASE_DIMENSIONS: tuple[DimensionDefinition, ...] = (
    DimensionDefinition(
        code='TOOL',
        label='AI 工具掌握度',
        weight=0.15,
        keywords=('tooling', 'automation', 'agent', 'prompt', 'workflow', 'copilot', 'llm', '模型', '提示词', '智能体', '自动化', '工作流'),
        focus='是否能把合适的 AI 工具、工作流和方法稳定用于本岗位。',
    ),
    DimensionDefinition(
        code='DEPTH',
        label='AI 应用深度',
        weight=0.15,
        keywords=('architecture', 'deployment', 'integration', 'design', 'analysis', 'complex', '架构', '部署', '集成', '设计', '分析', '复杂'),
        focus='是否把 AI 用到核心流程、复杂场景或跨系统协同，而不是停留在浅层试用。',
    ),
    DimensionDefinition(
        code='LEARN',
        label='AI 学习速度',
        weight=0.20,
        keywords=('learn', 'training', 'course', 'study', 'certification', 'mentor', '学习', '培训', '课程', '研究', '认证', '辅导'),
        focus='是否持续学习 AI 能力，并能快速吸收新方法、新模型和新工具。',
    ),
    DimensionDefinition(
        code='SHARE',
        label='知识分享',
        weight=0.20,
        keywords=('share', 'document', 'playbook', 'workshop', 'guide', 'knowledge', '分享', '文档', '手册', '宣讲', '指南', '知识'),
        focus='是否把 AI 实践沉淀为团队可复用的方法、文档、案例或培训材料。',
    ),
    DimensionDefinition(
        code='IMPACT',
        label='业务影响力',
        weight=0.30,
        keywords=('impact', 'save', 'efficiency', 'delivery', 'launch', 'roi', 'revenue', '影响', '降本', '提效', '交付', '上线', '收益'),
        focus='是否在业务结果、效率、质量、收入、成本或风险控制上形成可验证价值。',
    ),
)

DIMENSIONS = BASE_DIMENSIONS

DEFAULT_PROFILE = DepartmentProfile(
    code='GENERAL',
    label='通用岗位画像',
    match_keywords=(),
    summary='未命中明确部门画像，采用通用岗位标准，综合判断工具掌握、落地深度、学习成长、知识沉淀和业务结果。',
    focus_points=(
        '优先看真实材料是否说明 AI 已经被稳定使用。',
        '重点确认是否产生了可验证的效率、质量或业务价值。',
    ),
    dimension_weights={item.code: item.weight for item in BASE_DIMENSIONS},
    dimension_keywords={},
    dimension_focuses={item.code: item.focus for item in BASE_DIMENSIONS},
)

DEPARTMENT_PROFILES: tuple[DepartmentProfile, ...] = (
    DepartmentProfile(
        code='ENGINEERING',
        label='研发与技术画像',
        match_keywords=(
            'engineering',
            'platform',
            'backend',
            'frontend',
            'fullstack',
            'infra',
            'infrastructure',
            'devops',
            'tech',
            'technology',
            '研发',
            '技术',
            '平台',
            '开发',
            '架构',
            '算法',
            '测试',
            '运维',
            '数据',
        ),
        summary='重点看 AI 是否进入研发交付链路、系统架构、测试自动化、稳定性治理和工程效率提升。',
        focus_points=(
            '更看重 AI 是否被用在代码、架构、测试、发布、排障和工程流程中。',
            '业务影响不仅是产出数量，还包括质量、稳定性、交付效率和复用能力。',
        ),
        dimension_weights={'TOOL': 0.20, 'DEPTH': 0.25, 'LEARN': 0.15, 'SHARE': 0.10, 'IMPACT': 0.30},
        dimension_keywords={
            'TOOL': ('sdk', 'api', 'debug', 'copilot', '脚本', '代码生成', '接口调试', '测试生成', '自动化测试'),
            'DEPTH': ('architecture', 'service', 'pipeline', 'deployment', 'observability', 'integration', '微服务', '部署', '监控', '链路', '稳定性'),
            'LEARN': ('benchmark', 'prototype', 'poc', 'experiment', 'eval', '调研', '试验', '基准', '迭代'),
            'SHARE': ('readme', 'wiki', 'guide', 'playbook', '复盘', '规范', '分享会', '最佳实践'),
            'IMPACT': ('研发效率', '交付周期', '缺陷率', '故障恢复', '自动化率', '上线质量', '稳定性', '成本优化'),
        },
        dimension_focuses={
            'TOOL': '重点看是否会选型、组合并稳定使用适合研发岗位的 AI 工具链。',
            'DEPTH': '重点看 AI 是否进入架构、编码、测试、发布、监控或排障等核心工程环节。',
            'LEARN': '重点看是否能快速试验新方法，并把实验结果转成工程实践。',
            'SHARE': '重点看是否沉淀代码规范、README、方案文档或团队实践。',
            'IMPACT': '重点看对研发效率、质量、稳定性和交付结果的实际改善。',
        },
    ),
    DepartmentProfile(
        code='PRODUCT',
        label='产品与设计画像',
        match_keywords=('product', 'pm', 'design', 'ux', 'ui', '产品', '设计', '用户研究', '体验', '交互', '策划'),
        summary='重点看 AI 是否用于需求分析、方案设计、用户洞察、实验验证和跨团队推进。',
        focus_points=(
            '更看重 AI 是否帮助形成更高质量的需求、方案和用户洞察。',
            '业务影响体现为转化、留存、满意度、交付节奏和决策质量。',
        ),
        dimension_weights={'TOOL': 0.15, 'DEPTH': 0.20, 'LEARN': 0.15, 'SHARE': 0.15, 'IMPACT': 0.35},
        dimension_keywords={
            'TOOL': ('prototype', 'analysis', 'workflow', 'notebook', '原型', '用户洞察', '提示词模板', '调研工具'),
            'DEPTH': ('roadmap', 'requirements', 'funnel', 'journey', 'experiment design', '需求', '场景', '漏斗', '闭环', '流程重塑'),
            'LEARN': ('user research', 'competitive analysis', 'ab test', '洞察', '竞品', '复盘', '迭代'),
            'SHARE': ('prd', 'spec', 'knowledge base', '对齐会', '培训', '方案模板', '共识文档'),
            'IMPACT': ('adoption', 'conversion', 'retention', 'gmv', '活跃', '转化', '留存', '满意度'),
        },
        dimension_focuses={
            'TOOL': '重点看是否能把 AI 用于调研、原型、分析和方案协作。',
            'DEPTH': '重点看是否把 AI 用进需求定义、实验设计和产品闭环。',
            'LEARN': '重点看是否持续吸收用户洞察、竞品信息和新方法。',
            'SHARE': '重点看是否形成可复用的产品文档、模板和共识材料。',
            'IMPACT': '重点看对用户价值、转化、留存和项目推进的影响。',
        },
    ),
    DepartmentProfile(
        code='SALES',
        label='销售与增长画像',
        match_keywords=('sales', 'commercial', 'bd', 'marketing', 'growth', 'channel', '客户成功', '销售', '市场', '增长', '渠道', '商务'),
        summary='重点看 AI 是否提升客户洞察、线索转化、方案输出、销售效率和收入结果。',
        focus_points=(
            '更看重 AI 是否被用在客户沟通、方案生成、线索管理和销售复盘中。',
            '业务影响主要体现在签约、回款、转化率、商机质量和客户满意度。',
        ),
        dimension_weights={'TOOL': 0.15, 'DEPTH': 0.10, 'LEARN': 0.15, 'SHARE': 0.15, 'IMPACT': 0.45},
        dimension_keywords={
            'TOOL': ('crm', 'proposal', 'playbook', 'lead', '客户画像', '话术', '线索', '商机', '方案生成'),
            'DEPTH': ('pipeline', 'forecast', 'bid', 'journey', '报价', '投标', '预测', '客户旅程'),
            'LEARN': ('market insight', 'case review', '产品学习', '竞品应对', '案例复盘', '市场洞察'),
            'SHARE': ('销售手册', '案例库', '培训', '话术模板', '最佳实践'),
            'IMPACT': ('签约', '回款', '转化率', '客单价', '收入', '营收', '客户满意度', 'pipeline'),
        },
        dimension_focuses={
            'TOOL': '重点看是否把 AI 用于客户分析、商机推进、方案输出和沟通准备。',
            'DEPTH': '重点看是否把 AI 深度接入销售流程，而不只是偶尔生成文案。',
            'LEARN': '重点看是否持续吸收市场、产品和客户反馈并快速转化为打法。',
            'SHARE': '重点看是否沉淀销售手册、案例库和团队培训内容。',
            'IMPACT': '重点看签约、回款、转化率和客户满意度等直接业务结果。',
        },
    ),
    DepartmentProfile(
        code='OPERATIONS',
        label='运营与交付画像',
        match_keywords=('operations', 'delivery', 'implementation', 'support', 'service', '运营', '交付', '实施', '客服', '服务', '项目管理'),
        summary='重点看 AI 是否用于流程编排、服务响应、问题闭环、交付效率和履约质量。',
        focus_points=(
            '更看重 AI 是否进入工单、排班、知识库、交付执行和问题处理链路。',
            '业务影响主要体现为时效、履约质量、一次解决率和满意度。',
        ),
        dimension_weights={'TOOL': 0.20, 'DEPTH': 0.15, 'LEARN': 0.15, 'SHARE': 0.15, 'IMPACT': 0.35},
        dimension_keywords={
            'TOOL': ('ticket', 'workflow', 'sop', 'knowledge base', '工单', '排班', '机器人', '自动化流程', '知识库'),
            'DEPTH': ('dispatch', 'handoff', 'process', '闭环', '监控', '跨部门协同', '实施流程'),
            'LEARN': ('incident review', '演练', '问题分析', '现场复盘', '应急响应'),
            'SHARE': ('操作手册', 'faq', '培训', '问题库', '作业指引'),
            'IMPACT': ('响应时效', '处理时长', '履约', '交付质量', '一次解决率', '满意度'),
        },
        dimension_focuses={
            'TOOL': '重点看是否把 AI 用到运营执行、工单处理、知识库和流程自动化。',
            'DEPTH': '重点看是否进入跨角色协作、服务闭环和交付管理链路。',
            'LEARN': '重点看是否持续复盘问题，并把经验快速反馈到流程中。',
            'SHARE': '重点看是否形成标准操作手册、FAQ 和培训材料。',
            'IMPACT': '重点看时效、质量、履约结果和服务体验的改善。',
        },
    ),
    DepartmentProfile(
        code='CORP_SUPPORT',
        label='职能支持画像',
        match_keywords=('hr', 'finance', 'legal', 'procurement', 'admin', 'people', 'compliance', 'risk', '人力', '财务', '法务', '采购', '行政', '合规', '风控', '审计'),
        summary='重点看 AI 是否帮助制度执行、流程优化、风险控制、分析决策和组织赋能。',
        focus_points=(
            '更看重 AI 是否用于审批、分析、制度执行、合规校验和跨部门服务。',
            '业务影响主要体现为准确率、时效、成本节约、满意度和风险下降。',
        ),
        dimension_weights={'TOOL': 0.15, 'DEPTH': 0.10, 'LEARN': 0.15, 'SHARE': 0.25, 'IMPACT': 0.35},
        dimension_keywords={
            'TOOL': ('report', 'workflow', 'template', 'knowledge base', '报表', '审批流', '表单', '机器人', '知识库'),
            'DEPTH': ('policy', 'compliance', 'risk control', 'budget analysis', '制度', '流程重构', '合规校验', '预算分析', '系统对接'),
            'LEARN': ('政策学习', '制度更新', '专项培训', '案例复盘', '外部研究'),
            'SHARE': ('制度宣导', '模板', '指引', '培训', '标准化材料'),
            'IMPACT': ('准确率', '时效', '成本节约', '预算控制', '风险下降', '满意度'),
        },
        dimension_focuses={
            'TOOL': '重点看是否把 AI 用于分析、审批、知识检索和标准化处理。',
            'DEPTH': '重点看是否进入制度执行、预算分析、合规风控和流程优化。',
            'LEARN': '重点看是否持续跟进政策、制度和行业实践变化。',
            'SHARE': '重点看是否通过模板、制度宣导和培训扩大团队复用。',
            'IMPACT': '重点看时效、准确率、成本、满意度和风险控制结果。',
        },
    ),
)

SOURCE_RELIABILITY = {
    'self_report': 0.92,
    'file_parse': 1.0,
    'artifact_image': 0.96,
    'code_artifact': 1.05,
    'manager_review': 1.08,
    'business_metric': 1.12,
    'system_detected': 1.06,
    'vision_evaluation': 0.90,
    'vision_failed': 0.0,
}

LEVEL_THRESHOLDS = (
    ('Level 5', 88),
    ('Level 4', 76),
    ('Level 3', 64),
    ('Level 2', 52),
    ('Level 1', 0),
)

SCORE_GUIDANCE_BANDS = (
    {
        'range': '0-54',
        'meaning': '证据明显不足，或能力表现确实未达到岗位基本要求。',
    },
    {
        'range': '55-67',
        'meaning': '有零散尝试，但应用不稳定，结果不够清晰，整体仍低于稳态达标线。',
    },
    {
        'range': '68-78',
        'meaning': '达到岗位期望，能稳定使用 AI 解决本岗问题，并形成明确产出。',
    },
    {
        'range': '79-88',
        'meaning': '表现较强，方法可复用，结果较稳定，已形成清晰业务或效率价值。',
    },
    {
        'range': '89-95',
        'meaning': '表现突出，具备明显引领性、体系化沉淀或标杆价值。',
    },
)


@dataclass
class EvaluatedDimension:
    code: str
    label: str
    weight: float
    raw_score: float
    weighted_score: float
    rationale: str


@dataclass
class EvaluationResult:
    overall_score: float
    ai_level: str
    confidence_score: float
    explanation: str
    needs_manual_review: bool
    dimensions: list[EvaluatedDimension]


class EvaluationEngine:
    def evaluate(
        self,
        evidence_items: list[EvidenceItem],
        *,
        employee_profile: Mapping[str, Any] | None = None,
    ) -> EvaluationResult:
        if not evidence_items:
            raise ValueError('At least one evidence item is required to generate an evaluation.')

        profile = self.resolve_department_profile(employee_profile)
        dimensions = self.resolve_dimensions(employee_profile)
        suspicious_count = sum(1 for item in evidence_items if self._has_prompt_manipulation(item))
        average_confidence = sum(self._effective_confidence(item) for item in evidence_items) / len(evidence_items)
        average_reliability = sum(self._effective_reliability(item) for item in evidence_items) / len(evidence_items)

        evaluated_dimensions: list[EvaluatedDimension] = []
        strongest_dimension: EvaluatedDimension | None = None
        weakest_dimension: EvaluatedDimension | None = None

        for definition in dimensions:
            signals = self._collect_dimension_signals(definition, evidence_items)
            raw_score = self._score_dimension(
                signals,
                total_evidence_count=len(evidence_items),
                global_average_confidence=average_confidence,
                global_average_reliability=average_reliability,
            )
            dimension = EvaluatedDimension(
                code=definition.code,
                label=definition.label,
                weight=definition.weight,
                raw_score=raw_score,
                weighted_score=round(raw_score * definition.weight, 2),
                rationale=self._build_dimension_rationale(profile, signals, raw_score),
            )
            evaluated_dimensions.append(dimension)

            if strongest_dimension is None or dimension.raw_score > strongest_dimension.raw_score:
                strongest_dimension = dimension
            if weakest_dimension is None or dimension.raw_score < weakest_dimension.raw_score:
                weakest_dimension = dimension

        overall_score = round(sum(item.weighted_score for item in evaluated_dimensions), 2)
        high_dimension_count = sum(1 for item in evaluated_dimensions if item.raw_score >= 70)
        if suspicious_count == 0 and average_confidence >= 0.75 and high_dimension_count >= 2 and overall_score < 68:
            overall_score = 68.0
        ai_level = self._map_level(overall_score)
        needs_manual_review = (
            average_confidence < 0.68
            or suspicious_count > 0
            or any(item.raw_score < 50 for item in evaluated_dimensions)
            or sum(1 for item in evaluated_dimensions if item.raw_score < 55) >= 2
        )
        explanation = self._build_explanation(
            profile=profile,
            evidence_count=len(evidence_items),
            average_confidence=average_confidence,
            overall_score=overall_score,
            ai_level=ai_level,
            strongest_dimension=strongest_dimension,
            weakest_dimension=weakest_dimension,
            suspicious_count=suspicious_count,
        )
        return EvaluationResult(
            overall_score=overall_score,
            ai_level=ai_level,
            confidence_score=round(average_confidence, 2),
            explanation=explanation,
            needs_manual_review=needs_manual_review,
            dimensions=evaluated_dimensions,
        )

    def map_level(self, overall_score: float) -> str:
        return self._map_level(overall_score)

    def resolve_department_profile(self, employee_profile: Mapping[str, Any] | None = None) -> DepartmentProfile:
        haystack = self._profile_haystack(employee_profile)
        best_profile = DEFAULT_PROFILE
        best_score = 0

        for profile in DEPARTMENT_PROFILES:
            matched = {keyword for keyword in profile.match_keywords if keyword in haystack}
            score = len(matched)
            if score > best_score:
                best_profile = profile
                best_score = score

        return best_profile

    def resolve_dimensions(self, employee_profile: Mapping[str, Any] | None = None) -> tuple[DimensionDefinition, ...]:
        profile = self.resolve_department_profile(employee_profile)
        weights = self._normalized_weights(profile.dimension_weights)
        resolved: list[DimensionDefinition] = []

        for base in BASE_DIMENSIONS:
            profile_keywords = tuple(profile.dimension_keywords.get(base.code, ()))
            focus = profile.dimension_focuses.get(base.code, base.focus)
            keywords = self._dedupe_tuple(base.keywords + profile_keywords)
            resolved.append(
                DimensionDefinition(
                    code=base.code,
                    label=base.label,
                    weight=weights.get(base.code, base.weight),
                    keywords=keywords,
                    focus=focus,
                    profile_keywords=profile_keywords,
                )
            )

        return tuple(resolved)

    def build_scoring_context(self, employee_profile: Mapping[str, Any] | None = None) -> dict[str, Any]:
        profile = self.resolve_department_profile(employee_profile)
        dimensions = self.resolve_dimensions(employee_profile)
        return {
            'profile_code': profile.code,
            'profile_label': profile.label,
            'profile_summary': profile.summary,
            'focus_points': list(profile.focus_points),
            'reasoning_style': {
                'tone': '使用真实主管复核口吻，先说明员工做了什么，再说明是否符合岗位期待，最后点明结果或短板。',
                'rules': [
                    '不要照抄示例语料，要结合当前证据改写。',
                    '理由要像主管点评，不要像模型自述或抽象定义。',
                    '如果是达标表现，要明确写出“已达到岗位期望”或同等含义。',
                ],
            },
            'score_policy': {
                'default_expectation': '只要证据能说明员工已稳定、真实地在本岗位使用 AI 并形成产出，单维度通常应落在 68-85 分区间。',
                'low_score_rule': '只有在证据明显不足、结果不稳定，或能力表现确实未达岗位要求时，才应打到 60 分以下。',
                'bands': list(SCORE_GUIDANCE_BANDS),
            },
            'dimension_specs': [
                {
                    'code': item.code,
                    'label': item.label,
                    'weight': item.weight,
                    'focus': item.focus,
                    'sample_signals': list(item.profile_keywords[:6]),
                    'manager_examples': self._dimension_manager_examples(profile.code, item.code),
                }
                for item in dimensions
            ],
        }

    def _collect_dimension_signals(
        self,
        definition: DimensionDefinition,
        evidence_items: list[EvidenceItem],
    ) -> DimensionSignals:
        matched_evidence_count = 0
        matched_sources: set[str] = set()
        distinct_keywords: set[str] = set()
        distinct_profile_keywords: set[str] = set()
        total_keyword_hits = 0
        confidences: list[float] = []
        reliabilities: list[float] = []
        text_richness_values: list[float] = []
        suspicious_count = 0
        ranked_titles: list[tuple[float, str]] = []

        for item in evidence_items:
            item_is_suspicious = self._has_prompt_manipulation(item)
            if item_is_suspicious:
                suspicious_count += 1

            haystack = self._normalized_haystack(item)
            matched_keywords = [keyword for keyword in definition.keywords if keyword in haystack]
            if not matched_keywords:
                continue

            matched_profile_keywords = [keyword for keyword in definition.profile_keywords if keyword in haystack]
            matched_evidence_count += 1
            matched_sources.add(item.source_type)
            distinct_keywords.update(matched_keywords)
            distinct_profile_keywords.update(matched_profile_keywords)
            keyword_hits = sum(haystack.count(keyword) for keyword in matched_keywords)
            total_keyword_hits += keyword_hits

            confidence = self._effective_confidence(item)
            reliability = self._effective_reliability(item)
            confidences.append(confidence)
            reliabilities.append(reliability)
            text_richness_values.append(min(len(self._safe_text(item)) / 1200, 1.0))

            ranking_score = len(set(matched_keywords)) * 2 + min(keyword_hits, 6) + confidence * 2 + len(set(matched_profile_keywords))
            ranked_titles.append((ranking_score, item.title.strip() or '未命名材料'))

        ranked_titles.sort(key=lambda item: item[0], reverse=True)
        top_titles = self._dedupe([title for _, title in ranked_titles])[:2]

        return DimensionSignals(
            definition=definition,
            matched_evidence_count=matched_evidence_count,
            matched_source_count=len(matched_sources),
            distinct_keyword_count=len(distinct_keywords),
            total_keyword_hits=total_keyword_hits,
            profile_keyword_count=len(distinct_profile_keywords),
            average_confidence=round(sum(confidences) / len(confidences), 2) if confidences else 0.0,
            average_reliability=round(sum(reliabilities) / len(reliabilities), 2) if reliabilities else 0.0,
            average_text_richness=round(sum(text_richness_values) / len(text_richness_values), 2) if text_richness_values else 0.0,
            suspicious_count=suspicious_count,
            top_titles=top_titles,
            matched_keywords=self._dedupe(list(distinct_keywords))[:5],
            matched_profile_keywords=self._dedupe(list(distinct_profile_keywords))[:4],
        )

    def _score_dimension(
        self,
        signals: DimensionSignals,
        *,
        total_evidence_count: int,
        global_average_confidence: float,
        global_average_reliability: float,
    ) -> float:
        suspicious_penalty = signals.suspicious_count * 6.0
        profile_alignment = (
            signals.profile_keyword_count / len(signals.definition.profile_keywords)
            if signals.definition.profile_keywords
            else min(signals.distinct_keyword_count / max(len(signals.definition.keywords), 1), 1.0)
        )

        if signals.matched_evidence_count == 0:
            fallback_score = (
                48.0
                + global_average_confidence * 5.0
                + global_average_reliability * 4.0
                + profile_alignment * 4.0
                - suspicious_penalty
            )
            return round(max(45.0, min(62.0, fallback_score)), 2)

        keyword_coverage = signals.distinct_keyword_count / len(signals.definition.keywords)
        matched_ratio = signals.matched_evidence_count / total_evidence_count
        source_diversity = min(signals.matched_source_count / 3, 1.0)
        hit_intensity = min(signals.total_keyword_hits / max(signals.matched_evidence_count * 4, 1), 1.0)

        evidence_strength = (
            keyword_coverage * 0.17
            + matched_ratio * 0.16
            + source_diversity * 0.12
            + signals.average_confidence * 0.17
            + signals.average_reliability * 0.13
            + signals.average_text_richness * 0.08
            + hit_intensity * 0.07
            + profile_alignment * 0.10
        )

        if evidence_strength < 0.28:
            raw_score = self._interpolate_band(evidence_strength, 0.0, 0.28, 60.0, 69.0)
        elif evidence_strength < 0.55:
            raw_score = self._interpolate_band(evidence_strength, 0.28, 0.55, 70.0, 79.0)
        elif evidence_strength < 0.80:
            raw_score = self._interpolate_band(evidence_strength, 0.55, 0.80, 80.0, 88.0)
        else:
            raw_score = self._interpolate_band(evidence_strength, 0.80, 1.0, 89.0, 95.0)

        if signals.definition.profile_keywords and signals.profile_keyword_count == 0:
            raw_score -= 2.0
        if signals.matched_evidence_count == 1 and keyword_coverage < 0.18:
            raw_score -= 2.0
        if signals.average_confidence < 0.55 or signals.average_reliability < 0.75:
            raw_score -= 4.0
        if signals.definition.weight >= 0.30 and profile_alignment >= 0.25:
            raw_score += 1.5
        raw_score -= suspicious_penalty

        return round(max(35.0, min(96.0, raw_score)), 2)

    def _build_dimension_rationale(
        self,
        profile: DepartmentProfile,
        signals: DimensionSignals,
        raw_score: float,
    ) -> str:
        label = signals.definition.label
        focus_text = signals.definition.focus
        if signals.matched_evidence_count == 0:
            rationale = (
                f'按照“{profile.label}”的岗位标准，这个维度重点看{focus_text}'
                f'当前材料里没有找到与“{label}”直接相关的证据。'
                f'因此暂按保守口径给出 {raw_score:.2f} 分，不建议据此判定为高分。'
            )
        else:
            keyword_text = '、'.join(signals.matched_keywords) if signals.matched_keywords else '相关岗位信号'
            evidence_text = '、'.join(f'《{title}》' for title in signals.top_titles) if signals.top_titles else '当前材料'
            rationale = (
                f'按照“{profile.label}”的岗位标准，这个维度重点看{focus_text}'
                f'目前已在 {signals.matched_evidence_count} 份材料中识别到相关信号，主要依据来自 {evidence_text}，'
                f'命中的关键词包括 {keyword_text}。'
                f'综合材料强度后，当前评分为 {raw_score:.2f} 分。'
            )
            if signals.matched_profile_keywords:
                rationale += f' 其中还命中了更贴合该部门职能的信号：{"、".join(signals.matched_profile_keywords)}。'
            elif signals.definition.profile_keywords:
                rationale += ' 但材料里能直接证明该部门核心职能贡献的信号还不够充分。'

        if signals.suspicious_count:
            rationale += f' 同时检测到 {signals.suspicious_count} 份材料含疑似引导评分内容，系统已做降权处理。'
        return rationale

    def _build_explanation(
        self,
        *,
        profile: DepartmentProfile,
        evidence_count: int,
        average_confidence: float,
        overall_score: float,
        ai_level: str,
        strongest_dimension: EvaluatedDimension | None,
        weakest_dimension: EvaluatedDimension | None,
        suspicious_count: int,
    ) -> str:
        strongest_label = strongest_dimension.label if strongest_dimension is not None else '待补充'
        weakest_label = weakest_dimension.label if weakest_dimension is not None else '待补充'
        focus_points = '；'.join(profile.focus_points[:2])
        explanation = (
            f'本次评分按“{profile.label}”进行岗位职能解读，共分析 {evidence_count} 份真实材料，平均置信度为 {average_confidence:.2f}。'
            f'{profile.summary}{focus_points}。'
            f'当前优势维度为“{strongest_label}”，相对薄弱维度为“{weakest_label}”，综合得分 {overall_score:.2f}，对应 {ai_level}。'
        )
        if suspicious_count:
            explanation += f' 另外检测到 {suspicious_count} 份材料含疑似引导评分内容，系统已自动降权并建议人工复核。'
        return explanation

    def _profile_haystack(self, employee_profile: Mapping[str, Any] | None) -> str:
        if employee_profile is None:
            return ''
        parts = [
            str(employee_profile.get('department', '') or ''),
            str(employee_profile.get('job_family', '') or ''),
            str(employee_profile.get('job_level', '') or ''),
        ]
        return ' '.join(parts).lower()

    def _normalized_haystack(self, item: EvidenceItem) -> str:
        metadata_tags = item.metadata_json.get('tags', []) if isinstance(item.metadata_json, dict) else []
        text = f"{item.title} {item.content} {' '.join(str(tag) for tag in metadata_tags)}"
        return scan_for_prompt_manipulation(text).sanitized_text.lower()

    def _effective_confidence(self, item: EvidenceItem) -> float:
        confidence = item.confidence_score
        if self._has_prompt_manipulation(item):
            confidence = max(0.05, confidence - 0.25)
        return confidence

    def _effective_reliability(self, item: EvidenceItem) -> float:
        reliability = SOURCE_RELIABILITY.get(item.source_type, 0.95)
        if self._has_prompt_manipulation(item):
            reliability = max(0.55, reliability - 0.35)
        return reliability

    def _safe_text(self, item: EvidenceItem) -> str:
        return scan_for_prompt_manipulation(f'{item.title} {item.content}').sanitized_text

    def _has_prompt_manipulation(self, item: EvidenceItem) -> bool:
        if isinstance(item.metadata_json, dict) and item.metadata_json.get('prompt_manipulation_detected'):
            return True
        return scan_for_prompt_manipulation(f'{item.title} {item.content}').detected

    def _map_level(self, overall_score: float) -> str:
        for label, threshold in LEVEL_THRESHOLDS:
            if overall_score >= threshold:
                return label
        return 'Level 1'

    def _normalized_weights(self, raw_weights: Mapping[str, float]) -> dict[str, float]:
        total = sum(raw_weights.values()) or 1.0
        return {code: round(weight / total, 4) for code, weight in raw_weights.items()}

    def _dedupe(self, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    def _dedupe_tuple(self, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(self._dedupe(list(values)))

    def _interpolate_band(
        self,
        value: float,
        lower_bound: float,
        upper_bound: float,
        lower_score: float,
        upper_score: float,
    ) -> float:
        if upper_bound <= lower_bound:
            return lower_score
        normalized = max(0.0, min((value - lower_bound) / (upper_bound - lower_bound), 1.0))
        return lower_score + (upper_score - lower_score) * normalized

    def _dimension_manager_examples(self, profile_code: str, dimension_code: str) -> dict[str, list[str]]:
        profile_examples = DEPARTMENT_DIMENSION_EXAMPLES.get(profile_code) or DEPARTMENT_DIMENSION_EXAMPLES['GENERAL']
        dimension_examples = profile_examples.get(dimension_code) or DEPARTMENT_DIMENSION_EXAMPLES['GENERAL'][dimension_code]
        return {
            'meets_expectation': list(dimension_examples.get('meets', ())),
            'strong_performance': list(dimension_examples.get('strong', ())),
        }
