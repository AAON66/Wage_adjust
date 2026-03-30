import { Link } from 'react-router-dom';
import { useState } from 'react';

type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

interface ApiEndpointDoc {
  method: HttpMethod;
  path: string;
  summary: string;
  auth: string;
  request?: string;
  params?: string;
  response: string;
  note?: string;
  service?: string;
  contentType?: 'application/json' | 'multipart/form-data' | 'none';
  exampleBody?: string;
  exampleQuery?: string;
}

interface ApiModuleDoc {
  key: string;
  title: string;
  summary: string;
  tag: string;
  endpoints: ApiEndpointDoc[];
}

const API_MODULES: ApiModuleDoc[] = [
  {
    key: 'system',
    title: '系统',
    summary: '用于前端启动时读取应用元信息。',
    tag: '无鉴权',
    endpoints: [
      {
        method: 'GET',
        path: '/system/meta',
        summary: '读取应用名称、版本、环境和 API 前缀。',
        auth: '无鉴权',
        response: '{ app_name, app_version, environment, api_prefix }',
      },
    ],
  },
  {
    key: 'auth',
    title: '认证',
    summary: '登录、刷新令牌、查询当前账号与修改密码。',
    tag: 'Bearer / 无鉴权',
    endpoints: [
      {
        method: 'POST',
        path: '/auth/register',
        summary: '自助注册账号并返回用户信息与令牌。',
        auth: '无鉴权',
        request: '{ email, password, role }',
        response: 'AuthResponse { user, tokens }',
        note: '是否允许注册受 allow_self_registration 配置控制。',
        service: 'frontend/src/services/auth.ts -> register',
        exampleBody: JSON.stringify({ email: 'dev@example.com', password: 'Password123!', role: 'employee' }, null, 2),
      },
      {
        method: 'POST',
        path: '/auth/login',
        summary: '账号登录，返回 access_token 和 refresh_token。',
        auth: '无鉴权',
        request: '{ email, password }',
        response: 'TokenPair { access_token, refresh_token }',
        service: 'frontend/src/services/auth.ts -> login',
        exampleBody: JSON.stringify({ email: 'dev@example.com', password: 'Password123!' }, null, 2),
      },
      {
        method: 'POST',
        path: '/auth/refresh',
        summary: '使用 refresh_token 换取新令牌。',
        auth: '无鉴权',
        request: '{ refresh_token }',
        response: 'TokenPair { access_token, refresh_token }',
        service: 'frontend/src/services/auth.ts -> refresh',
        exampleBody: JSON.stringify({ refresh_token: 'your-refresh-token' }, null, 2),
      },
      {
        method: 'GET',
        path: '/auth/me',
        summary: '读取当前登录用户资料。',
        auth: 'Bearer',
        response: 'UserRead',
        service: 'frontend/src/services/auth.ts -> fetchCurrentUser',
      },
      {
        method: 'POST',
        path: '/auth/change-password',
        summary: '修改当前账号密码。',
        auth: 'Bearer',
        request: '{ current_password, new_password }',
        response: '{ message }',
        service: 'frontend/src/services/auth.ts -> changePassword',
        exampleBody: JSON.stringify({ current_password: 'OldPass123!', new_password: 'NewPass123!' }, null, 2),
      },
    ],
  },
  {
    key: 'users',
    title: '用户管理',
    summary: '管理员、HRBP、主管的账号管理接口。',
    tag: 'Bearer(admin/hrbp/manager)',
    endpoints: [
      {
        method: 'GET',
        path: '/users',
        summary: '分页查询账号列表。',
        auth: 'Bearer(admin/hrbp/manager)',
        params: 'page, page_size, role, keyword',
        response: 'UserListResponse',
        service: 'frontend/src/services/userAdminService.ts -> fetchUsers',
        exampleQuery: '?page=1&page_size=20&role=employee&keyword=zhang',
      },
      {
        method: 'POST',
        path: '/users',
        summary: '创建单个托管账号。',
        auth: 'Bearer(admin/hrbp/manager)',
        request: 'UserAdminCreate',
        response: 'UserRead',
        service: 'frontend/src/services/userAdminService.ts -> createManagedUser',
        exampleBody: JSON.stringify({ email: 'new.user@example.com', password: 'Password123!', role: 'employee', employee_id: null }, null, 2),
      },
      {
        method: 'POST',
        path: '/users/bulk-create',
        summary: '批量创建账号。',
        auth: 'Bearer(admin/hrbp/manager)',
        request: '{ items: UserAdminCreate[] }',
        response: 'BulkUserCreateResponse',
        service: 'frontend/src/services/userAdminService.ts -> bulkCreateUsers',
        exampleBody: JSON.stringify({ items: [{ email: 'user.a@example.com', password: 'Password123!', role: 'employee' }] }, null, 2),
      },
      {
        method: 'PATCH',
        path: '/users/{user_id}/binding',
        summary: '绑定或解绑员工档案。',
        auth: 'Bearer(admin/hrbp/manager)',
        request: '{ employee_id }',
        response: 'UserRead',
        service: 'frontend/src/services/userAdminService.ts -> updateManagedUserEmployeeBinding',
        exampleBody: JSON.stringify({ employee_id: 'emp_001' }, null, 2),
      },
      {
        method: 'PATCH',
        path: '/users/{user_id}/password',
        summary: '重置托管账号密码。',
        auth: 'Bearer(admin/hrbp/manager)',
        request: '{ new_password }',
        response: '{ updated_user_id, message }',
        service: 'frontend/src/services/userAdminService.ts -> updateManagedUserPassword',
        exampleBody: JSON.stringify({ new_password: 'ResetPass123!' }, null, 2),
      },
      {
        method: 'DELETE',
        path: '/users/{user_id}',
        summary: '删除单个账号。',
        auth: 'Bearer(admin/hrbp/manager)',
        response: '{ deleted_user_id }',
        service: 'frontend/src/services/userAdminService.ts -> deleteManagedUser',
      },
      {
        method: 'POST',
        path: '/users/bulk-delete',
        summary: '批量删除账号。',
        auth: 'Bearer(admin/hrbp/manager)',
        request: '{ user_ids: string[] }',
        response: 'BulkUserDeleteResponse',
        service: 'frontend/src/services/userAdminService.ts -> bulkDeleteUsers',
        exampleBody: JSON.stringify({ user_ids: ['user_001', 'user_002'] }, null, 2),
      },
    ],
  },
  {
    key: 'employees',
    title: '员工',
    summary: '员工档案查询与创建。',
    tag: 'Bearer',
    endpoints: [
      {
        method: 'GET',
        path: '/employees',
        summary: '分页查询员工档案。',
        auth: 'Bearer',
        params: 'page, page_size, department, job_family, status',
        response: 'EmployeeListResponse',
        service: 'frontend/src/services/employeeService.ts -> fetchEmployees',
        exampleQuery: '?page=1&page_size=20&department=研发&status=active',
      },
      {
        method: 'GET',
        path: '/employees/{employee_id}',
        summary: '读取单个员工档案。',
        auth: 'Bearer',
        response: 'EmployeeRead',
        service: 'frontend/src/services/employeeService.ts -> fetchEmployee',
      },
      {
        method: 'POST',
        path: '/employees',
        summary: '创建员工档案。',
        auth: 'Bearer(admin/hrbp/manager)',
        request: 'EmployeeCreate',
        response: 'EmployeeRead',
        exampleBody: JSON.stringify({ employee_no: 'E10001', name: '张三', department: '研发', job_family: '工程', job_level: 'P5' }, null, 2),
        service: 'frontend/src/services/employeeService.ts -> createEmployee',
      },
    ],
  },
  {
    key: 'cycles',
    title: '评估周期',
    summary: '创建、维护、发布与归档评估周期。',
    tag: 'Bearer',
    endpoints: [
      {
        method: 'GET',
        path: '/cycles',
        summary: '读取周期列表。',
        auth: 'Bearer',
        response: 'CycleListResponse',
        service: 'frontend/src/services/cycleService.ts -> fetchCycles',
      },
      {
        method: 'POST',
        path: '/cycles',
        summary: '创建评估周期。',
        auth: 'Bearer(admin/hrbp)',
        request: 'CycleCreate',
        response: 'CycleRead',
        service: 'frontend/src/services/cycleService.ts -> createCycle',
        exampleBody: JSON.stringify({ name: '2026 上半年调薪', budget_amount: '500000', start_date: '2026-04-01', end_date: '2026-05-31' }, null, 2),
      },
      {
        method: 'PATCH',
        path: '/cycles/{cycle_id}',
        summary: '更新周期配置。',
        auth: 'Bearer(admin/hrbp)',
        request: 'CycleUpdate',
        response: 'CycleRead',
        service: 'frontend/src/services/cycleService.ts -> updateCycle',
        exampleBody: JSON.stringify({ budget_amount: '650000', status: 'draft' }, null, 2),
      },
      {
        method: 'POST',
        path: '/cycles/{cycle_id}/publish',
        summary: '发布周期。',
        auth: 'Bearer(admin/hrbp)',
        response: 'CycleRead',
        service: 'frontend/src/services/cycleService.ts -> publishCycle',
      },
      {
        method: 'POST',
        path: '/cycles/{cycle_id}/archive',
        summary: '归档周期。',
        auth: 'Bearer(admin/hrbp)',
        response: 'CycleRead',
        service: 'frontend/src/services/cycleService.ts -> archiveCycle',
      },
    ],
  },
  {
    key: 'submissions',
    title: '提交与材料',
    summary: '负责员工提交记录、材料上传、解析和证据抽取。',
    tag: 'Bearer',
    endpoints: [
      {
        method: 'POST',
        path: '/submissions/ensure',
        summary: '确保员工在某个周期存在提交记录。',
        auth: 'Bearer',
        request: '{ employee_id, cycle_id }',
        response: 'SubmissionRead',
        service: 'frontend/src/services/submissionService.ts -> ensureSubmission',
        exampleBody: JSON.stringify({ employee_id: 'emp_001', cycle_id: 'cycle_2026_h1' }, null, 2),
      },
      {
        method: 'GET',
        path: '/submissions/employee/{employee_id}',
        summary: '读取员工的提交记录列表。',
        auth: 'Bearer',
        response: 'SubmissionListResponse',
        service: 'frontend/src/services/submissionService.ts -> fetchEmployeeSubmissions',
      },
      {
        method: 'GET',
        path: '/submissions/{submission_id}/files',
        summary: '读取某次提交下的材料文件。',
        auth: 'Bearer',
        response: 'UploadedFileListResponse',
        service: 'frontend/src/services/fileService.ts -> fetchSubmissionFiles',
      },
      {
        method: 'POST',
        path: '/submissions/{submission_id}/files',
        summary: '批量上传材料文件。',
        auth: 'Bearer',
        request: 'multipart/form-data: files[]',
        response: 'UploadedFileListResponse',
        contentType: 'multipart/form-data',
        service: 'frontend/src/services/fileService.ts -> uploadSubmissionFiles',
      },
      {
        method: 'POST',
        path: '/submissions/{submission_id}/github-import',
        summary: '通过 GitHub URL 导入材料并立即触发解析。',
        auth: 'Bearer',
        request: '{ url }',
        response: 'UploadedFileRead',
        note: '属于长耗时接口，前端为它单独放宽了超时。',
        service: 'frontend/src/services/fileService.ts -> importGitHubSubmissionFile',
        exampleBody: JSON.stringify({ url: 'https://github.com/org/repo/blob/main/README.md' }, null, 2),
      },
      {
        method: 'PUT',
        path: '/files/{file_id}',
        summary: '替换已上传的材料文件。',
        auth: 'Bearer',
        request: 'multipart/form-data: file',
        response: 'UploadedFileRead',
        contentType: 'multipart/form-data',
        service: 'frontend/src/services/fileService.ts -> replaceSubmissionFile',
      },
      {
        method: 'DELETE',
        path: '/files/{file_id}',
        summary: '删除材料文件。',
        auth: 'Bearer',
        response: 'FileDeleteResponse',
        service: 'frontend/src/services/fileService.ts -> deleteSubmissionFile',
      },
      {
        method: 'POST',
        path: '/files/{file_id}/parse',
        summary: '解析单个文件并抽取证据。',
        auth: 'Bearer',
        response: 'ParseResultResponse',
        note: '若未配置所需模型能力，后端会返回 503。',
        service: 'frontend/src/services/fileService.ts -> parseFile',
      },
      {
        method: 'POST',
        path: '/submissions/{submission_id}/parse-all',
        summary: '批量解析某次提交的全部文件。',
        auth: 'Bearer',
        response: 'UploadedFileListResponse',
        note: '适合上传完成后的整批处理。',
        service: 'frontend/src/services/fileService.ts -> parseAllSubmissionFiles',
      },
      {
        method: 'GET',
        path: '/files/{file_id}/preview',
        summary: '读取文件预览地址。',
        auth: 'Bearer',
        response: 'FilePreviewResponse',
        service: 'frontend/src/services/fileService.ts -> previewFile(后端预留，前端当前未单独封装)',
      },
      {
        method: 'GET',
        path: '/submissions/{submission_id}/evidence',
        summary: '读取抽取出的证据卡片。',
        auth: 'Bearer',
        response: 'EvidenceListResponse',
        service: 'frontend/src/services/fileService.ts -> fetchSubmissionEvidence',
      },
    ],
  },
  {
    key: 'evaluations',
    title: '评估',
    summary: 'AI 评估生成、人工复核和确认。',
    tag: 'Bearer',
    endpoints: [
      {
        method: 'POST',
        path: '/evaluations/generate',
        summary: '根据 submission_id 生成 AI 评估。',
        auth: 'Bearer',
        request: '{ submission_id }',
        response: 'EvaluationRead',
        note: '属于长耗时接口。',
        service: 'frontend/src/services/evaluationService.ts -> generateEvaluation',
        exampleBody: JSON.stringify({ submission_id: 'sub_001' }, null, 2),
      },
      {
        method: 'POST',
        path: '/evaluations/regenerate',
        summary: '强制重新生成 AI 评估。',
        auth: 'Bearer',
        request: '{ submission_id }',
        response: 'EvaluationRead',
        note: '用于覆盖已有结果。',
        service: 'frontend/src/services/evaluationService.ts -> regenerateEvaluation',
        exampleBody: JSON.stringify({ submission_id: 'sub_001' }, null, 2),
      },
      {
        method: 'GET',
        path: '/evaluations/{evaluation_id}',
        summary: '读取单条评估详情。',
        auth: 'Bearer',
        response: 'EvaluationRead',
        service: 'frontend/src/services/evaluationService.ts -> fetchEvaluation',
      },
      {
        method: 'GET',
        path: '/evaluations/by-submission/{submission_id}',
        summary: '按提交记录查询评估。',
        auth: 'Bearer',
        response: 'EvaluationRead',
        service: 'frontend/src/services/evaluationService.ts -> fetchEvaluationBySubmission',
      },
      {
        method: 'PATCH',
        path: '/evaluations/{evaluation_id}/manual-review',
        summary: '主管或人工校准评估结果。',
        auth: 'Bearer',
        request: '{ ai_level, overall_score, explanation, dimension_scores[] }',
        response: 'EvaluationRead',
        service: 'frontend/src/services/evaluationService.ts -> submitManualReview',
        exampleBody: JSON.stringify({
          ai_level: 'Level 4',
          overall_score: 88,
          explanation: '结合项目交付与影响面完成人工复核。',
          dimension_scores: [{ dimension_code: 'impact', raw_score: 90, rationale: '推动核心项目上线。' }],
        }, null, 2),
      },
      {
        method: 'PATCH',
        path: '/evaluations/{evaluation_id}/hr-review',
        summary: 'HR 审核评估结果。',
        auth: 'Bearer(admin/hrbp)',
        request: '{ decision, comment, final_score }',
        response: 'EvaluationRead',
        service: 'frontend/src/services/evaluationService.ts -> submitHrReview',
        exampleBody: JSON.stringify({ decision: 'approved', comment: '同意进入调薪阶段。', final_score: 89 }, null, 2),
      },
      {
        method: 'POST',
        path: '/evaluations/{evaluation_id}/confirm',
        summary: '确认评估状态。',
        auth: 'Bearer',
        response: 'EvaluationConfirmResponse',
        service: 'frontend/src/services/evaluationService.ts -> confirmEvaluation',
      },
    ],
  },
  {
    key: 'salary',
    title: '调薪',
    summary: '推荐、模拟、更新和锁定调薪建议。',
    tag: 'Bearer',
    endpoints: [
      {
        method: 'POST',
        path: '/salary/recommend',
        summary: '根据评估结果生成调薪建议。',
        auth: 'Bearer',
        request: '{ evaluation_id }',
        response: 'SalaryRecommendationRead',
        note: '属于长耗时接口。',
        service: 'frontend/src/services/salaryService.ts -> recommendSalary',
        exampleBody: JSON.stringify({ evaluation_id: 'eval_001' }, null, 2),
      },
      {
        method: 'GET',
        path: '/salary/by-evaluation/{evaluation_id}',
        summary: '按评估记录查询调薪建议。',
        auth: 'Bearer',
        response: 'SalaryRecommendationRead',
        service: 'frontend/src/services/salaryService.ts -> fetchSalaryRecommendationByEvaluation',
      },
      {
        method: 'GET',
        path: '/salary/{recommendation_id}',
        summary: '读取单条调薪建议。',
        auth: 'Bearer',
        response: 'SalaryRecommendationRead',
        service: 'frontend/src/services/salaryService.ts -> fetchSalaryRecommendation',
      },
      {
        method: 'PATCH',
        path: '/salary/{recommendation_id}',
        summary: '更新最终调薪比例和状态。',
        auth: 'Bearer',
        request: '{ final_adjustment_ratio, status }',
        response: 'SalaryRecommendationRead',
        service: 'frontend/src/services/salaryService.ts -> updateSalaryRecommendation',
        exampleBody: JSON.stringify({ final_adjustment_ratio: 0.12, status: 'recommended' }, null, 2),
      },
      {
        method: 'POST',
        path: '/salary/simulate',
        summary: '按周期、预算、部门或职族模拟调薪结果。',
        auth: 'Bearer',
        request: '{ cycle_id, budget_amount, department, job_family }',
        response: 'SalarySimulationResponse',
        service: 'frontend/src/services/salaryService.ts -> simulateSalary',
        exampleBody: JSON.stringify({ cycle_id: 'cycle_2026_h1', budget_amount: '500000', department: '研发', job_family: '工程' }, null, 2),
      },
      {
        method: 'POST',
        path: '/salary/{recommendation_id}/lock',
        summary: '锁定调薪建议，进入更稳定的后续流程。',
        auth: 'Bearer',
        response: 'SalaryLockResponse',
        service: '后端预留 /salary/{recommendation_id}/lock',
      },
    ],
  },
  {
    key: 'approvals',
    title: '审批',
    summary: '发起审批、审批决策、查看历史和校准队列。',
    tag: 'Bearer',
    endpoints: [
      {
        method: 'GET',
        path: '/approvals',
        summary: '读取当前账号可见的审批记录。',
        auth: 'Bearer',
        params: 'include_all, decision',
        response: 'ApprovalListResponse',
        service: 'frontend/src/services/approvalService.ts -> fetchApprovals',
        exampleQuery: '?include_all=true&decision=pending',
      },
      {
        method: 'POST',
        path: '/approvals/submit',
        summary: '提交调薪建议进入审批流程。',
        auth: 'Bearer(admin/hrbp/manager)',
        request: '{ recommendation_id, steps[] }',
        response: 'ApprovalListResponse',
        service: 'frontend/src/services/approvalService.ts -> submitApproval',
        exampleBody: JSON.stringify({
          recommendation_id: 'rec_001',
          steps: [{ approver_id: 'user_hrbp_001', step_name: 'HRBP 审核' }],
        }, null, 2),
      },
      {
        method: 'PATCH',
        path: '/approvals/{approval_id}',
        summary: '审批人对单条审批记录做决策。',
        auth: 'Bearer',
        request: '{ decision, comment }',
        response: 'ApprovalStatusResponse',
        service: 'frontend/src/services/approvalService.ts -> decideApproval',
        exampleBody: JSON.stringify({ decision: 'approved', comment: '同意通过。' }, null, 2),
      },
      {
        method: 'GET',
        path: '/approvals/recommendations/{recommendation_id}/history',
        summary: '读取某条调薪建议的审批历史。',
        auth: 'Bearer',
        response: 'ApprovalListResponse',
        service: '后端预留 /approvals/recommendations/{recommendation_id}/history',
      },
      {
        method: 'GET',
        path: '/approvals/calibration-queue',
        summary: '读取校准队列。',
        auth: 'Bearer(admin/hrbp/manager)',
        params: 'include_completed',
        response: 'CalibrationQueueResponse',
        service: '后端预留 /approvals/calibration-queue',
        exampleQuery: '?include_completed=false',
      },
    ],
  },
  {
    key: 'dashboard',
    title: '看板',
    summary: '组织概览、AI 分布、ROI 分布和热力图。',
    tag: 'Bearer',
    endpoints: [
      {
        method: 'GET',
        path: '/dashboard/overview',
        summary: '读取概览指标。',
        auth: 'Bearer',
        params: 'cycle_id',
        response: 'DashboardOverviewResponse',
        service: '后端预留 /dashboard/overview',
        exampleQuery: '?cycle_id=cycle_2026_h1',
      },
      {
        method: 'GET',
        path: '/dashboard/ai-level-distribution',
        summary: '读取 AI 等级分布。',
        auth: 'Bearer',
        params: 'cycle_id',
        response: 'DistributionResponse',
        service: '后端预留 /dashboard/ai-level-distribution',
        exampleQuery: '?cycle_id=cycle_2026_h1',
      },
      {
        method: 'GET',
        path: '/dashboard/department-heatmap',
        summary: '读取部门热力图。',
        auth: 'Bearer',
        params: 'cycle_id',
        response: 'HeatmapResponse',
        service: '后端预留 /dashboard/department-heatmap',
        exampleQuery: '?cycle_id=cycle_2026_h1',
      },
      {
        method: 'GET',
        path: '/dashboard/roi-distribution',
        summary: '读取 ROI 分布。',
        auth: 'Bearer',
        params: 'cycle_id',
        response: 'DistributionResponse',
        service: '后端预留 /dashboard/roi-distribution',
        exampleQuery: '?cycle_id=cycle_2026_h1',
      },
      {
        method: 'GET',
        path: '/dashboard/snapshot',
        summary: '一次性读取看板聚合快照。',
        auth: 'Bearer',
        params: 'cycle_id',
        response: 'DashboardSnapshotResponse',
        service: 'frontend/src/services/dashboardService.ts -> fetchDashboardSnapshot',
        exampleQuery: '?cycle_id=cycle_2026_h1',
      },
    ],
  },
  {
    key: 'imports',
    title: '导入',
    summary: '模板下载、导入任务执行、结果导出和清理。',
    tag: 'Bearer',
    endpoints: [
      {
        method: 'GET',
        path: '/imports/jobs',
        summary: '读取导入任务列表。',
        auth: 'Bearer',
        response: 'ImportJobListResponse',
        service: 'frontend/src/services/importService.ts -> fetchImportJobs',
      },
      {
        method: 'GET',
        path: '/imports/jobs/{job_id}',
        summary: '读取单个导入任务详情。',
        auth: 'Bearer',
        response: 'ImportJobRead',
        service: '后端预留 /imports/jobs/{job_id}',
      },
      {
        method: 'POST',
        path: '/imports/jobs',
        summary: '创建导入任务。',
        auth: 'Bearer(admin/hrbp/manager)',
        params: 'import_type',
        request: 'multipart/form-data: file',
        response: 'ImportJobRead',
        contentType: 'multipart/form-data',
        service: 'frontend/src/services/importService.ts -> createImportJob',
        exampleQuery: '?import_type=employees',
      },
      {
        method: 'GET',
        path: '/imports/templates/{import_type}',
        summary: '下载对应模板。',
        auth: 'Bearer',
        response: '文件流',
        service: 'frontend/src/services/importService.ts -> downloadImportTemplate',
      },
      {
        method: 'GET',
        path: '/imports/jobs/{job_id}/export',
        summary: '导出导入结果报告。',
        auth: 'Bearer',
        response: '文件流',
        service: 'frontend/src/services/importService.ts -> exportImportJob',
      },
      {
        method: 'DELETE',
        path: '/imports/jobs/{job_id}',
        summary: '删除单个导入任务。',
        auth: 'Bearer(admin/hrbp/manager)',
        response: 'ImportJobDeleteResponse',
        service: 'frontend/src/services/importService.ts -> deleteImportJob',
      },
      {
        method: 'POST',
        path: '/imports/jobs/bulk-delete',
        summary: '批量删除导入任务。',
        auth: 'Bearer(admin/hrbp/manager)',
        request: '{ job_ids: string[] }',
        response: 'BulkImportJobDeleteResponse',
        service: 'frontend/src/services/importService.ts -> bulkDeleteImportJobs',
        exampleBody: JSON.stringify({ job_ids: ['job_001', 'job_002'] }, null, 2),
      },
    ],
  },
  {
    key: 'handbooks',
    title: '员工手册',
    summary: '管理员维护员工手册，用于规则和说明材料。',
    tag: 'Bearer(admin/hrbp/manager)',
    endpoints: [
      {
        method: 'GET',
        path: '/handbooks',
        summary: '读取员工手册列表。',
        auth: 'Bearer(admin/hrbp/manager)',
        response: 'EmployeeHandbookListResponse',
        service: 'frontend/src/services/handbookService.ts -> fetchHandbooks',
      },
      {
        method: 'POST',
        path: '/handbooks',
        summary: '上传员工手册。',
        auth: 'Bearer(admin/hrbp/manager)',
        request: 'multipart/form-data: file',
        response: 'EmployeeHandbookRead',
        contentType: 'multipart/form-data',
        service: 'frontend/src/services/handbookService.ts -> uploadHandbook',
      },
      {
        method: 'DELETE',
        path: '/handbooks/{handbook_id}',
        summary: '删除员工手册。',
        auth: 'Bearer(admin/hrbp/manager)',
        response: 'EmployeeHandbookDeleteResponse',
        service: 'frontend/src/services/handbookService.ts -> deleteHandbook',
      },
    ],
  },
  {
    key: 'public',
    title: '公开接口',
    summary: '预留给外部系统对接的只读接口，需要单独的 X-API-Key。',
    tag: 'X-API-Key',
    endpoints: [
      {
        method: 'GET',
        path: '/public/employees/{employee_no}/latest-evaluation',
        summary: '读取员工最新评估和调薪建议。',
        auth: 'X-API-Key',
        response: 'PublicLatestEvaluationResponse',
        service: '后端预留公开接口',
      },
      {
        method: 'GET',
        path: '/public/cycles/{cycle_id}/salary-results',
        summary: '读取某周期全部调薪结果。',
        auth: 'X-API-Key',
        response: 'PublicSalaryResultsResponse',
        service: '后端预留公开接口',
      },
      {
        method: 'GET',
        path: '/public/cycles/{cycle_id}/approval-status',
        summary: '读取某周期审批推进状态。',
        auth: 'X-API-Key',
        response: 'PublicApprovalStatusResponse',
        service: '后端预留公开接口',
      },
      {
        method: 'GET',
        path: '/public/dashboard/summary',
        summary: '读取公开版看板摘要。',
        auth: 'X-API-Key',
        response: 'PublicDashboardSummaryResponse',
        service: '后端预留公开接口',
      },
    ],
  },
];

