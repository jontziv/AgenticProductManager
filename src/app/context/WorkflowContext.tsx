import { createContext, useContext, useState, useCallback, ReactNode } from "react";
import type { IntakeRun, ArtifactRecord, QaReport, JobRecord } from "../types/api";

interface WorkflowState {
  run: IntakeRun | null;
  artifacts: Record<string, ArtifactRecord>;
  latestJob: JobRecord | null;
  qaReport: QaReport | null;
  currentStep: number;
}

interface WorkflowContextType {
  state: WorkflowState;
  setRun: (run: IntakeRun) => void;
  setArtifact: (artifact: ArtifactRecord) => void;
  setArtifacts: (artifacts: ArtifactRecord[]) => void;
  setLatestJob: (job: JobRecord | null) => void;
  setQaReport: (report: QaReport) => void;
  setCurrentStep: (step: number) => void;
  clearRun: () => void;
}

const initialState: WorkflowState = {
  run: null,
  artifacts: {},
  latestJob: null,
  qaReport: null,
  currentStep: 0,
};

const WorkflowContext = createContext<WorkflowContextType | undefined>(undefined);

export function WorkflowProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<WorkflowState>(initialState);

  const setRun = useCallback((run: IntakeRun) => {
    setState((prev) => ({ ...prev, run }));
  }, []);

  const setArtifact = useCallback((artifact: ArtifactRecord) => {
    setState((prev) => ({
      ...prev,
      artifacts: { ...prev.artifacts, [artifact.artifact_type]: artifact },
    }));
  }, []);

  const setArtifacts = useCallback((artifacts: ArtifactRecord[]) => {
    setState((prev) => ({
      ...prev,
      artifacts: artifacts.reduce<Record<string, ArtifactRecord>>((acc, a) => {
        acc[a.artifact_type] = a;
        return acc;
      }, {}),
    }));
  }, []);

  const setLatestJob = useCallback((job: JobRecord | null) => {
    setState((prev) => ({ ...prev, latestJob: job }));
  }, []);

  const setQaReport = useCallback((qaReport: QaReport) => {
    setState((prev) => ({ ...prev, qaReport }));
  }, []);

  const setCurrentStep = useCallback((currentStep: number) => {
    setState((prev) => ({ ...prev, currentStep }));
  }, []);

  const clearRun = useCallback(() => {
    setState(initialState);
  }, []);

  return (
    <WorkflowContext.Provider
      value={{ state, setRun, setArtifact, setArtifacts, setLatestJob, setQaReport, setCurrentStep, clearRun }}
    >
      {children}
    </WorkflowContext.Provider>
  );
}

export function useWorkflow() {
  const ctx = useContext(WorkflowContext);
  if (!ctx) throw new Error("useWorkflow must be used within WorkflowProvider");
  return ctx;
}
