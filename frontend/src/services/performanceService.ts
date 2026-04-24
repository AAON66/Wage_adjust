import axios from 'axios';

import api from './api';
import type {
  AvailableYearsResponse,
  MyTierResponse,
  NoSnapshotErrorDetail,
  PerformanceHistoryResponse,
  PerformanceRecordCreatePayload,
  PerformanceRecordItem,
  PerformanceRecordsListResponse,
  RecomputeTriggerResponse,
  TierRecomputeBusyDetail,
  TierSummaryResponse,
} from '../types/api';

/**
 * 重算重算超时缓冲：后端 D-03 5s + 网络往返；前端 axios 默认 10s 不够稳。
 * 给 30s 缓冲覆盖最坏情况（全公司 5000 员工 + 慢网）。
 */
const LONG_RECOMPUTE_TIMEOUT = 30000;

/**
 * D-10：tier-summary 404 no_snapshot 时抛此错。
 * 调用方据此分支渲染「立即生成档次」空状态。
 */
export class NoSnapshotError extends Error {
  readonly year: number;
  readonly hint: string;

  constructor(year: number, hint: string, message: string) {
    super(message);
    this.name = 'NoSnapshotError';
    this.year = year;
    this.hint = hint;
  }
}

/**
 * D-06：recompute-tiers 409 tier_recompute_busy 时抛此错。
 * 调用方据此分支显示「系统正在自动重算，请稍后重试」+ 5 秒后启用按钮。
 */
export class TierRecomputeBusyError extends Error {
  readonly year: number;
  readonly retryAfterSeconds: number;

  constructor(year: number, retryAfterSeconds: number, message: string) {
    super(message);
    this.name = 'TierRecomputeBusyError';
    this.year = year;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

interface ErrorDetailEnvelope<T> {
  detail?: T;
  error?: string;
  message?: string;
  year?: number;
  hint?: string;
  retry_after_seconds?: number;
}

function extractDetail<T>(payload: unknown): T | null {
  if (payload && typeof payload === 'object') {
    const env = payload as ErrorDetailEnvelope<T>;
    if (env.detail && typeof env.detail === 'object') {
      return env.detail as T;
    }
    // http_exception_handler 在 detail 是 dict 时直接返回 content（无 detail 包裹）
    if ('error' in env) {
      return payload as T;
    }
  }
  return null;
}

/** GET /performance/tier-summary?year=X */
export async function getTierSummary(year: number): Promise<TierSummaryResponse> {
  try {
    const { data } = await api.get<TierSummaryResponse>('/performance/tier-summary', {
      params: { year },
    });
    return data;
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 404) {
      const detail = extractDetail<NoSnapshotErrorDetail>(err.response.data);
      if (detail && detail.error === 'no_snapshot') {
        throw new NoSnapshotError(detail.year, detail.hint, detail.message);
      }
    }
    throw err;
  }
}

/** POST /performance/recompute-tiers?year=X — 含 30s 长超时 */
export async function recomputeTiers(year: number): Promise<RecomputeTriggerResponse> {
  try {
    const { data } = await api.post<RecomputeTriggerResponse>(
      '/performance/recompute-tiers',
      undefined,
      { params: { year }, timeout: LONG_RECOMPUTE_TIMEOUT },
    );
    return data;
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.status === 409) {
      const detail = extractDetail<TierRecomputeBusyDetail>(err.response.data);
      if (detail && detail.error === 'tier_recompute_busy') {
        throw new TierRecomputeBusyError(
          detail.year,
          detail.retry_after_seconds ?? 5,
          detail.message,
        );
      }
    }
    throw err;
  }
}

interface RecordsQuery {
  year?: number | null;
  department?: string | null;
  page?: number;
  page_size?: number;
}

/** GET /performance/records?year=X&department=Y&page=N&page_size=50 */
export async function getPerformanceRecords(
  query: RecordsQuery = {},
): Promise<PerformanceRecordsListResponse> {
  const params: Record<string, string | number> = {};
  if (query.year != null) params.year = query.year;
  if (query.department) params.department = query.department;
  if (query.page != null) params.page = query.page;
  if (query.page_size != null) params.page_size = query.page_size;
  const { data } = await api.get<PerformanceRecordsListResponse>('/performance/records', {
    params,
  });
  return data;
}

/** POST /performance/records — 单条新增 */
export async function createPerformanceRecord(
  payload: PerformanceRecordCreatePayload,
): Promise<PerformanceRecordItem> {
  const { data } = await api.post<PerformanceRecordItem>('/performance/records', payload);
  return data;
}

/**
 * B-3：GET /performance/available-years
 * 替代「拉 200 条 records 凑 distinct」的旧 hack。
 * 后端在表为空时返回 [今年] 兜底，前端再叠一层 fallback 防御网络异常。
 */
export async function getAvailableYears(): Promise<number[]> {
  const { data } = await api.get<AvailableYearsResponse>('/performance/available-years');
  return data.years;
}

/**
 * Phase 35 D-11: 员工自助查询本人绩效档次（无参数路由，ESELF-03 / ESELF-04）
 *
 * 后端端点：GET /api/v1/performance/me/tier
 * 错误码：
 *   - 401 未鉴权（axios 拦截器可能触发 token refresh）
 *   - 422 未绑定员工 → 前端展示「请前往账号设置绑定」
 *   - 404 员工档案缺失 → 前端展示「员工档案缺失，请联系 HR」
 *   - 500 服务异常 → 前端展示通用错误 + 重试按钮
 *
 * 不做 try/catch —— axios 异常原样 throw，由调用方（MyPerformanceTierBadge 组件）
 * 负责按 status code 分支渲染。
 */
export async function fetchMyTier(): Promise<MyTierResponse> {
  const { data } = await api.get<MyTierResponse>('/performance/me/tier');
  return data;
}

/**
 * Phase 36 D-04 / D-05：按员工拉取历史绩效（year DESC，不分页）。
 * 权限：admin/hrbp/manager；employee 403；manager 跨部门 403；不存在员工 404。
 * 错误由 axios interceptor 处理 401；其它错误抛 AxiosError 给调用方 catch。
 */
export async function fetchPerformanceHistoryByEmployee(
  employeeId: string,
): Promise<PerformanceHistoryResponse> {
  const { data } = await api.get<PerformanceHistoryResponse>(
    `/performance/records/by-employee/${encodeURIComponent(employeeId)}`,
  );
  return data;
}
