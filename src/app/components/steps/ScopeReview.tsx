import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { useWorkflow } from "../../context/WorkflowContext";
import { runsApi } from "../../api/runs";
import { useJobPolling } from "../../hooks/useJobPolling";
import type {
  JobRecord,
  ProblemFramingArtifact,
  PersonasArtifact,
  MvpScopeArtifact,
} from "../../types/api";
import {
  Loader2, ArrowRight, ArrowLeft, Sparkles, AlertTriangle, RefreshCw, X,
} from "lucide-react";

const PROCESSING_STEPS = [
  "Normalizing input and extracting brief",
  "Detecting missing information",
  "Classifying idea type",
  "Choosing product pattern",
  "Framing the problem",
  "Generating user personas",
  "Defining MVP scope",
];

export function ScopeReview() {
  const navigate = useNavigate();
  const { runId } = useParams<{ runId: string }>();
  const { state, setRun, setArtifacts, setCurrentStep } = useWorkflow();
  const [processingStep, setProcessingStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleCancelRun = async () => {
    if (!runId) return;
    if (!window.confirm("Stop and delete this run?")) return;
    try {
      await runsApi.delete(runId);
      navigate("/dashboard");
    } catch {
      setError("Could not cancel the run. Please try from the dashboard.");
    }
  };

  const isProcessing = !state.run ||
    state.run.status === "queued" ||
    state.run.status === "processing";

  // Cycle processing step labels while waiting
  useEffect(() => {
    if (!isProcessing) return;
    const interval = setInterval(() => {
      setProcessingStep((prev) => (prev + 1) % PROCESSING_STEPS.length);
    }, 1200);
    return () => clearInterval(interval);
  }, [isProcessing]);

  // Poll job status
  useJobPolling({
    runId: runId ?? null,
    enabled: isProcessing,
    intervalMs: 2500,
    onUpdate: async (job: JobRecord) => {
      if (job.current_step) {
        const idx = PROCESSING_STEPS.findIndex((s) =>
          s.toLowerCase().includes(job.current_step?.toLowerCase() ?? "")
        );
        if (idx >= 0) setProcessingStep(idx);
      }
    },
    onComplete: async () => {
      if (!runId) return;
      const run = await runsApi.get(runId);
      setRun(run);
      if (run.artifacts?.length) setArtifacts(run.artifacts);
    },
    onError: (job) => {
      setError(job.error_message ?? "Processing failed. Please try again.");
    },
  });

  const handleContinue = () => {
    setCurrentStep(1);
    navigate(`/runs/${runId}/mvp`);
  };

  const handleBack = () => {
    setCurrentStep(0);
    navigate("/new");
  };

  const artifacts = state.artifacts ?? {};
  const problemFraming = artifacts["problem_framing"]?.content as ProblemFramingArtifact | undefined;
  const personas = artifacts["personas"]?.content as PersonasArtifact | undefined;
  const mvpScope = artifacts["mvp_scope"]?.content as MvpScopeArtifact | undefined;

  // Run completed but the LLM flagged missing information — no artifacts generated
  const missingInfo = state.run?.missing_info ?? [];
  const needsMoreInfo = !isProcessing && missingInfo.length > 0 && !problemFraming;

  if (error) {
    return (
      <div className="flex max-w-2xl flex-col items-center justify-center py-20">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
          <AlertTriangle className="h-6 w-6 text-destructive" />
        </div>
        <h2 className="mb-2 text-center">Analysis failed</h2>
        <p className="mb-6 text-center text-sm text-muted-foreground">{error}</p>
        <button
          onClick={handleBack}
          className="inline-flex items-center gap-2 rounded-lg border border-border px-5 py-2.5 text-sm transition-colors hover:bg-accent"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to intake
        </button>
      </div>
    );
  }

  if (isProcessing) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
        <h2 className="mb-2 text-center">Analyzing your idea</h2>
        <p className="mb-8 max-w-md text-center text-muted-foreground">
          The AI is processing your submission and generating structured PM artifacts.
        </p>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Sparkles className="h-4 w-4 text-primary" />
          <span>{PROCESSING_STEPS[processingStep]}...</span>
        </div>
        <button
          onClick={handleCancelRun}
          className="mt-6 inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-muted-foreground/60 transition-colors hover:bg-destructive/10 hover:text-destructive"
        >
          <X className="h-3.5 w-3.5" />
          Stop &amp; delete this run
        </button>
        {state.run?.missing_info?.length ? (
          <div className="mt-8 max-w-md rounded-xl border border-chart-4/20 bg-chart-4/5 p-4">
            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-chart-4">
              <AlertTriangle className="h-4 w-4" />
              Proceeding with assumptions
            </div>
            <ul className="space-y-1">
              {state.run.missing_info.map((flag, i) => (
                <li key={i} className="text-sm text-muted-foreground">• {flag}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    );
  }

  if (!problemFraming || !personas || !mvpScope) {
    if (needsMoreInfo) {
      return (
        <div className="flex max-w-2xl flex-col items-center justify-center py-20">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-chart-4/10">
            <AlertTriangle className="h-6 w-6 text-chart-4" />
          </div>
          <h2 className="mb-2 text-center">More information needed</h2>
          <p className="mb-4 text-center text-sm text-muted-foreground">
            The AI couldn't generate a complete analysis. Please resubmit with more detail on:
          </p>
          <ul className="mb-6 w-full max-w-sm space-y-2">
            {missingInfo.map((flag, i) => (
              <li key={i} className="flex items-start gap-2 rounded-lg border border-chart-4/20 bg-chart-4/5 px-3 py-2 text-sm text-chart-4">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                {flag}
              </li>
            ))}
          </ul>
          <button
            onClick={handleBack}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-5 py-2.5 text-sm transition-colors hover:bg-accent"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to intake
          </button>
        </div>
      );
    }
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <RefreshCw className="mb-4 h-8 w-8 text-muted-foreground" />
        <p className="text-muted-foreground">Artifacts not yet available. Reload to check.</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="mb-2">Scope & Assumptions</h1>
        <p className="text-muted-foreground">
          Review the AI-generated analysis. These assumptions drive all downstream artifacts.
        </p>
      </div>

      <div className="space-y-6">
        {/* Problem framing */}
        <section className="rounded-xl border border-border bg-card p-6">
          <h2 className="mb-5">Problem Framing</h2>
          <div className="space-y-4">
            <div>
              <div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Problem Statement</div>
              <p>{problemFraming.problem_statement}</p>
            </div>
            <div>
              <div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Opportunity</div>
              <p>{problemFraming.opportunity}</p>
            </div>
            <div>
              <div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Hypothesis</div>
              <p className="italic text-muted-foreground">{problemFraming.hypothesis}</p>
            </div>
            {problemFraming.assumptions.length > 0 && (
              <div>
                <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Assumptions made ({problemFraming.assumptions.length})
                </div>
                <ul className="space-y-1">
                  {problemFraming.assumptions.map((a, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <span className="text-chart-4">~</span>
                      <span className="text-muted-foreground">{a}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>

        {/* MVP scope */}
        <section className="rounded-xl border border-border bg-card p-6">
          <h2 className="mb-5">Initial Scope Assessment</h2>
          <div className="grid gap-6 md:grid-cols-2">
            <div>
              <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                <div className="h-2 w-2 rounded-full bg-primary" />
                In Scope ({mvpScope.in_scope.length})
              </div>
              <ul className="space-y-1.5">
                {mvpScope.in_scope.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span className="mt-0.5 text-primary">+</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <div className="mb-3 flex items-center gap-2 text-sm font-medium">
                <div className="h-2 w-2 rounded-full bg-muted-foreground/30" />
                Out of Scope ({mvpScope.out_of_scope.length})
              </div>
              <ul className="space-y-1.5">
                {mvpScope.out_of_scope.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <span className="mt-0.5">–</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* Personas */}
        <section className="rounded-xl border border-border bg-card p-6">
          <h2 className="mb-5">User Personas ({personas.personas.length})</h2>
          <div className="grid gap-4">
            {personas.personas.map((persona, i) => (
              <div key={i} className="rounded-lg border border-border p-4">
                <div className="mb-3">
                  <div className="font-medium">{persona.name}</div>
                  <div className="text-sm text-muted-foreground">{persona.role}</div>
                  {persona.archetype && (
                    <span className="mt-1 inline-block rounded-full bg-accent px-2.5 py-0.5 text-xs">
                      {persona.archetype}
                    </span>
                  )}
                </div>
                <div className="grid gap-3 text-sm md:grid-cols-3">
                  <div>
                    <div className="mb-1.5 text-xs font-medium text-muted-foreground">Goals</div>
                    <ul className="space-y-0.5">
                      {persona.goals.map((g, j) => <li key={j}>• {g}</li>)}
                    </ul>
                  </div>
                  <div>
                    <div className="mb-1.5 text-xs font-medium text-muted-foreground">Pain Points</div>
                    <ul className="space-y-0.5">
                      {persona.pain_points.map((p, j) => <li key={j}>• {p}</li>)}
                    </ul>
                  </div>
                  <div>
                    <div className="mb-1.5 text-xs font-medium text-muted-foreground">Behaviors</div>
                    <ul className="space-y-0.5">
                      {persona.behaviors.map((b, j) => <li key={j}>• {b}</li>)}
                    </ul>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="flex justify-between pt-8">
        <button
          onClick={handleBack}
          className="inline-flex items-center gap-2 rounded-lg border border-border px-6 py-2.5 text-sm transition-colors hover:bg-accent"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <button
          onClick={handleContinue}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-sm text-primary-foreground transition-opacity hover:opacity-90"
        >
          Continue to MVP Brief
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
