import { useNavigate, useParams } from "react-router";
import { useWorkflow } from "../../context/WorkflowContext";
import { ArrowRight, ArrowLeft, Boxes, Network } from "lucide-react";
import { useEffect } from "react";
import type { ArchitectureArtifact } from "../../types/api";

export function Architecture() {
  const navigate = useNavigate();
  const { runId } = useParams<{ runId: string }>();
  const { state, setCurrentStep } = useWorkflow();

  useEffect(() => {
    if (!state.run) {
      navigate("/dashboard");
    }
  }, [state.run, navigate]);

  const architectureRecord = state.artifacts["architecture"];
  const architecture = architectureRecord?.content as ArchitectureArtifact | undefined;
  const recommended = architecture?.options.find((o) => o.recommended) ?? architecture?.options[0];

  const handleContinue = () => {
    setCurrentStep(5);
    navigate(`/runs/${runId}/qa`);
  };

  const handleBack = () => {
    setCurrentStep(3);
    navigate(`/runs/${runId}/backlog`);
  };

  if (!architecture || !recommended) {
    return (
      <div className="flex h-40 items-center justify-center text-muted-foreground">
        Architecture not yet generated
      </div>
    );
  }

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h2 className="mb-2">Architecture Recommendation</h2>
        <p className="text-muted-foreground">
          Lightweight technical architecture guidance based on your requirements
        </p>
      </div>

      <div className="space-y-8">
        <section className="rounded-lg border border-border bg-card p-6">
          <h3 className="mb-4">{recommended.name}</h3>
          <p className="text-muted-foreground">{architecture.rationale}</p>
        </section>

        <section className="rounded-lg border border-border bg-card p-6">
          <div className="mb-4 flex items-center gap-2">
            <Boxes className="h-5 w-5 text-primary" />
            <h3>Key Components</h3>
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            {recommended.components.map((component, i) => (
              <div
                key={i}
                className="rounded-lg border border-border bg-accent/30 p-4"
              >
                <p>{component}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-border bg-card p-6">
          <div className="mb-4 flex items-center gap-2">
            <Network className="h-5 w-5 text-primary" />
            <h3>Data Flow</h3>
          </div>
          <div className="rounded-lg bg-accent/50 p-6">
            <p className="whitespace-pre-line">{recommended.data_flow}</p>
          </div>
        </section>

        <section className="rounded-lg border border-border bg-card p-6">
          <h3 className="mb-4">Technical Considerations</h3>
          <ul className="space-y-3">
            {architecture.technical_considerations.map((consideration, i) => (
              <li key={i} className="flex items-start gap-3">
                <div className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                <p>{consideration}</p>
              </li>
            ))}
          </ul>
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
          Export Package
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
