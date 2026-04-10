import { useNavigate, useParams } from "react-router";
import { useWorkflow } from "../../context/WorkflowContext";
import { ArrowRight, ArrowLeft, ListChecks, FlaskConical, AlertTriangle } from "lucide-react";
import { useEffect } from "react";
import type { UserStoriesArtifact, BacklogArtifact, TestCasesArtifact, RisksArtifact } from "../../types/api";

export function Backlog() {
  const navigate = useNavigate();
  const { runId } = useParams<{ runId: string }>();
  const { state, setCurrentStep } = useWorkflow();

  useEffect(() => {
    if (!state.run) {
      navigate("/dashboard");
    }
  }, [state.run, navigate]);

  const userStories = (state.artifacts["user_stories"]?.content as UserStoriesArtifact | undefined)?.stories ?? [];
  const backlogItems = (state.artifacts["backlog_items"]?.content as BacklogArtifact | undefined)?.epics ?? [];
  const testCases = (state.artifacts["test_cases"]?.content as TestCasesArtifact | undefined)?.test_cases ?? [];
  const risks = (state.artifacts["risks"]?.content as RisksArtifact | undefined)?.risks ?? [];

  const handleContinue = () => {
    setCurrentStep(4);
    navigate(`/runs/${runId}/architecture`);
  };

  const handleBack = () => {
    setCurrentStep(2);
    navigate(`/runs/${runId}/mvp`);
  };

  const priorityColors: Record<string, string> = {
    High: "bg-destructive/10 text-destructive border-destructive/20",
    Medium: "bg-chart-4/10 text-chart-4 border-chart-4/20",
    Low: "bg-muted text-muted-foreground border-border",
  };

  return (
    <div className="max-w-5xl">
      <div className="mb-8">
        <h2 className="mb-2">Backlog & Test Plan</h2>
        <p className="text-muted-foreground">
          User stories, backlog organization, test cases, and risk assessment
        </p>
      </div>

      <div className="space-y-8">
        <section className="rounded-lg border border-border bg-card p-6">
          <div className="mb-4 flex items-center gap-2">
            <ListChecks className="h-5 w-5 text-primary" />
            <h3>User Stories ({userStories.length})</h3>
          </div>
          <div className="space-y-4">
            {userStories.map((story) => (
              <div key={story.id} className="rounded-lg border border-border p-4">
                <div className="mb-3 flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="mb-2">
                      <span className="text-muted-foreground">As a </span>
                      <span className="font-medium">{story.as_a}</span>
                      <span className="text-muted-foreground">, I want </span>
                      <span className="font-medium">{story.i_want}</span>
                      <span className="text-muted-foreground">, so that </span>
                      <span className="font-medium">{story.so_that}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span
                      className={`rounded-md border px-2 py-1 text-xs ${
                        priorityColors[story.priority]
                      }`}
                    >
                      {story.priority}
                    </span>
                    <span className="rounded-md bg-muted px-2 py-1 text-xs text-muted-foreground">
                      {story.estimated_effort}
                    </span>
                  </div>
                </div>
                <div>
                  <div className="mb-2 text-sm text-muted-foreground">Acceptance Criteria</div>
                  <ul className="space-y-1">
                    {story.acceptance_criteria.map((criteria, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <span className="text-primary">✓</span>
                        <span>{criteria}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-border bg-card p-6">
          <h3 className="mb-4">Backlog Organization</h3>
          <div className="space-y-3">
            {backlogItems.map((item, i) => (
              <div key={i} className="rounded-lg bg-accent/50 p-4">
                <div className="mb-2 font-medium">{item.epic}</div>
                <div className="flex flex-wrap gap-2">
                  {item.story_ids.map((storyId, j) => (
                    <span
                      key={j}
                      className="rounded bg-background px-2 py-1 text-xs border border-border"
                    >
                      {storyId}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-border bg-card p-6">
          <div className="mb-4 flex items-center gap-2">
            <FlaskConical className="h-5 w-5 text-primary" />
            <h3>Test Cases ({testCases.length})</h3>
          </div>
          <div className="space-y-3">
            {testCases.map((test) => (
              <div key={test.id} className="rounded-lg border border-border p-4">
                <div className="mb-3 flex items-start justify-between gap-4">
                  <h4 className="flex-1">{test.scenario}</h4>
                  <span
                    className={`rounded-md border px-2 py-1 text-xs shrink-0 ${
                      priorityColors[test.priority]
                    }`}
                  >
                    {test.priority}
                  </span>
                </div>
                <div className="grid md:grid-cols-[1fr_200px] gap-4">
                  <div>
                    <div className="mb-1 text-sm text-muted-foreground">Steps</div>
                    <ol className="space-y-1">
                      {test.steps.map((step, i) => (
                        <li key={i} className="text-sm">
                          {i + 1}. {step}
                        </li>
                      ))}
                    </ol>
                  </div>
                  <div>
                    <div className="mb-1 text-sm text-muted-foreground">Expected Result</div>
                    <p className="text-sm">{test.expected_result}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-destructive/20 bg-destructive/5 p-6">
          <div className="mb-4 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <h3>Risk Checklist ({risks.length})</h3>
          </div>
          <div className="space-y-3">
            {risks.map((risk, i) => (
              <div key={i} className="rounded-lg border border-border bg-card p-4">
                <div className="mb-2 flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="mb-1 text-sm text-muted-foreground">{risk.category}</div>
                    <p>{risk.description}</p>
                  </div>
                  <span
                    className={`rounded-md border px-2 py-1 text-xs shrink-0 ${
                      priorityColors[risk.impact]
                    }`}
                  >
                    {risk.impact} Impact
                  </span>
                </div>
                <div>
                  <div className="mb-1 text-sm text-muted-foreground">Mitigation Strategy</div>
                  <p className="text-sm">{risk.mitigation}</p>
                </div>
              </div>
            ))}
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
          View Architecture
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

