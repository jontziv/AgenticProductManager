import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { useWorkflow } from "../../context/WorkflowContext";
import type {
  ExportFormat,
  UserStoriesArtifact,
  BacklogArtifact,
  TestCasesArtifact,
  RisksArtifact,
  SuccessMetricsArtifact,
  PersonasArtifact,
  ProblemFramingArtifact,
  MvpScopeArtifact,
  ArchitectureArtifact,
} from "../../types/api";
import {
  ArrowLeft, Download, FileText, CheckCircle2, RotateCcw,
} from "lucide-react";

// ── Format config ─────────────────────────────────────────────────────────────

const FORMAT_CONFIG: Record<ExportFormat, { label: string; description: string; ext: string; mime: string }> = {
  json:        { label: "JSON",            description: "Machine-readable artifact pack",  ext: "json", mime: "application/json" },
  markdown:    { label: "Markdown",        description: "For wikis & version control",     ext: "md",   mime: "text/markdown" },
  html:        { label: "PDF-ready HTML",  description: "Print or save as PDF",            ext: "html", mime: "text/html" },
  jira_csv:    { label: "Jira CSV",        description: "Import user stories to Jira",     ext: "csv",  mime: "text/csv" },
  linear_csv:  { label: "Linear CSV",      description: "Import user stories to Linear",   ext: "csv",  mime: "text/csv" },
};

// ── CSV helpers ───────────────────────────────────────────────────────────────

