import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { useWorkflow } from "../../context/WorkflowContext";
import { evaluateArtifacts } from "../../utils/evaluators";
import { EvaluationReport } from "../../types/evaluation";
import {
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  ShieldCheck,
  ChevronDown,
  ChevronRight
} from "lucide-react";

export function QAEvaluation() {
  const navigate = useNavigate();
  const { state, setCurrentStep } = useWorkflow();
  const [isEvaluating, setIsEvaluating] = useState(true);
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!state.run) {
      navigate("/dashboard");
      return;
    }

    // Simulate evaluation process
    setTimeout(() => {
      const evaluationReport = evaluateArtifacts(state.artifacts as Record<string, unknown>);
      setReport(evaluationReport);
      setIsEvaluating(false);
      // Auto-expand categories with issues
      const categoriesToExpand = new Set(
        evaluationReport.categories
          .filter(cat => cat.checks.some(c => c.status === "failed" || c.status === "warning"))
          .map(cat => cat.name)
      );
      setExpandedCategories(categoriesToExpand);
    }, 3000);
  }, [state.artifacts, navigate]);

  const handleContinue = () => {
    setCurrentStep(6);
    navigate("/export");
  };

  const handleBack = () => {
    setCurrentStep(4);
    navigate("/architecture");
  };

  const toggleCategory = (categoryName: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(categoryName)) {
        next.delete(categoryName);
      } else {
        next.add(categoryName);
      }
      return next;
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "passed":
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case "failed":
        return <XCircle className="h-5 w-5 text-destructive" />;
      case "warning":
        return <AlertTriangle className="h-5 w-5 text-chart-4" />;
      default:
        return <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "passed":
        return "border-green-200 bg-green-50";
      case "failed":
        return "border-destructive/20 bg-destructive/5";
      case "warning":
        return "border-chart-4/20 bg-chart-4/5";
      default:
        return "border-border bg-background";
    }
  };

  if (isEvaluating) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
        <h2 className="mb-2 text-center">Running QA Evaluation</h2>
        <p className="text-center text-muted-foreground mb-8 max-w-md">
          Validating generated artifacts against quality standards
        </p>
        <div className="space-y-2 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
            <span>Checking faithfulness and grounding...</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
            <span>Verifying completeness...</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
            <span>Validating compliance with standards...</span>
          </div>
        </div>
      </div>
    );
  }

  if (!report) return null;

  const canProceed = report.criticalIssues === 0;

  return (
    <div className="max-w-5xl">
      <div className="mb-8">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
            <ShieldCheck className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h2>QA Evaluation Report</h2>
            <p className="text-sm text-muted-foreground">
              Automated quality assessment of generated artifacts
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        {/* Summary Card */}
        <section className="rounded-lg border border-border bg-card p-6">
          <div className="grid md:grid-cols-4 gap-6">
            <div>
              <div className="text-sm text-muted-foreground mb-1">Overall Score</div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-semibold">{report.overallScore}</span>
                <span className="text-muted-foreground">/ {report.maxScore}</span>
              </div>
              <div className="mt-1 text-sm text-muted-foreground">
                {report.passRate.toFixed(1)}% pass rate
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground mb-1">Categories</div>
              <div className="text-3xl font-semibold">{report.categories.length}</div>
              <div className="mt-1 text-sm text-green-600">
                {report.categories.filter(c => c.checks.every(ch => ch.status === "passed")).length} passed
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground mb-1">Critical Issues</div>
              <div className={`text-3xl font-semibold ${report.criticalIssues > 0 ? "text-destructive" : "text-green-600"}`}>
                {report.criticalIssues}
              </div>
              <div className="mt-1 text-sm text-muted-foreground">
                Must fix before export
              </div>
            </div>
            <div>
              <div className="text-sm text-muted-foreground mb-1">Warnings</div>
              <div className={`text-3xl font-semibold ${report.warnings > 0 ? "text-chart-4" : "text-green-600"}`}>
                {report.warnings}
              </div>
              <div className="mt-1 text-sm text-muted-foreground">
                Recommended fixes
              </div>
            </div>
          </div>
        </section>

        {/* Evaluation Categories */}
        <section className="space-y-3">
          {report.categories.map((category) => {
            const isExpanded = expandedCategories.has(category.name);
            const hasIssues = category.checks.some(c => c.status === "failed" || c.status === "warning");

            return (
              <div
                key={category.name}
                className="rounded-lg border border-border bg-card overflow-hidden"
              >
                <button
                  onClick={() => toggleCategory(category.name)}
                  className="w-full flex items-center justify-between p-4 hover:bg-accent/50 transition-colors"
                >
                  <div className="flex items-center gap-3 flex-1">
                    {isExpanded ? (
                      <ChevronDown className="h-5 w-5 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-5 w-5 text-muted-foreground" />
                    )}
                    <div className="text-left flex-1">
                      <h3>{category.name}</h3>
                      <p className="text-sm text-muted-foreground">{category.description}</p>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="font-semibold">
                          {category.overallScore} / {category.maxScore}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {category.checks.filter(c => c.status === "passed").length} / {category.checks.length} checks passed
                        </div>
                      </div>
                      {hasIssues && (
                        <div className="flex items-center gap-1">
                          {category.checks.some(c => c.status === "failed") && (
                            <XCircle className="h-5 w-5 text-destructive" />
                          )}
                          {category.checks.some(c => c.status === "warning") && (
                            <AlertTriangle className="h-5 w-5 text-chart-4" />
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </button>

                {isExpanded && (
                  <div className="border-t border-border bg-accent/20 p-4">
                    <div className="space-y-3">
                      {category.checks.map((check) => (
                        <div
                          key={check.id}
                          className={`rounded-lg border p-4 ${getStatusColor(check.status)}`}
                        >
                          <div className="flex items-start justify-between gap-4 mb-3">
                            <div className="flex items-start gap-3 flex-1">
                              {getStatusIcon(check.status)}
                              <div className="flex-1">
                                <h4 className="mb-1">{check.name}</h4>
                                <p className="text-sm text-muted-foreground">{check.description}</p>
                              </div>
                            </div>
                            {check.score !== undefined && (
                              <div className="shrink-0 text-right">
                                <div className="font-semibold">{check.score}/{check.maxScore}</div>
                              </div>
                            )}
                          </div>

                          {check.findings.length > 0 && (
                            <div className="mb-3 ml-8">
                              <div className="text-sm text-muted-foreground mb-1">Findings:</div>
                              <ul className="space-y-1">
                                {check.findings.map((finding, i) => (
                                  <li key={i} className="text-sm flex items-start gap-2">
                                    <span className="text-muted-foreground">•</span>
                                    <span>{finding}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {check.remediation && (
                            <div className="ml-8 rounded-md bg-background/80 p-3 border border-border">
                              <div className="text-sm font-medium mb-1">Recommended Action:</div>
                              <p className="text-sm">{check.remediation}</p>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </section>

        {/* Action Required Notice */}
        {!canProceed && (
          <section className="rounded-lg border border-destructive bg-destructive/5 p-6">
            <div className="flex items-start gap-3">
              <XCircle className="h-6 w-6 text-destructive shrink-0 mt-0.5" />
              <div>
                <h3 className="text-destructive mb-2">Action Required</h3>
                <p className="text-sm mb-3">
                  {report.criticalIssues} critical {report.criticalIssues === 1 ? "issue" : "issues"} must be resolved before proceeding to export.
                  Please review the failed checks above and regenerate artifacts or manually edit the output.
                </p>
                <button className="text-sm px-4 py-2 rounded-lg bg-destructive text-destructive-foreground hover:opacity-90 transition-opacity">
                  Regenerate Artifacts
                </button>
              </div>
            </div>
          </section>
        )}

        {canProceed && report.warnings > 0 && (
          <section className="rounded-lg border border-chart-4/20 bg-chart-4/5 p-6">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-6 w-6 text-chart-4 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-chart-4 mb-2">Warnings Detected</h3>
                <p className="text-sm">
                  {report.warnings} {report.warnings === 1 ? "warning" : "warnings"} detected.
                  You can proceed to export, but consider addressing these issues for higher quality output.
                </p>
              </div>
            </div>
          </section>
        )}

        {canProceed && report.warnings === 0 && report.criticalIssues === 0 && (
          <section className="rounded-lg border border-green-200 bg-green-50 p-6">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="h-6 w-6 text-green-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-green-900 mb-2">All Checks Passed</h3>
                <p className="text-sm text-green-800">
                  All quality evaluations passed successfully. Your artifacts are ready for export.
                </p>
              </div>
            </div>
          </section>
        )}
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
          disabled={!canProceed}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {canProceed ? "Proceed to Export" : "Fix Issues to Continue"}
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
