export type EvaluationStatus = "passed" | "failed" | "warning" | "running";

export interface EvaluationCheck {
  id: string;
  name: string;
  description: string;
  status: EvaluationStatus;
  score?: number;
  maxScore?: number;
  findings: string[];
  remediation?: string;
}

export interface EvaluationCategory {
  name: string;
  description: string;
  checks: EvaluationCheck[];
  overallScore: number;
  maxScore: number;
}

export interface EvaluationReport {
  categories: EvaluationCategory[];
  overallScore: number;
  maxScore: number;
  passRate: number;
  criticalIssues: number;
  warnings: number;
  timestamp: string;
}
