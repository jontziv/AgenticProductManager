import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router";
import { useWorkflow } from "../../context/WorkflowContext";
import { exportsApi } from "../../api/jobs";
import { useJobPolling } from "../../hooks/useJobPolling";
import type { ExportRecord, ExportFormat, JobRecord } from "../../types/api";
import {
  ArrowLeft, Download, FileText, CheckCircle2, Loader2, RotateCcw, ExternalLink,
} from "lucide-react";

const FORMAT_CONFIG: Record<ExportFormat, { label: string; description: string; ext: string }> = {
  markdown: { label: "Markdown", description: "For wikis & version control", ext: "md" },
  json: { label: "JSON", description: "Machine-readable artifact pack", ext: "json" },
  html: { label: "PDF-ready HTML", description: "Print or save as PDF", ext: "html" },
  jira_csv: { label: "Jira CSV", description: "Import stories to Jira", ext: "csv" },
  linear_csv: { label: "Linear CSV", description: "Import stories to Linear", ext: "csv" },
};

export function ExportPack() {
  const navigate = useNavigate();
  const { runId } = useParams<{ runId: string }>();
  const { state } = useWorkflow();
  const [exports, setExports] = useState<ExportRecord[]>([]);
  const [pending, setPending] = useState<Partial<Record<ExportFormat, string>>>({}); // format -> jobId

  useEffect(() => {
    if (!runId) return;
    exportsApi.getExports(runId)
      .then(setExports)
      .catch(() => {/* silently handled by empty state */});
  }, [runId]);

  // Poll for in-progress export jobs
  const firstPendingJobId = Object.values(pending)[0];

  useJobPolling({
    runId: runId ?? null,
    jobId: firstPendingJobId,
    enabled: Object.keys(pending).length > 0,
    onComplete: async () => {
      if (!runId) return;
      const updated = await exportsApi.getExports(runId);
      setExports(updated);
      setPending({});
    },
    onError: (job: JobRecord) => {
      console.error("Export job failed:", job.error_message);
      setPending({});
    },
  });

  const requestExport = async (format: ExportFormat) => {
    if (!runId) return;
    const { job_id } = await exportsApi.requestExport({ run_id: runId, formats: [format] });
    setPending((prev) => ({ ...prev, [format]: job_id }));
  };

  const isApproved = state.run?.status === "approved" || state.run?.status === "exported";

  const artifactList = [
    { key: "problem_framing", label: "Problem Framing" },
    { key: "personas", label: "User Personas" },
    { key: "mvp_scope", label: "MVP Scope" },
    { key: "success_metrics", label: "Success Metrics" },
    { key: "user_stories", label: "User Stories" },
    { key: "backlog_items", label: "Backlog Items" },
    { key: "test_cases", label: "Test Cases" },
    { key: "risks", label: "Risk Checklist" },
    { key: "architecture", label: "Architecture Recommendation" },
  ];

  const availableArtifacts = artifactList.filter((a) => state.artifacts[a.key]);

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
          <CheckCircle2 className="h-5 w-5 text-primary" />
        </div>
        <h1 className="mb-2">Export Pack</h1>
        <p className="text-muted-foreground">
          Download your complete PM artifact pack in multiple formats.
        </p>
      </div>

      {!isApproved && (
        <div className="mb-6 rounded-xl border border-chart-4/20 bg-chart-4/5 p-5 text-sm text-chart-4">
          Approval is required before exporting. Go to{" "}
          <button
            className="underline underline-offset-2"
            onClick={() => navigate(`/runs/${runId}/approval`)}
          >
            Approval Review
          </button>{" "}
          first.
        </div>
      )}

      <div className="space-y-6">
        {/* Artifact checklist */}
        <section className="rounded-xl border border-border bg-card p-6">
          <h2 className="mb-4">Included Artifacts ({availableArtifacts.length})</h2>
          <div className="grid gap-2 sm:grid-cols-2">
            {artifactList.map((a) => {
              const exists = Boolean(state.artifacts[a.key]);
              return (
                <div
                  key={a.key}
                  className={`flex items-center gap-3 rounded-lg border px-4 py-3 ${
                    exists ? "border-border" : "border-border/30 opacity-40"
                  }`}
                >
                  <FileText className={`h-4 w-4 shrink-0 ${exists ? "text-primary" : "text-muted-foreground"}`} />
                  <span className="text-sm">{a.label}</span>
                  {exists && <CheckCircle2 className="ml-auto h-4 w-4 text-green-600" />}
                </div>
              );
            })}
          </div>
        </section>

        {/* Export options */}
        <section className="rounded-xl border border-border bg-card p-6">
          <h2 className="mb-4">Export Formats</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {(Object.entries(FORMAT_CONFIG) as [ExportFormat, typeof FORMAT_CONFIG[ExportFormat]][]).map(
              ([format, cfg]) => {
                const existing = exports.find((e) => e.format === format);
                const isPending = Boolean(pending[format]);
                return (
                  <div
                    key={format}
                    className="flex flex-col rounded-xl border border-border p-4"
                  >
                    <div className="mb-1 font-medium text-sm">{cfg.label}</div>
                    <p className="mb-3 text-xs text-muted-foreground flex-1">{cfg.description}</p>
                    {existing ? (
                      <a
                        href={existing.file_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 rounded-lg bg-green-50 border border-green-200 px-3 py-2 text-xs text-green-700 transition-opacity hover:opacity-80"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                        Download .{cfg.ext}
                      </a>
                    ) : (
                      <button
                        onClick={() => requestExport(format)}
                        disabled={isPending || !isApproved}
                        className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        {isPending ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Download className="h-3.5 w-3.5" />
                        )}
                        {isPending ? "Generating..." : `Generate .${cfg.ext}`}
                      </button>
                    )}
                  </div>
                );
              }
            )}
          </div>
        </section>

        {/* Next steps */}
        <section className="rounded-xl border border-primary/20 bg-primary/5 p-5">
          <h3 className="mb-3">Next Steps</h3>
          <ul className="space-y-2 text-sm">
            {[
              "Review artifacts with stakeholders and refine as needed",
              "Import backlog items into your project management tool",
              "Schedule sprint planning with your development team",
              "Set up success metrics tracking and dashboards",
            ].map((step, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-primary">•</span>
                {step}
              </li>
            ))}
          </ul>
        </section>
      </div>

      <div className="flex justify-between pt-8">
        <button
          onClick={() => navigate(`/runs/${runId}/approval`)}
          className="inline-flex items-center gap-2 rounded-lg border border-border px-6 py-2.5 text-sm transition-colors hover:bg-accent"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <button
          onClick={() => navigate("/new")}
          className="inline-flex items-center gap-2 rounded-lg border border-primary bg-background px-6 py-2.5 text-sm text-primary transition-colors hover:bg-primary/5"
        >
          <RotateCcw className="h-4 w-4" />
          New run
        </button>
      </div>
    </div>
  );
}
