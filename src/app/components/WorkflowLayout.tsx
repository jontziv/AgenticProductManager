import { useEffect } from "react";
import { Outlet, useLocation, useParams, Link } from "react-router";
import { WorkflowProvider, useWorkflow } from "../context/WorkflowContext";
import { runsApi } from "../api/runs";
import { jobsApi } from "../api/jobs";
import { ErrorBoundary } from "./ErrorBoundary";
import { Check, Zap, LayoutDashboard } from "lucide-react";
import type { RunStatus } from "../types/api";

interface Step {
  path: string;
  label: string;
  requiredStatus?: RunStatus[];
}

const STEPS: Step[] = [
  { path: "scope", label: "Scope & Assumptions" },
  { path: "mvp", label: "MVP Brief" },
  { path: "backlog", label: "Backlog" },
  { path: "architecture", label: "Architecture" },
  { path: "qa", label: "QA Studio" },
  { path: "approval", label: "Approval" },
  { path: "export", label: "Export" },
];

function RunLoader() {
  const { runId } = useParams<{ runId: string }>();
  const { setRun, setArtifacts, setLatestJob, setQaReport } = useWorkflow();

  useEffect(() => {
    if (!runId) return;

    let cancelled = false;

    const load = async () => {
      const run = await runsApi.get(runId);
      if (cancelled) return;
      setRun(run);
      if (run.artifacts?.length) setArtifacts(run.artifacts);
      if (run.latest_qa_report) setQaReport(run.latest_qa_report);

      const job = await jobsApi.getLatestJob(runId);
      if (!cancelled && job) setLatestJob(job);
    };

    load().catch(() => {});
    return () => { cancelled = true; };
  }, [runId, setRun, setArtifacts, setLatestJob, setQaReport]);

  return null;
}

function StepNav() {
  const location = useLocation();
  const { runId } = useParams<{ runId: string }>();
  const { state } = useWorkflow();

  const currentSegment = location.pathname.split("/").pop() ?? "";
  const currentIndex = STEPS.findIndex((s) => s.path === currentSegment);

  const runStatus = state.run?.status;
  const isCompleted = (index: number) => {
    if (runStatus === "exported" || runStatus === "approved") return index <= STEPS.length - 1;
    return index < currentIndex;
  };

  return (
    <div className="flex items-center gap-1 overflow-x-auto pb-1">
      {STEPS.map((step, index) => {
        const completed = isCompleted(index);
        const current = index === currentIndex;

        return (
          <div key={step.path} className="flex items-center">
            <Link
              to={`/runs/${runId}/${step.path}`}
              className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition-colors whitespace-nowrap ${
                current
                  ? "bg-primary/10 text-primary font-medium"
                  : completed
                  ? "text-muted-foreground hover:text-foreground hover:bg-accent"
                  : "text-muted-foreground/40 pointer-events-none"
              }`}
            >
              <div
                className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs border transition-colors ${
                  completed
                    ? "border-primary bg-primary text-primary-foreground"
                    : current
                    ? "border-primary bg-background text-primary"
                    : "border-muted-foreground/20 bg-background text-muted-foreground"
                }`}
              >
                {completed ? <Check className="h-3 w-3" /> : <span>{index + 1}</span>}
              </div>
              {step.label}
            </Link>
            {index < STEPS.length - 1 && (
              <div
                className={`mx-1 h-px w-4 ${completed ? "bg-primary" : "bg-border"}`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

export function WorkflowLayout() {
  return (
    <WorkflowProvider>
      <RunLoader />
      <div className="min-h-screen bg-background">
        <header className="sticky top-0 z-10 border-b border-border bg-card/95 backdrop-blur">
          <div className="mx-auto max-w-6xl px-6 py-3">
            <div className="mb-3 flex items-center justify-between">
              <Link
                to="/dashboard"
                className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                <Zap className="h-4 w-4 text-primary" />
                PM Sidekick
              </Link>
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-accent"
              >
                <LayoutDashboard className="h-3.5 w-3.5" />
                Dashboard
              </Link>
            </div>
            <StepNav />
          </div>
        </header>

        <main className="mx-auto max-w-6xl px-6 py-10">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </WorkflowProvider>
  );
}
