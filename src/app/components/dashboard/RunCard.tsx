import { Link } from "react-router";
import { format } from "date-fns";
import { ArrowRight, CheckCircle2, Clock, AlertTriangle, XCircle, Loader2 } from "lucide-react";
import type { IntakeRunSummary, RunStatus } from "../../types/api";

interface RunCardProps {
  run: IntakeRunSummary;
}

const STATUS_CONFIG: Record<RunStatus, { label: string; icon: React.ReactNode; className: string }> = {
  queued: {
    label: "Queued",
    icon: <Clock className="h-3.5 w-3.5" />,
    className: "bg-muted text-muted-foreground border-border",
  },
  processing: {
    label: "Processing",
    icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
    className: "bg-primary/10 text-primary border-primary/20",
  },
  needs_review: {
    label: "Needs Review",
    icon: <AlertTriangle className="h-3.5 w-3.5" />,
    className: "bg-chart-4/10 text-chart-4 border-chart-4/20",
  },
  qa_failed: {
    label: "QA Failed",
    icon: <XCircle className="h-3.5 w-3.5" />,
    className: "bg-destructive/5 text-destructive border-destructive/20",
  },
  qa_passed: {
    label: "QA Passed",
    icon: <AlertTriangle className="h-3.5 w-3.5" />,
    className: "bg-chart-4/10 text-chart-4 border-chart-4/20",
  },
  approved: {
    label: "Approved",
    icon: <CheckCircle2 className="h-3.5 w-3.5" />,
    className: "bg-green-50 text-green-700 border-green-200",
  },
  exported: {
    label: "Exported",
    icon: <CheckCircle2 className="h-3.5 w-3.5" />,
    className: "bg-green-50 text-green-700 border-green-200",
  },
  failed: {
    label: "Failed",
    icon: <XCircle className="h-3.5 w-3.5" />,
    className: "bg-destructive/5 text-destructive border-destructive/20",
  },
  cancelled: {
    label: "Cancelled",
    icon: <XCircle className="h-3.5 w-3.5" />,
    className: "bg-muted text-muted-foreground border-border",
  },
};

function getRunPath(run: IntakeRunSummary): string {
  switch (run.status) {
    case "queued":
    case "processing":
      return `/runs/${run.id}/processing`;
    case "needs_review":
    case "qa_failed":
      return `/runs/${run.id}/scope`;
    case "qa_passed":
      return `/runs/${run.id}/approval`;
    case "approved":
    case "exported":
      return `/runs/${run.id}/export`;
    case "failed":
      return `/runs/${run.id}/scope`;
    default:
      return `/runs/${run.id}/scope`;
  }
}

export function RunCard({ run }: RunCardProps) {
  const config = STATUS_CONFIG[run.status];
  const path = getRunPath(run);

  return (
    <Link
      to={path}
      className="group flex items-center justify-between rounded-xl border border-border bg-card px-6 py-5 transition-colors hover:border-primary/30 hover:bg-accent/30"
    >
      <div className="min-w-0 flex-1">
        <div className="mb-1.5 flex items-center gap-3">
          <h3 className="truncate">{run.title}</h3>
          <span
            className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs ${config.className}`}
          >
            {config.icon}
            {config.label}
          </span>
        </div>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>{run.artifact_count} artifacts</span>
          {run.qa_score != null && (
            <span>QA {run.qa_score.toFixed(0)}%</span>
          )}
          <span>{format(new Date(run.created_at), "MMM d, yyyy")}</span>
        </div>
      </div>
      <ArrowRight className="ml-4 h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
    </Link>
  );
}
