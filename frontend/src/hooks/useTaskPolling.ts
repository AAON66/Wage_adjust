import { useCallback, useEffect, useRef, useState } from 'react';

import api from '../services/api';

interface TaskProgress {
  processed: number;
  total: number;
  errors: number;
}

interface TaskStatusPayload {
  task_id: string;
  status: string;
  progress: TaskProgress | null;
  result: unknown;
  error: string | null;
}

interface UseTaskPollingResult {
  status: string | null;
  progress: TaskProgress | null;
  result: unknown;
  error: string | null;
  isPolling: boolean;
}

export function useTaskPolling(
  taskId: string | null,
  options?: { intervalMs?: number },
): UseTaskPollingResult {
  const intervalMs = options?.intervalMs ?? 2000;

  const [status, setStatus] = useState<string | null>(null);
  const [progress, setProgress] = useState<TaskProgress | null>(null);
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cancelledRef = useRef(false);

  const cleanup = useCallback(() => {
    cancelledRef.current = true;
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!taskId) {
      setStatus(null);
      setProgress(null);
      setResult(null);
      setError(null);
      setIsPolling(false);
      return;
    }

    cancelledRef.current = false;
    setIsPolling(true);
    setStatus('pending');
    setProgress(null);
    setResult(null);
    setError(null);

    async function poll() {
      if (cancelledRef.current) return;
      try {
        const response = await api.get<TaskStatusPayload>(`/tasks/${taskId}/status`);
        if (cancelledRef.current) return;

        const data = response.data;
        setStatus(data.status);
        setProgress(data.progress);

        if (data.status === 'completed' || data.status === 'failed') {
          setResult(data.result);
          setError(data.error);
          setIsPolling(false);
          return;
        }

        timerRef.current = setTimeout(() => {
          void poll();
        }, intervalMs);
      } catch (err) {
        if (cancelledRef.current) return;
        setError(err instanceof Error ? err.message : 'Failed to poll task status');
        setIsPolling(false);
      }
    }

    void poll();

    return cleanup;
  }, [taskId, intervalMs, cleanup]);

  return { status, progress, result, error, isPolling };
}
