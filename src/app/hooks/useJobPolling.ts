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

  const poll = useCallback(async () => {
    if (!runId || !enabled) return;

    try {
      const job = jobId
        ? await jobsApi.getJob(jobId)
        : await jobsApi.getLatestJob(runId);

      if (!job || !isMountedRef.current) return;

      onUpdate?.(job);

      if (TERMINAL_STATUSES.includes(job.status)) {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        if (job.status === "completed") {
          onComplete?.(job);
        } else if (job.status === "failed") {
          onError?.(job);
        }
      }
    } catch {
      // Polling errors are silent — job may not exist yet
    }
  }, [runId, jobId, enabled, onUpdate, onComplete, onError]);

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
