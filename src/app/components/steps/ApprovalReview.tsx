import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { useWorkflow } from "../../context/WorkflowContext";
import { runsApi } from "../../api/runs";
import { CheckCircle2, XCircle, ArrowLeft, Loader2, ClipboardCheck } from "lucide-react";

export function ApprovalReview() {
  const navigate = useNavigate();
  const { runId } = useParams<{ runId: string }>();
  const { state, setRun, setCurrentStep } = useWorkflow();
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isApproved = state.run?.status === "approved" || state.run?.status === "exported";

  const submitDecision = async (decision: "approved" | "rejected") => {
    if (!runId) return;
    setError(null);
    setSubmitting(true);
    try {
      await runsApi.submitApproval(runId, decision, comment || undefined);
      const run = await runsApi.get(runId);
      setRun(run);
      if (decision === "approved") {
        setCurrentStep(6);
        navigate(`/runs/${runId}/export`);
      } else {
        navigate(`/runs/${runId}/qa`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit approval");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
          <ClipboardCheck className="h-5 w-5 text-primary" />
        </div>
        <h1 className="mb-2">Approval Review</h1>
        <p className="text-muted-foreground">
          Review all generated artifacts before approving for export. Rejecting will route the run
          back to QA for remediation.
        </p>
      </div>

      {isApproved ? (
        <div className="mb-8 rounded-xl border border-green-200 bg-green-50 p-6">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-6 w-6 text-green-600" />
            <div>
              <div className="font-medium text-green-900">Approved</div>
              <p className="text-sm text-green-700">
                This run has been approved. You can now download the export pack.
              </p>
            </div>
          </div>
          <button
            onClick={() => navigate(`/runs/${runId}/export`)}
            className="mt-4 rounded-lg bg-green-700 px-5 py-2.5 text-sm text-white transition-opacity hover:opacity-90"
          >
            Go to Export
          </button>
        </div>
      ) : (
        <>
          <div className="mb-6 space-y-3">
            {state.run && (
              <div className="rounded-xl border border-border bg-card p-5">
                <div className="mb-3 text-sm font-medium">Run summary</div>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <div className="text-muted-foreground">Artifacts</div>
                    <div className="font-medium">{Object.keys(state.artifacts).length}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">QA Score</div>
                    <div className="font-medium">
                      {state.qaReport
                        ? `${(state.qaReport.pass_rate ?? 0).toFixed(0)}%`
                        : "—"}
                    </div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Hard Fails</div>
                    <div className={`font-medium ${state.qaReport?.critical_issues ? "text-destructive" : "text-green-600"}`}>
                      {state.qaReport?.critical_issues ?? "—"}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="mb-6 rounded-xl border border-destructive/20 bg-destructive/5 px-5 py-4 text-sm text-destructive">
              {error}
            </div>
          )}

          <div className="rounded-xl border border-border bg-card p-6">
            <label className="mb-1.5 block text-sm font-medium">
              Comment <span className="text-muted-foreground font-normal">(optional)</span>
            </label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              placeholder="Add notes for the record..."
              className="mb-5 w-full rounded-lg border border-border bg-input-background px-4 py-2.5 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none resize-none"
            />

            <div className="flex gap-3">
              <button
                onClick={() => submitDecision("approved")}
                disabled={submitting}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                Approve & unlock export
              </button>
              <button
                onClick={() => submitDecision("rejected")}
                disabled={submitting}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-5 py-2.5 text-sm text-destructive transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                <XCircle className="h-4 w-4" />
                Reject — back to QA
              </button>
            </div>
          </div>
        </>
      )}

      <div className="pt-6">
        <button
          onClick={() => navigate(`/runs/${runId}/qa`)}
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to QA
        </button>
      </div>
    </div>
  );
}
