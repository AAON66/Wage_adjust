import axios from 'axios';

export type FeishuErrorCode =
  | 'authorization_cancelled'
  | 'employee_not_matched'
  | 'state_invalid_or_expired'
  | 'code_expired_or_replayed'
  | 'redis_unavailable'
  | 'feishu_unreachable'
  | 'network_error'
  | 'sdk_load_failed'
  | 'feishu_already_bound'
  | 'feishu_employee_mismatch'
  | 'unknown_error';

export interface FeishuError {
  code: FeishuErrorCode;
  message: string;
}

const COPY: Record<FeishuErrorCode, string> = {
  authorization_cancelled: '你已取消飞书授权',
  employee_not_matched: '工号未匹配，请联系管理员开通',
  state_invalid_or_expired: '会话已过期，请重新发起授权',
  code_expired_or_replayed: '授权码已失效，请重新登录',
  redis_unavailable: '登录服务暂不可用，请稍后重试',
  feishu_unreachable: '无法连接飞书服务，请稍后重试',
  network_error: '网络错误，请检查连接',
  sdk_load_failed: '飞书登录组件加载失败，请刷新重试',
  feishu_already_bound: '该飞书账号已被其他系统账号绑定，请先在原账号解绑',
  feishu_employee_mismatch: '飞书工号与当前账号绑定的工号不一致，无法绑定',
  unknown_error: '登录失败，请稍后重试',
};

function extractDetail(data: unknown): string {
  if (!data || typeof data !== 'object') return '';
  const maybe = data as { message?: unknown; detail?: unknown };
  // 后端 main.py exception_handler 把 HTTPException.detail 改写为 { error, message } 格式
  if (typeof maybe.message === 'string') return maybe.message;
  if (typeof maybe.detail === 'string') return maybe.detail;
  return '';
}

function classifyBackend(err: unknown): FeishuErrorCode {
  if (!axios.isAxiosError(err)) return 'unknown_error';
  if (!err.response) return 'network_error';

  const status = err.response.status;
  const detail = extractDetail(err.response.data);

  if (status === 503) return 'redis_unavailable';
  if (status === 502) return 'feishu_unreachable';
  if (status === 409) return 'feishu_already_bound';
  if (status === 403) return 'authorization_cancelled';
  if (status === 400) {
    // 特化匹配：绑定路径的工号不一致 / 未关联员工 优先于通用的「工号未匹配」
    if (detail.includes('工号与当前账号')) return 'feishu_employee_mismatch';
    if (detail.includes('当前账号未关联员工信息')) return 'feishu_employee_mismatch';
    if (detail.includes('state')) return 'state_invalid_or_expired';
    if (detail.includes('工号')) return 'employee_not_matched';
    if (detail.includes('授权码')) return 'code_expired_or_replayed';
    return 'unknown_error';
  }
  return 'unknown_error';
}

function classifySdk(payload: unknown): FeishuErrorCode {
  if (payload instanceof Error && payload.message === 'sdk_load_failed') {
    return 'sdk_load_failed';
  }
  return 'unknown_error';
}

export function resolveFeishuError(
  source: 'backend' | 'sdk',
  payload: unknown,
): FeishuError {
  const code = source === 'backend' ? classifyBackend(payload) : classifySdk(payload);
  return { code, message: COPY[code] };
}
