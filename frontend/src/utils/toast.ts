/**
 * W-4 修复：单实例 toast helper，避免多次 alert 同时触发卡浏览器。
 *
 * MVP 占位：浏览器原生 alert + console 标 variant 便于调试。
 * TODO Phase 35+: 替换为正式 toast 库（如 sonner / react-hot-toast）。
 */

let activeTimeoutId: number | null = null;

export type ToastVariant = 'success' | 'info' | 'warning' | 'error';

/**
 * 显示一条 toast；若上一条 toast 还未弹出（未达 setTimeout 调度时刻），则取消。
 *
 * 注意：浏览器 alert 是同步阻塞 modal，没有「正在显示」的 cancel 概念；
 * 这里 cancel 的是「计划中的 alert 调度」，避免短时间内连续多次 alert 排队卡死。
 */
export function showToast(message: string, variant: ToastVariant = 'info'): void {
  // 取消上一个尚未显示的 toast
  if (activeTimeoutId !== null) {
    window.clearTimeout(activeTimeoutId);
    activeTimeoutId = null;
  }

  // 用 console 标 variant 便于调试（正式 toast 会替换此实现）
  console.log(`[toast/${variant}]`, message);

  // 单帧延迟，确保上一个 alert 已被关闭
  activeTimeoutId = window.setTimeout(() => {
    window.alert(message);
    activeTimeoutId = null;
  }, 0);
}
