import { useNavigate, useParams } from "react-router";
import { useWorkflow } from "../../context/WorkflowContext";
import { ArrowRight, ArrowLeft, Target, TrendingUp } from "lucide-react";
import { useEffect } from "react";
import type { MvpScopeArtifact, SuccessMetricsArtifact } from "../../types/api";

export function MVPBrief() {
  const navigate = useNavigate();
  const { runId } = useParams<{ runId: string }>();
  const { state, setCurrentStep } = useWorkflow();

  useEffect(() => {
    if (!state.run) {
      navigate("/dashboard");
    }
  }, [state.run, navigate]);

  const mvpScope = state.artifacts["mvp_scope"]?.content as MvpScopeArtifact | undefined;
  const successMetrics = state.artifacts["success_metrics"]?.content as SuccessMetricsArtifact | undefined;

  const handleContinue = () => {
    setCurrentStep(3);
    navigate(`/runs/${runId}/backlog`);
  };

  const handleBack = () => {
    setCurrentStep(1);
    navigate(`/runs/${runId}/scope`);
  };

  if (!mvpScope || !successMetrics) {
    return (
      <div className="flex h-40 items-center justify-center text-muted-foreground">
        MVP brief not yet generated
      </div>
    );
  }

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h2 className="mb-2">MVP Brief</h2>
        <p className="text-muted-foreground">
          Core features and success metrics for your minimum viable product
        </p>
      </div>

      <div className="space-y-8">
        <section className="rounded-lg border border-border bg-card p-6">
          <div className="mb-4 flex items-center gap-2">
            <Target className="h-5 w-5 text-primary" />
            <h3>Core Features</h3>
          </div>
          <div className="grid gap-3">
            {mvpScope.core_features.map((feature, i) => (
              <div
                key={i}
                className="flex items-start gap-3 rounded-lg bg-accent/50 p-4"
              >
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs text-primary-foreground">
                  {i + 1}
                </div>
                <div className="pt-0.5">
                  <p className="font-medium">{feature.name}</p>
                  {feature.description && <p className="text-sm text-muted-foreground">{feature.description}</p>}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-border bg-card p-6">
          <div className="mb-4 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            <h3>Success Metrics</h3>
          </div>
          <div className="space-y-4">
            {successMetrics.metrics.map((metric, i) => (
              <div key={i} className="grid md:grid-cols-[140px_1fr_140px] gap-4 items-center">
                <div className="text-sm text-muted-foreground">{metric.category}</div>
                <div>{metric.metric_name}</div>
                <div className="rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-center">
                  {metric.target}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-border bg-card p-6">
          <h3 className="mb-4">MVP Scope Summary</h3>
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <div className="mb-3 flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-primary" />
                <div className="text-sm">Included in MVP</div>
              </div>
              <ul className="space-y-2 pl-4">
                {mvpScope.in_scope.map((item, i) => (
                  <li key={i} className="text-sm">{item}</li>
                ))}
              </ul>
            </div>
            <div>
              <div className="mb-3 flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-muted-foreground/30" />
                <div className="text-sm">Deferred to Later</div>
              </div>
              <ul className="space-y-2 pl-4">
                {mvpScope.out_of_scope.map((item, i) => (
                  <li key={i} className="text-sm text-muted-foreground">{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      </div>

      <div className="flex justify-between pt-8">
        <button
          onClick={handleBack}
          className="inline-flex items-center gap-2 rounded-lg border border-border px-6 py-2.5 transition-colors hover:bg-accent"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <button
          onClick={handleContinue}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-primary-foreground transition-opacity hover:opacity-90"
        >
          Generate Backlog
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
