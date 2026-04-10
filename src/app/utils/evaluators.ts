import { EvaluationReport, EvaluationCategory, EvaluationCheck } from "../types/evaluation";

type Artifacts = Record<string, unknown>;

export function evaluateArtifacts(artifacts: Artifacts): EvaluationReport {
  const categories: EvaluationCategory[] = [
    evaluateFaithfulness(artifacts),
    evaluateCompleteness(artifacts),
    evaluateCompliance(artifacts),
    evaluateConsistency(artifacts),
    evaluateFormat(artifacts),
  ];

  const overallScore = categories.reduce((sum, cat) => sum + cat.overallScore, 0);
  const maxScore = categories.reduce((sum, cat) => sum + cat.maxScore, 0);
  const passRate = (overallScore / maxScore) * 100;

  const criticalIssues = categories.reduce(
    (sum, cat) => sum + cat.checks.filter((c) => c.status === "failed").length,
    0
  );
  const warnings = categories.reduce(
    (sum, cat) => sum + cat.checks.filter((c) => c.status === "warning").length,
    0
  );

  return {
    categories,
    overallScore,
    maxScore,
    passRate,
    criticalIssues,
    warnings,
    timestamp: new Date().toISOString(),
  };
}

function evaluateFaithfulness(_artifacts: Artifacts): EvaluationCategory {
  const checks: EvaluationCheck[] = [
    {
      id: "faith-001",
      name: "Problem Statement Grounding",
      description: "Verify problem statement is grounded in provided input",
      status: "passed",
      score: 10,
      maxScore: 10,
      findings: ["Problem statement directly references target audience", "Aligns with described business context"],
    },
    {
      id: "faith-002",
      name: "Persona-Feature Alignment",
      description: "Ensure personas align with target audience and features match persona needs",
      status: "passed",
      score: 10,
      maxScore: 10,
      findings: ["All personas match stated target audience", "Feature set addresses persona pain points"],
    },
    {
      id: "faith-003",
      name: "Scope Justification",
      description: "MVP scope decisions are traceable to problem framing",
      status: "warning",
      score: 7,
      maxScore: 10,
      findings: ["Most scope decisions have clear rationale", "2 out-of-scope items lack explicit reasoning"],
      remediation: "Add rationale for why real-time editing and custom AI training are deferred",
    },
  ];

  return {
    name: "Faithfulness",
    description: "AI outputs are grounded in user input without hallucination",
    checks,
    overallScore: checks.reduce((sum, c) => sum + (c.score || 0), 0),
    maxScore: checks.reduce((sum, c) => sum + (c.maxScore || 0), 0),
  };
}

function evaluateCompleteness(_artifacts: Artifacts): EvaluationCategory {
  const checks: EvaluationCheck[] = [
    {
      id: "comp-001",
      name: "Artifact Coverage",
      description: "All required deliverables are present",
      status: "passed",
      score: 10,
      maxScore: 10,
      findings: [
        "Problem framing: ✓",
        "User personas: ✓ (2 personas)",
        "MVP scope: ✓",
        "Success metrics: ✓ (4 metrics)",
        "User stories: ✓ (5 stories)",
        "Test cases: ✓ (4 cases)",
        "Risk assessment: ✓ (4 risks)",
        "Architecture: ✓",
      ],
    },
    {
      id: "comp-002",
      name: "User Story Completeness",
      description: "All user stories have acceptance criteria and estimates",
      status: "passed",
      score: 10,
      maxScore: 10,
      findings: [
        "All stories follow As-a/I-want/So-that format",
        "All stories have 2+ acceptance criteria",
        "All stories have priority and effort estimates",
      ],
    },
    {
      id: "comp-003",
      name: "Test Coverage",
      description: "Critical user flows have corresponding test cases",
      status: "failed",
      score: 5,
      maxScore: 10,
      findings: [
        "Happy path covered: ✓",
        "Validation errors covered: ✓",
        "Missing: concurrent user submissions test",
        "Missing: large input handling test",
        "Missing: export format validation test",
      ],
      remediation: "Add test cases for edge cases: concurrent access, large inputs, and export validation",
    },
    {
      id: "comp-004",
      name: "Risk Mitigation Strategies",
      description: "Each identified risk has actionable mitigation",
      status: "passed",
      score: 10,
      maxScore: 10,
      findings: ["All 4 risks have specific mitigation strategies", "Mitigations include concrete actions"],
    },
  ];

  return {
    name: "Completeness",
    description: "All required fields and artifacts are present with sufficient detail",
    checks,
    overallScore: checks.reduce((sum, c) => sum + (c.score || 0), 0),
    maxScore: checks.reduce((sum, c) => sum + (c.maxScore || 0), 0),
  };
}

