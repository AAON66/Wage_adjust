import { useEffect, useRef, useState } from 'react';
import { fetchTaskStatus } from '../services/taskService';
import type { TaskStatusResponse } from '../types/api';

interface UseTaskPollingOptions {
  onComplete: (result: unknown) => void;
  onError: (error: string) => void;
  onProgress?: (progress: { processed: number; total: number; errors: number }) => void;
}

export function useTaskPolling(taskId: string | null, options: UseTaskPollingOptions): TaskStatusResponse | null {
  const [status, setStatus] = useState<TaskStatusResponse | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  useEffect(() => {
    if (!taskId) {
      setStatus(null);
      return;
    }

    let cancelled = false;

    const interval = setInterval(async () => {
      try {
        const taskStatus = await fetchTaskStatus(taskId);
        if (cancelled) return;
        setStatus(taskStatus);

        if (taskStatus.status === 'completed') {
          clearInterval(interval);
          optionsRef.current.onComplete(taskStatus.result);
        } else if (taskStatus.status === 'failed') {
          clearInterval(interval);
          optionsRef.current.onError(taskStatus.error ?? '任务执行失败');
        } else if (taskStatus.progress) {
          optionsRef.current.onProgress?.(taskStatus.progress);
        }
      } catch {
        // 网络错误时不停止轮询，继续重试
      }
    }, 2000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [taskId]);

  return status;
}
