import { apiClient } from "./client";
import type {
  IntakeRun,
  IntakeRunSummary,
  CreateRunPayload,
  ArtifactRecord,
  ArtifactType,
  Approval,
  ApprovalDecision,
} from "../types/api";

export const runsApi = {
  list(): Promise<IntakeRunSummary[]> {
    return apiClient.get<IntakeRunSummary[]>("/runs");
  },

  get(runId: string): Promise<IntakeRun> {
    return apiClient.get<IntakeRun>(`/runs/${runId}`);
  },

  create(payload: CreateRunPayload): Promise<IntakeRun> {
    return apiClient.post<IntakeRun>("/runs", payload);
  },

  cancel(runId: string): Promise<void> {
    return apiClient.post<void>(`/runs/${runId}/cancel`);
  },

  delete(runId: string): Promise<void> {
    return apiClient.delete<void>(`/runs/${runId}`);
  },

  getArtifacts(runId: string): Promise<ArtifactRecord[]> {
    return apiClient.get<ArtifactRecord[]>(`/runs/${runId}/artifacts`);
  },

  getArtifact(runId: string, artifactType: ArtifactType): Promise<ArtifactRecord> {
    return apiClient.get<ArtifactRecord>(`/runs/${runId}/artifacts/${artifactType}`);
  },

  regenerateArtifact(runId: string, artifactType: ArtifactType): Promise<{ job_id: string }> {
    return apiClient.post<{ job_id: string }>(
      `/runs/${runId}/artifacts/${artifactType}/regenerate`,
    );
  },

  submitApproval(
    runId: string,
    decision: ApprovalDecision,
    comment?: string,
  ): Promise<Approval> {
    return apiClient.post<Approval>(`/runs/${runId}/approval`, { decision, comment });
  },

  getApprovals(runId: string): Promise<Approval[]> {
    return apiClient.get<Approval[]>(`/runs/${runId}/approvals`);
  },
};