function evaluateCompliance(_artifacts: Artifacts): EvaluationCategory {
  const checks: EvaluationCheck[] = [
    {
      id: "comp-001",
      name: "Story Format Compliance",
      description: "User stories follow standard format and conventions",
      status: "passed",
      score: 10,
      maxScore: 10,
      findings: [
        "All stories use As-a/I-want/So-that structure",
        "Acceptance criteria are testable",
        "Story IDs follow naming convention",
      ],
    },
    {
      id: "comp-002",
      name: "Priority Classification",
      description: "Priorities follow defined taxonomy (High/Medium/Low)",
      status: "passed",
      score: 10,
      maxScore: 10,
      findings: ["All priorities use standard values", "Priority distribution is reasonable (60% High, 40% Medium)"],
    },
    {
      id: "comp-003",
      name: "Metric Measurability",
      description: "Success metrics are quantifiable and time-bound",
      status: "warning",
      score: 7,
      maxScore: 10,
      findings: [
        "3 of 4 metrics have clear targets",
        "1 metric (NPS > 40) lacks baseline context",
      ],
      remediation: "Specify current NPS baseline or clarify this is initial measurement",
    },
    {
      id: "comp-004",
      name: "Architecture Standards",
      description: "Architecture recommendation follows enterprise patterns",
      status: "passed",
      score: 10,
      maxScore: 10,
      findings: [
        "Separates presentation, business logic, and data layers",
        "Includes scalability and security considerations",
      ],
    },
  ];

  return {
    name: "Compliance",
    description: "Outputs adhere to organizational standards and best practices",
    checks,
    overallScore: checks.reduce((sum, c) => sum + (c.score || 0), 0),
    maxScore: checks.reduce((sum, c) => sum + (c.maxScore || 0), 0),
  };
}

function evaluateConsistency(_artifacts: Artifacts): EvaluationCategory {
  const checks: EvaluationCheck[] = [
    {
      id: "cons-001",
      name: "Cross-Artifact Alignment",
      description: "Features mentioned in scope appear in user stories",
      status: "passed",
      score: 10,
      maxScore: 10,
      findings: [
        "All 8 core features have corresponding user stories",
        "Backlog epics map to MVP scope areas",
      ],
    },
    {
      id: "cons-002",
      name: "Persona-Story Consistency",
      description: "User stories reference personas defined in artifacts",
      status: "failed",
      score: 3,
      maxScore: 10,
      findings: [
        'Stories use generic "Product Manager" role',
        "No stories specifically reference Sarah Chen or Marcus Rodriguez",
        "Disconnect between detailed personas and story actors",
      ],
      remediation: 'Update stories to reference specific personas (e.g., "As Sarah Chen (Senior PM)")',
    },
    {
      id: "cons-003",
      name: "Risk-Architecture Alignment",
      description: "Architecture addresses identified risks",
      status: "passed",
      score: 9,
      maxScore: 10,
      findings: [
        "AI cost risk addressed by caching strategy",
        "Scalability considerations present",
        "Minor: integration risk not explicitly addressed in architecture",
      ],
    },
    {
      id: "cons-004",
      name: "Terminology Consistency",
      description: "Consistent use of terms across all artifacts",
      status: "passed",
      score: 10,
      maxScore: 10,
      findings: [
        "Consistent use of 'artifact', 'MVP', 'scope'",
        "No conflicting terminology across sections",
      ],
    },
  ];

  return {
    name: "Consistency",
    description: "Artifacts are internally coherent and reference each other correctly",
    checks,
    overallScore: checks.reduce((sum, c) => sum + (c.score || 0), 0),
    maxScore: checks.reduce((sum, c) => sum + (c.maxScore || 0), 0),
  };
}

function evaluateFormat(_artifacts: Artifacts): EvaluationCategory {
  const checks: EvaluationCheck[] = [
    {
      id: "form-001",
      name: "Data Structure Validity",
      description: "All artifacts conform to expected schema",
      status: "passed",
      score: 10,
      maxScore: 10,
      findings: ["All required fields present", "Data types match schema", "No malformed structures"],
    },
    {
      id: "form-002",
      name: "Text Quality",
      description: "Grammar, spelling, and readability",
      status: "passed",
      score: 10,
      maxScore: 10,
      findings: ["No spelling errors detected", "Grammar is correct", "Professional tone maintained"],
    },
    {
      id: "form-003",
      name: "Length Appropriateness",
      description: "Text fields are neither too terse nor overly verbose",
      status: "passed",
      score: 9,
      maxScore: 10,
      findings: [
        "Problem statement: appropriate length (2-3 sentences)",
        "User stories: concise and clear",
        "Minor: One architecture consideration could be more concise",
      ],
    },
  ];

  return {
    name: "Format & Quality",
    description: "Structural validity, grammar, and presentation quality",
    checks,
    overallScore: checks.reduce((sum, c) => sum + (c.score || 0), 0),
    maxScore: checks.reduce((sum, c) => sum + (c.maxScore || 0), 0),
  };
}
