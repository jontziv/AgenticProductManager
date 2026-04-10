import { apiClient } from "./client";
import type { JobRecord, QaReport, ExportRecord, ExportPackRequest } from "../types/api";

export const jobsApi = {
  getJob(jobId: string): Promise<JobRecord> {
    return apiClient.get<JobRecord>(`/jobs/${jobId}`);
  },

  getRunJobs(runId: string): Promise<JobRecord[]> {
    return apiClient.get<JobRecord[]>(`/runs/${runId}/jobs`);
  },

  getLatestJob(runId: string): Promise<JobRecord | null> {
    return apiClient
      .get<JobRecord>(`/runs/${runId}/jobs/latest`)
      .catch(() => null);
  },

  cancelJob(jobId: string): Promise<void> {
    return apiClient.post<void>(`/jobs/${jobId}/cancel`);
  },
};

export const qaApi = {
  getLatestReport(runId: string): Promise<QaReport | null> {
    return apiClient
      .get<QaReport>(`/runs/${runId}/qa`)
      .catch(() => null);
  },

  triggerEvaluation(runId: string): Promise<{ job_id: string }> {
    return apiClient.post<{ job_id: string }>(`/runs/${runId}/qa/evaluate`);
  },
};

export const exportsApi = {
  requestExport(request: ExportPackRequest): Promise<{ job_id: string }> {
    return apiClient.post<{ job_id: string }>("/exports", request);
  },

  getExports(runId: string): Promise<ExportRecord[]> {
    return apiClient.get<ExportRecord[]>(`/runs/${runId}/exports`);
  },
};