const METHOD_STYLES: Record<HttpMethod, { color: string; background: string; border: string }> = {
  GET: { color: '#1456F0', background: '#EBF0FE', border: '#C5D3FB' },
  POST: { color: '#00A870', background: '#E8FFEA', border: '#AFF0B5' },
  PATCH: { color: '#FF7D00', background: '#FFF3E8', border: '#FFD8A8' },
  PUT: { color: '#722ED1', background: '#F4EBFF', border: '#D9C2FF' },
  DELETE: { color: '#F53F3F', background: '#FFECE8', border: '#FFCDD0' },
};

function matchesKeyword(endpoint: ApiEndpointDoc, keyword: string): boolean {
  if (!keyword) {
    return true;
  }

  const content = [
    endpoint.method,
    endpoint.path,
    endpoint.summary,
    endpoint.auth,
    endpoint.request,
    endpoint.params,
    endpoint.response,
    endpoint.note,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

  return content.includes(keyword.toLowerCase());
}

function getContentType(endpoint: ApiEndpointDoc): 'application/json' | 'multipart/form-data' | 'none' {
  if (endpoint.contentType) {
    return endpoint.contentType;
  }

  if (endpoint.request?.includes('multipart/form-data')) {
    return 'multipart/form-data';
  }

  if (endpoint.method === 'GET' || endpoint.method === 'DELETE') {
    return 'none';
  }

  return 'application/json';
}

function getExamplePath(path: string): string {
  return path
    .replace('{user_id}', 'user_001')
    .replace('{employee_id}', 'emp_001')
    .replace('{employee_no}', 'E10001')
    .replace('{cycle_id}', 'cycle_2026_h1')
    .replace('{submission_id}', 'sub_001')
    .replace('{evaluation_id}', 'eval_001')
    .replace('{recommendation_id}', 'rec_001')
    .replace('{approval_id}', 'approval_001')
    .replace('{file_id}', 'file_001')
    .replace('{job_id}', 'job_001')
    .replace('{handbook_id}', 'handbook_001')
    .replace('{import_type}', 'employees');
}

function getExampleUrl(baseUrl: string, endpoint: ApiEndpointDoc): string {
  return `${baseUrl}${getExamplePath(endpoint.path)}${endpoint.exampleQuery ?? ''}`;
}

function getHeaderLines(endpoint: ApiEndpointDoc): string[] {
  const lines: string[] = [];
  const contentType = getContentType(endpoint);

  if (endpoint.auth.includes('Bearer')) {
    lines.push("'Authorization': 'Bearer <access_token>'");
  } else if (endpoint.auth === 'X-API-Key') {
    lines.push("'X-API-Key': '<public_api_key>'");
  }

  if (contentType === 'application/json') {
    lines.push("'Content-Type': 'application/json'");
  }

  return lines;
}

function buildFetchSnippet(baseUrl: string, endpoint: ApiEndpointDoc): string {
  const url = getExampleUrl(baseUrl, endpoint);
  const contentType = getContentType(endpoint);
  const headerLines = getHeaderLines(endpoint);

  if (contentType === 'multipart/form-data') {
    const formDataLines = endpoint.request?.includes('files[]')
      ? ["const formData = new FormData();", "files.forEach((file) => formData.append('files', file));"]
      : ["const formData = new FormData();", "formData.append('file', file);"];

    const authHeaderLines = headerLines.filter((line) => !line.includes('Content-Type'));
    const headersBlock = authHeaderLines.length > 0
      ? `,\n  headers: {\n    ${authHeaderLines.join(',\n    ')}\n  }`
      : '';

    return `${formDataLines.join('\n')}\n\nconst response = await fetch('${url}', {\n  method: '${endpoint.method}'${headersBlock},\n  body: formData,\n});\n\nconst data = await response.json();`;
  }

  const options: string[] = [`method: '${endpoint.method}'`];
  if (headerLines.length > 0) {
    options.push(`headers: {\n    ${headerLines.join(',\n    ')}\n  }`);
  }
  if (contentType === 'application/json' && endpoint.exampleBody) {
    options.push(`body: JSON.stringify(${endpoint.exampleBody})`);
  }

  return `const response = await fetch('${url}', {\n  ${options.join(',\n  ')}\n});\n\nconst data = await response.json();`;
}

function buildCurlSnippet(baseUrl: string, endpoint: ApiEndpointDoc): string {
  const url = getExampleUrl(baseUrl, endpoint);
  const contentType = getContentType(endpoint);
  const headerLines: string[] = [];

  if (endpoint.auth.includes('Bearer')) {
    headerLines.push(`-H "Authorization: Bearer <access_token>"`);
  } else if (endpoint.auth === 'X-API-Key') {
    headerLines.push(`-H "X-API-Key: <public_api_key>"`);
  }

  if (contentType === 'multipart/form-data') {
    const formLine = endpoint.request?.includes('files[]')
      ? '-F "files=@/path/to/file-1.pdf" -F "files=@/path/to/file-2.docx"'
      : '-F "file=@/path/to/file.pdf"';
    return [`curl -X ${endpoint.method} "${url}"`, ...headerLines, formLine].join(' \\\n  ');
  }

  if (contentType === 'application/json') {
    headerLines.push('-H "Content-Type: application/json"');
  }

  const dataLine = contentType === 'application/json' && endpoint.exampleBody
    ? `-d '${endpoint.exampleBody.replace(/\n/g, '')}'`
    : '';

  return [`curl -X ${endpoint.method} "${url}"`, ...headerLines, dataLine].filter(Boolean).join(' \\\n  ');
}

export function ApiDocsPage() {
  const [activeModule, setActiveModule] = useState<string>('all');
  const [keyword, setKeyword] = useState('');
  const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://127.0.0.1:8011/api/v1';
  const totalEndpointCount = API_MODULES.reduce((sum, module) => sum + module.endpoints.length, 0);
  const visibleModules = API_MODULES
    .filter((module) => activeModule === 'all' || module.key === activeModule)
    .map((module) => ({
      ...module,
      endpoints: module.endpoints.filter((endpoint) => matchesKeyword(endpoint, keyword)),
    }))
    .filter((module) => module.endpoints.length > 0);

  const visibleEndpointCount = visibleModules.reduce((sum, module) => sum + module.endpoints.length, 0);

  return (
    <main className="app-shell px-4 py-4 text-ink lg:px-5">
      <div className="mx-auto flex min-h-screen max-w-[1380px] flex-col gap-5">
        <header className="flex animate-fade-up flex-wrap items-start justify-between gap-3 px-1 pt-2">
          <div>
            <p className="eyebrow">开发者文档</p>
            <h1 className="mt-3 text-[34px] font-semibold leading-[1.04] tracking-[-0.05em] text-ink lg:text-[42px]">
              API 文档
            </h1>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-steel">
              按项目当前前端 service 和后端已预留接口整理，适合联调、查路径、看鉴权方式和快速确认请求结构。
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link className="action-secondary" to="/">
              返回首页
            </Link>
            <Link className="action-primary" to="/login">
              登录联调
            </Link>
          </div>
        </header>

        <section className="surface animate-fade-up px-6 py-6 lg:px-7" style={{ animationDelay: '60ms' }}>
          <div className="grid gap-6 lg:grid-cols-[1.08fr_0.92fr]">
            <div>
              <p className="eyebrow">接入信息</p>
              <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">先看基础约定</h2>
              <div className="mt-5 grid gap-3">
                {[
                  ['Base URL', baseUrl],
                  ['Bearer 鉴权', 'Authorization: Bearer <access_token>'],
                  ['公开接口鉴权', 'X-API-Key: <public_api_key>'],
                  ['JSON 请求', 'Content-Type: application/json'],
                  ['文件上传', 'multipart/form-data，交给 FormData 自动生成边界'],
                ].map(([label, value]) => (
                  <div className="surface-subtle px-4 py-4" key={label}>
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-placeholder">{label}</p>
                    <code style={{ display: 'block', marginTop: 10, fontSize: 13, lineHeight: 1.8, color: 'var(--color-ink)', wordBreak: 'break-all' }}>
                      {value}
                    </code>
                  </div>
                ))}
              </div>
            </div>

            <div className="surface-subtle p-5">
              <p className="eyebrow">说明</p>
              <div className="mt-4 space-y-3">
                {[
                  ['返回格式', '绝大多数接口返回 schema 对应的 JSON；导入模板与导出报告返回文件流。'],
                  ['错误处理', '未登录常见为 401，权限不足为 403，资源不存在为 404，参数错误通常为 400。'],
                  ['长耗时接口', '评估生成、GitHub 导入、文件解析和调薪推荐已在前端放宽超时设置。'],
                  ['调用建议', '先拿 /auth/login 换 token，再带 Bearer 调业务接口；公开接口则改用 X-API-Key。'],
                ].map(([title, description]) => (
                  <div className="surface px-4 py-4" key={title}>
                    <p className="text-sm font-medium text-ink">{title}</p>
                    <p className="mt-1 text-sm leading-6 text-steel">{description}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* === External API Guide Sections === */}
        <section className="surface animate-fade-up px-6 py-6 lg:px-7" style={{ animationDelay: '80ms' }}>
          <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 14, marginBottom: 20 }}>
            <p className="eyebrow">外部 API 指南</p>
            <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">快速开始</h2>
            <p className="mt-2 text-sm leading-6 text-steel">三步完成外部系统对接。</p>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {[
              ['01', '获取 API Key', '联系管理员在「API Key 管理」页面创建 Key，创建后一次性显示明文，请妥善保存。'],
              ['02', '调用接口', '使用 X-API-Key 请求头访问 /api/v1/public/ 下的端点，拉取已审批调薪数据。'],
              ['03', '分页遍历', '使用游标分页参数（cursor, page_size）遍历全部结果，直到 has_more 为 false。'],
            ].map(([step, title, desc]) => (
              <div className="surface-subtle px-5 py-5" key={step}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 32, height: 32, borderRadius: 8, background: 'var(--color-primary-light)', fontSize: 13, fontWeight: 700, color: 'var(--color-primary)' }}>{step}</span>
                  <span className="text-sm font-semibold text-ink">{title}</span>
                </div>
                <p className="text-sm leading-6 text-steel">{desc}</p>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 20 }}>
            <p className="text-sm font-semibold text-ink" style={{ marginBottom: 8 }}>完整 curl 示例</p>
            <pre style={{ overflowX: 'auto', borderRadius: 8, background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', padding: '14px 16px', fontSize: 12.5, lineHeight: 1.75, color: 'var(--color-ink)' }}>
              <code>{`curl -H "X-API-Key: your_api_key_here" \\
  "${baseUrl.replace('/api/v1', '')}/api/v1/public/salary-results?page_size=50"

# 带游标翻页
curl -H "X-API-Key: your_api_key_here" \\
  "${baseUrl.replace('/api/v1', '')}/api/v1/public/salary-results?page_size=50&cursor=<next_cursor>"`}</code>
            </pre>
          </div>
        </section>

        <section className="surface animate-fade-up px-6 py-6 lg:px-7" style={{ animationDelay: '90ms' }}>
          <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 14, marginBottom: 20 }}>
            <p className="eyebrow">认证方式</p>
            <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">外部 API 认证</h2>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="surface-subtle px-5 py-5">
              <p className="text-sm font-semibold text-ink">请求方式</p>
              <p className="mt-2 text-sm leading-6 text-steel">
                所有 <code style={{ padding: '1px 4px', borderRadius: 3, background: 'var(--color-bg-subtle)', fontSize: 12 }}>/api/v1/public/</code> 端点需要在请求头中携带 API Key。
              </p>
              <pre style={{ marginTop: 12, overflowX: 'auto', borderRadius: 8, background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', padding: '12px 14px', fontSize: 12.5, lineHeight: 1.7, color: 'var(--color-ink)' }}>
                <code>{`curl -H "X-API-Key: your_api_key_here" \\
  ${baseUrl.replace('/api/v1', '')}/api/v1/public/salary-results`}</code>
              </pre>
              <p className="mt-3 text-sm leading-6 text-steel">API Key 由管理员在「API Key 管理」页面创建，每个 Key 拥有独立的限流额度。</p>
            </div>

            <div className="surface-subtle px-5 py-5">
              <p className="text-sm font-semibold text-ink">错误码说明</p>
              <div className="mt-3 space-y-2">
                {[
                  ['401', 'Key 无效、已撤销或已过期'],
                  ['403', '权限不足，无法访问该资源'],
                  ['404', '资源不存在'],
                  ['429', '超过限流，请降低请求频率后重试'],
                ].map(([code, desc]) => (
                  <div key={code} style={{ display: 'flex', gap: 10, alignItems: 'baseline' }}>
                    <code style={{ fontSize: 13, fontWeight: 600, color: Number(code) >= 400 ? 'var(--color-danger)' : 'var(--color-ink)' }}>{code}</code>
                    <span className="text-sm text-steel">{desc}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="surface animate-fade-up px-6 py-6 lg:px-7" style={{ animationDelay: '100ms' }}>
          <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 14, marginBottom: 20 }}>
            <p className="eyebrow">分页方式</p>
            <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">游标分页</h2>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="surface-subtle px-5 py-5">
              <p className="text-sm font-semibold text-ink">参数说明</p>
              <div className="mt-3 space-y-2">
                {[
                  ['cursor', '分页游标（首次请求不传，后续使用响应中的 next_cursor）'],
                  ['page_size', '每页条数，默认 20，最大 100'],
                ].map(([param, desc]) => (
                  <div key={param} style={{ display: 'flex', gap: 10, alignItems: 'baseline' }}>
                    <code style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-primary)' }}>{param}</code>
                    <span className="text-sm text-steel">{desc}</span>
                  </div>
                ))}
              </div>
              <p className="mt-4 text-sm font-semibold text-ink">响应结构</p>
              <div className="mt-2 space-y-2">
                {[
                  ['items', '当前页数据数组'],
                  ['next_cursor', '下一页游标（最后一页为 null）'],
                  ['has_more', '是否还有更多数据（boolean）'],
                ].map(([field, desc]) => (
                  <div key={field} style={{ display: 'flex', gap: 10, alignItems: 'baseline' }}>
                    <code style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-primary)' }}>{field}</code>
                    <span className="text-sm text-steel">{desc}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="surface-subtle px-5 py-5">
              <p className="text-sm font-semibold text-ink">Python 遍历示例</p>
              <pre style={{ marginTop: 10, overflowX: 'auto', borderRadius: 8, background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', padding: '12px 14px', fontSize: 12.5, lineHeight: 1.7, color: 'var(--color-ink)' }}>
                <code>{`import requests

url = "${baseUrl.replace('/api/v1', '')}/api/v1/public/salary-results"
headers = {"X-API-Key": "your_api_key_here"}
cursor = None

while True:
    params = {"page_size": 50}
    if cursor:
        params["cursor"] = cursor
    resp = requests.get(url, headers=headers, params=params)
    data = resp.json()
    process(data["items"])
    if not data["has_more"]:
        break
    cursor = data["next_cursor"]`}</code>
              </pre>
            </div>
          </div>
        </section>

        <section className="surface animate-fade-up px-6 py-6 lg:px-7" style={{ animationDelay: '105ms' }}>
          <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 14, marginBottom: 20 }}>
            <p className="eyebrow">端点参考</p>
            <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">公开 API 端点</h2>
          </div>

          <div className="space-y-4">
            {[
              {
                method: 'GET',
                path: '/api/v1/public/salary-results',
                desc: '获取已审批的调薪结果（支持游标分页）',
                params: 'cursor, page_size, cycle_id, department',
                response: '{ items: SalaryResult[], next_cursor, has_more }',
                example: `curl -H "X-API-Key: key" "${baseUrl.replace('/api/v1', '')}/api/v1/public/salary-results?page_size=20"`,
              },
              {
                method: 'GET',
                path: '/api/v1/public/evaluations/latest',
                desc: '获取员工最新评估结果',
                params: 'employee_ids (逗号分隔)',
                response: 'LatestEvaluation[]',
                example: `curl -H "X-API-Key: key" "${baseUrl.replace('/api/v1', '')}/api/v1/public/evaluations/latest?employee_ids=id1,id2"`,
              },
              {
                method: 'GET',
                path: '/api/v1/public/evaluations/{evaluation_id}',
                desc: '获取指定评估详情',
                params: 'evaluation_id (路径参数)',
                response: 'EvaluationDetail',
                example: `curl -H "X-API-Key: key" "${baseUrl.replace('/api/v1', '')}/api/v1/public/evaluations/eval_001"`,
              },
              {
                method: 'GET',
                path: '/api/v1/public/cycles',
                desc: '获取评估周期列表',
                params: '无',
                response: 'Cycle[]',
                example: `curl -H "X-API-Key: key" "${baseUrl.replace('/api/v1', '')}/api/v1/public/cycles"`,
              },
            ].map((ep) => (
              <div className="surface-subtle px-5 py-4" key={ep.path}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700, background: ep.method === 'GET' ? '#e6f7ff' : '#fff7e6', color: ep.method === 'GET' ? '#0050b3' : '#d46b08' }}>{ep.method}</span>
                  <code style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-ink)' }}>{ep.path}</code>
                </div>
                <p className="mt-2 text-sm text-steel">{ep.desc}</p>
                <div className="mt-3 grid gap-2 md:grid-cols-2">
                  <div>
                    <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-placeholder)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>参数</p>
                    <p className="mt-1 text-sm text-steel">{ep.params}</p>
                  </div>
                  <div>
                    <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-placeholder)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>响应</p>
                    <p className="mt-1 text-sm text-steel">{ep.response}</p>
                  </div>
                </div>
                <pre style={{ marginTop: 10, overflowX: 'auto', borderRadius: 6, background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', padding: '8px 12px', fontSize: 12, lineHeight: 1.6, color: 'var(--color-ink)' }}>
                  <code>{ep.example}</code>
                </pre>
              </div>
            ))}
          </div>
        </section>

        <section className="surface animate-fade-up px-6 py-6 lg:px-7" style={{ animationDelay: '110ms' }}>
          <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 14, marginBottom: 20 }}>
            <p className="eyebrow">推送模式</p>
            <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">Webhook 通知</h2>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="surface-subtle px-5 py-5">
              <p className="text-sm font-semibold text-ink">工作方式</p>
              <p className="mt-2 text-sm leading-6 text-steel">
                管理员可在「Webhook 管理」页面注册回调 URL。当调薪建议审批通过（<code style={{ padding: '1px 4px', borderRadius: 3, background: 'var(--color-bg-subtle)', fontSize: 12 }}>recommendation.approved</code>）时，系统会自动 POST 事件数据到注册的 URL。
              </p>
              <p className="mt-3 text-sm leading-6 text-steel">
                每次投递会携带 <code style={{ padding: '1px 4px', borderRadius: 3, background: 'var(--color-bg-subtle)', fontSize: 12 }}>X-Signature-256</code> 请求头，值为 <code style={{ padding: '1px 4px', borderRadius: 3, background: 'var(--color-bg-subtle)', fontSize: 12 }}>sha256=hmac_hex</code> 格式的 HMAC 签名，用于接收端验证请求来源。
              </p>
              <p className="mt-3 text-sm leading-6 text-steel">投递失败时最多重试 3 次，间隔分别为 1s、5s、30s。可在投递日志中查看每次投递的详情。</p>
            </div>

            <div className="surface-subtle px-5 py-5">
              <p className="text-sm font-semibold text-ink">Python Flask 签名验证示例</p>
              <pre style={{ marginTop: 10, overflowX: 'auto', borderRadius: 8, background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', padding: '12px 14px', fontSize: 12.5, lineHeight: 1.7, color: 'var(--color-ink)' }}>
                <code>{`import hmac, hashlib

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

# Flask example
@app.route("/webhook", methods=["POST"])
def handle_webhook():
    sig = request.headers.get("X-Signature-256", "")
    if not verify_signature(request.data, sig, WEBHOOK_SECRET):
        abort(401)
    event = request.json
    # Process event...
    return "", 200`}</code>
              </pre>
            </div>
          </div>
        </section>
        {/* === End External API Guide === */}

        <section className="metric-strip animate-fade-up" style={{ animationDelay: '120ms' }}>
          {[
            [String(API_MODULES.length), '接口分组', '按业务模块拆分查看。'],
            [String(totalEndpointCount), '收录接口', '包含前端已接入和已预留接口。'],
            [String(visibleEndpointCount), '当前结果', keyword || activeModule !== 'all' ? '按筛选条件显示。' : '默认显示全部接口。'],
          ].map(([value, label, note]) => (
            <article className="metric-tile" key={label}>
              <p className="metric-label">{label}</p>
              <p className="metric-value text-[28px]">{value}</p>
              <p className="metric-note">{note}</p>
            </article>
          ))}
        </section>

        <section className="surface animate-fade-up px-6 py-6 lg:px-7" style={{ animationDelay: '180ms' }}>
          <div className="section-head">
            <div>
              <p className="eyebrow">快速筛选</p>
              <h2 className="section-title">按模块和关键词查接口</h2>
            </div>
            <p className="section-note">支持按路径、用途、鉴权方式、请求体关键词筛选。</p>
          </div>

          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto]">
            <input
              className="toolbar-input"
              onChange={(event) => setKeyword(event.target.value)}
              placeholder="例如：salary、manual-review、X-API-Key、multipart"
              type="text"
              value={keyword}
            />
            <div className="flex flex-wrap gap-2">
              <button
                className={`chip-button${activeModule === 'all' ? ' chip-button-active' : ''}`}
                onClick={() => setActiveModule('all')}
                type="button"
              >
                全部
              </button>
              {API_MODULES.map((module) => (
                <button
                  className={`chip-button${activeModule === module.key ? ' chip-button-active' : ''}`}
                  key={module.key}
                  onClick={() => setActiveModule(module.key)}
                  type="button"
                >
                  {module.title}
                </button>
              ))}
            </div>
          </div>
        </section>

        <section className="surface animate-fade-up px-6 py-6 lg:px-7" style={{ animationDelay: '220ms' }}>
          <div className="section-head">
            <div>
              <p className="eyebrow">调用方式</p>
              <h2 className="section-title">先统一这几种请求写法</h2>
            </div>
            <p className="section-note">文档下方每条接口也都补了对应示例。</p>
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            <article className="surface-subtle px-4 py-4">
              <p className="text-sm font-medium text-ink">JSON 接口</p>
              <p className="mt-1 text-sm leading-6 text-steel">登录、评估、调薪、审批大多走 JSON 请求体。</p>
              <pre style={{ marginTop: 12, overflowX: 'auto', borderRadius: 8, background: '#fff', border: '1px solid var(--color-border)', padding: '12px 14px', fontSize: 12.5, lineHeight: 1.7, color: 'var(--color-ink)' }}>
                <code>{`await fetch('${baseUrl}/salary/recommend', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer <access_token>',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ evaluation_id: 'eval_001' })
});`}</code>
              </pre>
            </article>

            <article className="surface-subtle px-4 py-4">
              <p className="text-sm font-medium text-ink">文件上传</p>
              <p className="mt-1 text-sm leading-6 text-steel">材料、员工手册、导入任务都建议使用 FormData。</p>
              <pre style={{ marginTop: 12, overflowX: 'auto', borderRadius: 8, background: '#fff', border: '1px solid var(--color-border)', padding: '12px 14px', fontSize: 12.5, lineHeight: 1.7, color: 'var(--color-ink)' }}>
                <code>{`const formData = new FormData();
formData.append('file', file);

await fetch('${baseUrl}/handbooks', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer <access_token>'
  },
  body: formData
});`}</code>
              </pre>
            </article>

            <article className="surface-subtle px-4 py-4">
              <p className="text-sm font-medium text-ink">公开接口</p>
              <p className="mt-1 text-sm leading-6 text-steel">给外部系统用，不走 Bearer，改用 `X-API-Key`。</p>
              <pre style={{ marginTop: 12, overflowX: 'auto', borderRadius: 8, background: '#fff', border: '1px solid var(--color-border)', padding: '12px 14px', fontSize: 12.5, lineHeight: 1.7, color: 'var(--color-ink)' }}>
                <code>{`await fetch('${baseUrl}/public/dashboard/summary', {
  method: 'GET',
  headers: {
    'X-API-Key': '<public_api_key>'
  }
});`}</code>
              </pre>
            </article>
          </div>
        </section>

        <div className="grid gap-5 xl:grid-cols-[250px_minmax(0,1fr)]">
          <aside className="surface animate-fade-up px-5 py-5 xl:sticky xl:top-5 xl:self-start" style={{ animationDelay: '240ms' }}>
            <p className="eyebrow">目录</p>
            <div className="mt-4 space-y-2">
              {visibleModules.map((module) => (
                <a
                  href={`#api-${module.key}`}
                  key={module.key}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 12,
                    padding: '10px 12px',
                    borderRadius: 8,
                    border: '1px solid var(--color-border)',
                    background: 'var(--color-bg-surface)',
                    color: 'var(--color-ink)',
                    textDecoration: 'none',
                  }}
                >
                  <span style={{ fontSize: 13.5, fontWeight: 500 }}>{module.title}</span>
                  <span style={{ fontSize: 12, color: 'var(--color-steel)' }}>{module.endpoints.length}</span>
                </a>
              ))}
            </div>
          </aside>

          <div className="space-y-5">
            {visibleModules.length === 0 ? (
              <section className="surface animate-fade-up px-6 py-8 text-center" style={{ animationDelay: '260ms' }}>
                <p className="text-base font-semibold text-ink">没有匹配的接口</p>
                <p className="mt-2 text-sm text-steel">可以换个关键词，或者切回全部模块查看。</p>
              </section>
            ) : null}

            {visibleModules.map((module, moduleIndex) => (
              <section
                className="surface animate-fade-up px-6 py-6 lg:px-7"
                id={`api-${module.key}`}
                key={module.key}
                style={{ animationDelay: `${280 + moduleIndex * 40}ms` }}
              >
                <div className="section-head">
                  <div>
                    <p className="eyebrow">{module.tag}</p>
                    <h2 className="mt-2 text-[22px] font-semibold tracking-[-0.03em] text-ink">{module.title}</h2>
                    <p className="mt-2 text-sm leading-6 text-steel">{module.summary}</p>
                  </div>
                  <div className="surface-subtle px-4 py-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-placeholder">接口数</p>
                    <p className="mt-2 text-[22px] font-semibold leading-none text-ink">{module.endpoints.length}</p>
                  </div>
                </div>

                <div className="space-y-3">
                  {module.endpoints.map((endpoint) => {
                    const methodStyle = METHOD_STYLES[endpoint.method];

                    return (
                      <article className="surface-subtle px-4 py-4 lg:px-5" key={`${endpoint.method}-${endpoint.path}`}>
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="flex min-w-0 flex-wrap items-center gap-2">
                            <span
                              style={{
                                borderRadius: 999,
                                border: `1px solid ${methodStyle.border}`,
                                background: methodStyle.background,
                                color: methodStyle.color,
                                padding: '4px 10px',
                                fontSize: 12,
                                fontWeight: 700,
                                letterSpacing: '0.04em',
                              }}
                            >
                              {endpoint.method}
                            </span>
                            <code
                              style={{
                                borderRadius: 8,
                                border: '1px solid var(--color-border)',
                                background: '#FFFFFF',
                                padding: '7px 10px',
                                fontSize: 13,
                                color: 'var(--color-ink)',
                                wordBreak: 'break-all',
                              }}
                            >
                              {endpoint.path}
                            </code>
                          </div>
                          <span
                            style={{
                              borderRadius: 999,
                              background: 'var(--color-bg-surface)',
                              border: '1px solid var(--color-border)',
                              padding: '4px 10px',
                              fontSize: 12,
                              color: 'var(--color-steel)',
                            }}
                          >
                            {endpoint.auth}
                          </span>
                        </div>

                        <p className="mt-4 text-sm font-medium text-ink">{endpoint.summary}</p>

                        <div className="mt-4 grid gap-3 lg:grid-cols-2">
                          {endpoint.params ? (
                            <div className="surface px-4 py-3">
                              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-placeholder">Query / Path</p>
                              <p className="mt-2 text-sm leading-6 text-steel">{endpoint.params}</p>
                            </div>
                          ) : null}
                          {endpoint.request ? (
                            <div className="surface px-4 py-3">
                              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-placeholder">Request</p>
                              <p className="mt-2 text-sm leading-6 text-steel">{endpoint.request}</p>
                            </div>
                          ) : null}
                          <div className="surface px-4 py-3">
                            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-placeholder">Response</p>
                            <p className="mt-2 text-sm leading-6 text-steel">{endpoint.response}</p>
                          </div>
                          <div className="surface px-4 py-3">
                            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-placeholder">Call</p>
                            <p className="mt-2 text-sm leading-6 text-steel">
                              {endpoint.method} {getExampleUrl(baseUrl, endpoint)}
                            </p>
                            <p className="mt-1 text-sm leading-6 text-steel">
                              Headers: {getHeaderLines(endpoint).length > 0 ? getHeaderLines(endpoint).join(' / ') : '无额外请求头'}
                            </p>
                            <p className="mt-1 text-sm leading-6 text-steel">
                              Body: {getContentType(endpoint) === 'none' ? '无请求体' : getContentType(endpoint)}
                            </p>
                          </div>
                          {endpoint.service ? (
                            <div className="surface px-4 py-3">
                              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-placeholder">Frontend Usage</p>
                              <p className="mt-2 text-sm leading-6 text-steel">{endpoint.service}</p>
                            </div>
                          ) : null}
                          {endpoint.note ? (
                            <div className="surface px-4 py-3">
                              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-placeholder">Note</p>
                              <p className="mt-2 text-sm leading-6 text-steel">{endpoint.note}</p>
                            </div>
                          ) : null}
                        </div>

                        <details style={{ marginTop: 14 }}>
                          <summary style={{ cursor: 'pointer', fontSize: 13, fontWeight: 600, color: 'var(--color-primary)' }}>
                            查看调用示例
                          </summary>
                          <div className="mt-3 grid gap-3 xl:grid-cols-2">
                            <div className="surface px-4 py-4">
                              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-placeholder">Fetch</p>
                              <pre style={{ marginTop: 10, overflowX: 'auto', fontSize: 12.5, lineHeight: 1.75, color: 'var(--color-ink)' }}>
                                <code>{buildFetchSnippet(baseUrl, endpoint)}</code>
                              </pre>
                            </div>
                            <div className="surface px-4 py-4">
                              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-placeholder">cURL</p>
                              <pre style={{ marginTop: 10, overflowX: 'auto', fontSize: 12.5, lineHeight: 1.75, color: 'var(--color-ink)' }}>
                                <code>{buildCurlSnippet(baseUrl, endpoint)}</code>
                              </pre>
                            </div>
                          </div>
                        </details>
                      </article>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
