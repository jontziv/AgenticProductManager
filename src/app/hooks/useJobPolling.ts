import { useEffect, useRef, useCallback } from "react";
import { jobsApi } from "../api/jobs";
import type { JobRecord, JobStatus } from "../types/api";

const TERMINAL_STATUSES: JobStatus[] = ["completed", "failed", "cancelled"];
const DEFAULT_INTERVAL_MS = 2000;

interface UseJobPollingOptions {
  runId: string | null;
  jobId?: string | null;
  intervalMs?: number;
  onUpdate?: (job: JobRecord) => void;
  onComplete?: (job: JobRecord) => void;
  onError?: (job: JobRecord) => void;
  enabled?: boolean;
}

export function useJobPolling({
  runId,
  jobId,
  intervalMs = DEFAULT_INTERVAL_MS,
  onUpdate,
  onComplete,
  onError,
  enabled = true,
}: UseJobPollingOptions) {
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isMountedRef = useRef(true);

  // Store callbacks in refs so the interval doesn't need to restart when the
  // caller's inline functions get new references on every re-render.
  const onUpdateRef = useRef(onUpdate);
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);
  onUpdateRef.current = onUpdate;
  onCompleteRef.current = onComplete;
  onErrorRef.current = onError;

  const poll = useCallback(async () => {
    if (!runId || !enabled) return;

    try {
      const job = jobId
        ? await jobsApi.getJob(jobId)
        : await jobsApi.getLatestJob(runId);

      if (!job || !isMountedRef.current) return;

      onUpdateRef.current?.(job);

      if (TERMINAL_STATUSES.includes(job.status)) {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        if (job.status === "completed") {
          onCompleteRef.current?.(job);
        } else if (job.status === "failed") {
          onErrorRef.current?.(job);
        }
      }
    } catch {
      // Polling errors are silent — job may not exist yet
    }
  }, [runId, jobId, enabled]); // callbacks removed from deps — stored in refs above

  useEffect(() => {
    isMountedRef.current = true;

    if (!runId || !enabled) return;

    poll();
    intervalRef.current = setInterval(poll, intervalMs);

    return () => {
      isMountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [runId, jobId, intervalMs, enabled, poll]);

  const stop = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  return { stop };
}
