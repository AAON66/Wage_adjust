import { useCallback, useEffect, useRef, useState } from 'react';

interface UsePollingResult<T> {
  data: T | null;
  error: Error | null;
  isServiceUnavailable: boolean;
}

export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
): UsePollingResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isServiceUnavailable, setIsServiceUnavailable] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const stableFetcher = useCallback(fetcher, [fetcher]);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const result = await stableFetcher();
        if (!cancelled && !controller.signal.aborted) {
          setData(result);
          setError(null);
          setIsServiceUnavailable(false);
        }
      } catch (err) {
        if (cancelled || controller.signal.aborted) return;
        if (
          err &&
          typeof err === 'object' &&
          'response' in err &&
          (err as { response?: { status?: number } }).response?.status === 503
        ) {
          setIsServiceUnavailable(true);
          setError(new Error('缓存服务暂时不可用'));
        }
      }
    }

    setData(null);
    setError(null);
    setIsServiceUnavailable(false);

    void poll();
    const id = setInterval(() => void poll(), intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, [stableFetcher, intervalMs]);

  return { data, error, isServiceUnavailable };
}