function ce(val: unknown): string {
  const s = String(val ?? "").replace(/"/g, '""');
  return /[,"\n]/.test(s) ? `"${s}"` : s;
}

function row(...cols: unknown[]): string {
  return cols.map(ce).join(",");
}

function buildCSV(arts: Record<string, unknown>, title: string): string {
  const lines: string[] = [
    ce(`PM Artifact Pack — ${title}`),
    ce(`Generated: ${new Date().toISOString()}`),
    "",
  ];

  const stories = ((arts.user_stories as UserStoriesArtifact | undefined)?.stories ?? []);
  if (stories.length) {
    lines.push(ce("=== USER STORIES ==="));
    lines.push(row("ID", "Epic", "As A", "I Want", "So That", "Priority", "Effort", "Acceptance Criteria"));
    for (const s of stories) {
      lines.push(row(s.id, s.epic, s.as_a, s.i_want, s.so_that, s.priority, s.estimated_effort,
        (s.acceptance_criteria ?? []).join(" | ")));
    }
    lines.push("");
  }

  const epics = ((arts.backlog_items as BacklogArtifact | undefined)?.epics ?? []);
  if (epics.length) {
    lines.push(ce("=== BACKLOG ==="));
    lines.push(row("Epic", "Description", "Story IDs", "Priority Rationale"));
    for (const e of epics) {
      lines.push(row(e.epic, e.epic_description, (e.story_ids ?? []).join(" | "), e.priority_rationale));
    }
    lines.push("");
  }

  const tests = ((arts.test_cases as TestCasesArtifact | undefined)?.test_cases ?? []);
  if (tests.length) {
    lines.push(ce("=== TEST CASES ==="));
    lines.push(row("ID", "Story ID", "Scenario", "Type", "Priority", "Steps", "Expected Result"));
    for (const t of tests) {
      lines.push(row(t.id, t.story_id ?? "", t.scenario, t.test_type, t.priority,
        (t.steps ?? []).join(" | "), t.expected_result));
    }
    lines.push("");
  }

  const risks = ((arts.risks as RisksArtifact | undefined)?.risks ?? []);
  if (risks.length) {
    lines.push(ce("=== RISKS ==="));
    lines.push(row("ID", "Category", "Description", "Likelihood", "Impact", "Mitigation", "Owner"));
    for (const r of risks) {
      lines.push(row(r.id, r.category, r.description, r.likelihood, r.impact, r.mitigation, r.owner));
    }
    lines.push("");
  }

  const metrics = ((arts.success_metrics as SuccessMetricsArtifact | undefined)?.metrics ?? []);
  if (metrics.length) {
    lines.push(ce("=== SUCCESS METRICS ==="));
    lines.push(row("Category", "Metric", "Target", "Baseline", "Signal Type", "Measurement"));
    for (const m of metrics) {
      lines.push(row(m.category, m.metric_name, m.target, m.baseline ?? "", m.signal_type, m.measurement_method));
    }
    lines.push("");
  }

  const pf = arts.problem_framing as ProblemFramingArtifact | undefined;
  if (pf?.problem_statement) {
    lines.push(ce("=== PROBLEM FRAMING ==="));
    lines.push(row("Field", "Value"));
    lines.push(row("Problem Statement", pf.problem_statement));
    lines.push(row("Opportunity", pf.opportunity));
    lines.push(row("Hypothesis", pf.hypothesis));
    for (const g of pf.goals ?? []) lines.push(row("Goal", g));
    for (const g of pf.non_goals ?? []) lines.push(row("Non-Goal", g));
    for (const a of pf.assumptions ?? []) lines.push(row("Assumption", a));
    lines.push("");
  }

  return lines.join("\n");
}

// ── Markdown builder ──────────────────────────────────────────────────────────

function buildMarkdown(arts: Record<string, unknown>, title: string): string {
  const lines: string[] = [
    `# ${title}`,
    `_Generated: ${new Date().toISOString()}_`,
    "",
  ];

  const pf = arts.problem_framing as ProblemFramingArtifact | undefined;
  if (pf?.problem_statement) {
    lines.push("## Problem Framing", "");
    lines.push(`**Problem Statement:** ${pf.problem_statement}`, "");
    lines.push(`**Opportunity:** ${pf.opportunity}`, "");
    lines.push(`**Hypothesis:** _${pf.hypothesis}_`, "");
    if (pf.goals?.length) lines.push("**Goals:**", ...pf.goals.map(g => `- ${g}`), "");
    if (pf.non_goals?.length) lines.push("**Non-Goals:**", ...pf.non_goals.map(g => `- ${g}`), "");
    if (pf.assumptions?.length) lines.push("**Assumptions:**", ...pf.assumptions.map(a => `- ${a}`), "");
  }

  const personas = (arts.personas as PersonasArtifact | undefined)?.personas ?? [];
  if (personas.length) {
    lines.push("## User Personas", "");
    for (const p of personas) {
      lines.push(`### ${p.name} — ${p.role}`, `**Archetype:** ${p.archetype}`, "");
      if (p.goals?.length) lines.push("**Goals:**", ...p.goals.map(g => `- ${g}`), "");
      if (p.pain_points?.length) lines.push("**Pain Points:**", ...p.pain_points.map(g => `- ${g}`), "");
    }
  }

  const scope = arts.mvp_scope as MvpScopeArtifact | undefined;
  if (scope) {
    lines.push("## MVP Scope", "");
    if (scope.in_scope?.length) lines.push("### In Scope", ...scope.in_scope.map(i => `- ${i}`), "");
    if (scope.out_of_scope?.length) lines.push("### Out of Scope", ...scope.out_of_scope.map(i => `- ${i}`), "");
    if (scope.core_features?.length) {
      lines.push("### Core Features", "");
      for (const f of scope.core_features) {
        lines.push(`**${f.id} ${f.name}** (${f.priority})`, f.description, "");
      }
    }
  }

  const metrics = (arts.success_metrics as SuccessMetricsArtifact | undefined)?.metrics ?? [];
  if (metrics.length) {
    lines.push("## Success Metrics", "", "| Metric | Target | Type |", "|---|---|---|");
    for (const m of metrics) lines.push(`| ${m.metric_name} | ${m.target} | ${m.signal_type} |`);
    lines.push("");
  }

  const stories = (arts.user_stories as UserStoriesArtifact | undefined)?.stories ?? [];
  if (stories.length) {
    lines.push("## User Stories", "");
    for (const s of stories) {
      lines.push(`### ${s.id} [${s.priority}]`);
      lines.push(`As a **${s.as_a}**, I want **${s.i_want}**, so that **${s.so_that}**.`, "");
      lines.push("**Acceptance Criteria:**", ...(s.acceptance_criteria ?? []).map(ac => `- [ ] ${ac}`));
      lines.push(`_Effort: ${s.estimated_effort} | Epic: ${s.epic}_`, "");
    }
  }

  const tests = (arts.test_cases as TestCasesArtifact | undefined)?.test_cases ?? [];
  if (tests.length) {
    lines.push("## Test Cases", "");
    for (const t of tests) {
      lines.push(`### ${t.id} — ${t.scenario}`, `**Type:** ${t.test_type} | **Priority:** ${t.priority}`, "");
      if (t.steps?.length) lines.push("**Steps:**", ...t.steps.map((s, i) => `${i + 1}. ${s}`));
      lines.push(`**Expected:** ${t.expected_result}`, "");
    }
  }

  const risks = (arts.risks as RisksArtifact | undefined)?.risks ?? [];
  if (risks.length) {
    lines.push("## Risk Checklist", "", "| ID | Category | Impact | Likelihood | Mitigation |", "|---|---|---|---|---|");
    for (const r of risks) {
      lines.push(`| ${r.id} | ${r.category} | ${r.impact} | ${r.likelihood} | ${r.mitigation.slice(0, 60)}... |`);
    }
    lines.push("");
  }

  const arch = arts.architecture as ArchitectureArtifact | undefined;
  if (arch) {
    lines.push("## Architecture Recommendation", "");
    lines.push(`**Recommended:** ${arch.recommended_option}`, "", arch.rationale, "");
    for (const opt of arch.options ?? []) {
      lines.push(`### Option: ${opt.name}${opt.recommended ? " ✓ Recommended" : ""}`, opt.description, "");
      if (opt.pros?.length) lines.push("**Pros:**", ...opt.pros.map(p => `+ ${p}`), "");
      if (opt.cons?.length) lines.push("**Cons:**", ...opt.cons.map(c => `- ${c}`), "");
    }
  }

  return lines.join("\n");
}

// ── JSON builder ──────────────────────────────────────────────────────────────

function buildJSON(arts: Record<string, unknown>, runId: string, title: string): string {
  return JSON.stringify({ run_id: runId, title, generated_at: new Date().toISOString(), artifacts: arts }, null, 2);
}

// ── HTML builder ──────────────────────────────────────────────────────────────

function buildHTML(arts: Record<string, unknown>, title: string): string {
  const md = buildMarkdown(arts, title).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>${title}</title>
<style>body{font-family:system-ui,sans-serif;max-width:900px;margin:40px auto;padding:0 20px;line-height:1.6;color:#111}
h1{border-bottom:2px solid #333;padding-bottom:8px}h2{border-bottom:1px solid #ddd;padding-bottom:4px;margin-top:2em}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:8px 12px}th{background:#f5f5f5}
@media print{body{margin:0}}</style></head>
<body><pre style="white-space:pre-wrap;font-family:inherit">${md}</pre></body></html>`;
}

// ── Download trigger ──────────────────────────────────────────────────────────

function triggerDownload(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ExportPack() {
  const navigate = useNavigate();
  const { runId } = useParams<{ runId: string }>();
  const { state } = useWorkflow();
  const [downloaded, setDownloaded] = useState<Set<ExportFormat>>(new Set());

  const isApproved = state.run?.status === "approved" || state.run?.status === "exported";
  const title = state.run?.title ?? "pm-artifacts";
  const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40) || "pm-artifacts";

  // Flatten artifact records to content-only map
  const flatArts: Record<string, unknown> = Object.fromEntries(
    Object.entries(state.artifacts).map(([k, v]) => [k, v?.content ?? {}])
  );

  const handleDownload = (format: ExportFormat) => {
    const cfg = FORMAT_CONFIG[format];
    let content: string;

    if (format === "json") {
      content = buildJSON(flatArts, runId ?? "", title);
    } else if (format === "markdown") {
      content = buildMarkdown(flatArts, title);
    } else if (format === "html") {
      content = buildHTML(flatArts, title);
    } else {
      // jira_csv, linear_csv — comprehensive multi-section CSV
      content = buildCSV(flatArts, title);
    }

    triggerDownload(content, `${slug}.${cfg.ext}`, cfg.mime);
    setDownloaded((prev) => new Set([...prev, format]));
  };

  const artifactList = [
    { key: "problem_framing",  label: "Problem Framing" },
    { key: "personas",         label: "User Personas" },
    { key: "mvp_scope",        label: "MVP Scope" },
    { key: "success_metrics",  label: "Success Metrics" },
    { key: "user_stories",     label: "User Stories" },
    { key: "backlog_items",    label: "Backlog Items" },
    { key: "test_cases",       label: "Test Cases" },
    { key: "risks",            label: "Risk Checklist" },
    { key: "architecture",     label: "Architecture Recommendation" },
  ];

  const availableArtifacts = artifactList.filter((a) => state.artifacts[a.key]);

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
          <Download className="h-5 w-5 text-primary" />
        </div>
        <h1 className="mb-2">Export Pack</h1>
        <p className="text-muted-foreground">
          Download your complete PM artifact pack. All formats are generated instantly in the browser.
        </p>
      </div>

      {!isApproved && (
        <div className="mb-6 rounded-xl border border-chart-4/20 bg-chart-4/5 p-5 text-sm text-chart-4">
          Approval is required before exporting.{" "}
          <button
            className="underline underline-offset-2"
            onClick={() => navigate(`/runs/${runId}/approval`)}
          >
            Go to Approval Review
          </button>
          .
        </div>
      )}

      <div className="space-y-6">
        {/* Artifact checklist */}
        <section className="rounded-xl border border-border bg-card p-6">
          <h2 className="mb-4">Included Artifacts ({availableArtifacts.length} / {artifactList.length})</h2>
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

        {/* Export formats */}
        <section className="rounded-xl border border-border bg-card p-6">
          <h2 className="mb-1">Export Formats</h2>
          <p className="mb-4 text-sm text-muted-foreground">Files are generated in your browser — no upload required.</p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {(Object.entries(FORMAT_CONFIG) as [ExportFormat, typeof FORMAT_CONFIG[ExportFormat]][]).map(
              ([format, cfg]) => {
                const done = downloaded.has(format);
                return (
                  <div key={format} className="flex flex-col rounded-xl border border-border p-4">
                    <div className="mb-1 font-medium text-sm">{cfg.label}</div>
                    <p className="mb-3 text-xs text-muted-foreground flex-1">{cfg.description}</p>
                    <button
                      onClick={() => handleDownload(format)}
                      disabled={!isApproved}
                      className={`inline-flex items-center justify-center gap-1.5 rounded-lg border px-3 py-2 text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
                        done
                          ? "border-green-200 bg-green-50 text-green-700 hover:opacity-80"
                          : "border-border hover:bg-accent"
                      }`}
                    >
                      {done ? (
                        <CheckCircle2 className="h-3.5 w-3.5" />
                      ) : (
                        <Download className="h-3.5 w-3.5" />
                      )}
                      {done ? `Downloaded .${cfg.ext}` : `Download .${cfg.ext}`}
                    </button>
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
              "Import the CSV into Jira or Linear to seed your backlog",
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
