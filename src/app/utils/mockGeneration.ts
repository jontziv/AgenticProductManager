import { IdeaSubmission, GeneratedArtifacts } from "../types";

export function generateArtifacts(idea: IdeaSubmission): GeneratedArtifacts {
  return {
    problemFraming: {
      problem: `${idea.targetAudience} struggle to efficiently ${idea.description.toLowerCase().slice(0, 50)}... due to fragmented tools and manual processes.`,
      opportunity: `By consolidating these workflows into a unified platform, we can reduce time spent on routine tasks by 40% and improve decision quality.`,
      hypothesis: `If we provide ${idea.targetAudience} with an integrated solution for ${idea.title.toLowerCase()}, they will adopt it as their primary tool within 30 days of onboarding.`,
    },
    personas: [
      {
        name: "Sarah Chen",
        role: "Senior Product Manager",
        goals: [
          "Reduce time spent on documentation",
          "Improve stakeholder alignment",
          "Data-driven decision making",
        ],
        painPoints: [
          "Manual compilation of requirements",
          "Scattered feedback across tools",
          "Limited visibility into progress",
        ],
        behaviors: [
          "Uses Jira and Notion daily",
          "Runs weekly sprint planning",
          "Reviews metrics every morning",
        ],
      },
      {
        name: "Marcus Rodriguez",
        role: "Lead Engineer",
        goals: [
          "Clear technical requirements",
          "Minimize context switching",
          "Early risk identification",
        ],
        painPoints: [
          "Ambiguous user stories",
          "Last-minute scope changes",
          "Insufficient technical specs",
        ],
        behaviors: [
          "Prefers written documentation",
          "Reviews PRs in batches",
          "Participates in planning sessions",
        ],
      },
    ],
    mvpScope: {
      inScope: [
        "Core intake form with AI analysis",
        "Automated artifact generation",
        "Basic export functionality (PDF, Markdown)",
        "Single-user workflow",
      ],
      outOfScope: [
        "Multi-user collaboration",
        "Real-time editing",
        "Integration with Jira/Linear APIs",
        "Custom AI training",
        "Advanced analytics dashboard",
      ],
      coreFeatures: [
        "Structured idea intake with guided prompts to capture business context, target users, and constraints",
        "AI-powered problem framing that generates hypothesis and opportunity statements based on submission",
        "Automated persona generation with goals, pain points, and behavioral patterns relevant to the idea",
        "MVP scope recommendation with clear in/out-of-scope boundaries and feature prioritization",
        "User story generation with acceptance criteria, priorities, and effort estimates",
        "Test case creation covering critical user flows with steps and expected outcomes",
        "Risk identification across technical, business, and operational dimensions with mitigation strategies",
        "Lightweight architecture recommendation with component breakdown and data flow guidance",
      ],
    },
    successMetrics: [
      {
        category: "Adoption",
        metric: "PMs using tool for new projects",
        target: "60% in 90 days",
      },
      {
        category: "Efficiency",
        metric: "Time to generate artifacts",
        target: "< 10 minutes",
      },
      {
        category: "Quality",
        metric: "Artifacts requiring major revision",
        target: "< 20%",
      },
      {
        category: "Satisfaction",
        metric: "PM satisfaction score (NPS)",
        target: "> 40",
      },
    ],
    userStories: [
      {
        id: "US-001",
        asA: "Product Manager",
        iWant: "to submit a business idea with key context",
        soThat: "the system can generate relevant product artifacts",
        acceptanceCriteria: [
          "Form accepts title, description, audience, goals, and constraints",
          "Required fields are validated before submission",
          "Data is persisted throughout the workflow",
        ],
        priority: "High",
        estimatedEffort: "3 points",
      },
      {
        id: "US-002",
        asA: "Product Manager",
        iWant: "to review AI-generated problem framing",
        soThat: "I can validate the system understands my idea",
        acceptanceCriteria: [
          "Problem statement reflects the submission",
          "Opportunity is clearly articulated",
          "Hypothesis is testable and specific",
        ],
        priority: "High",
        estimatedEffort: "5 points",
      },
      {
        id: "US-003",
        asA: "Product Manager",
        iWant: "to see user personas for my target audience",
        soThat: "I can ensure we're building for the right users",
        acceptanceCriteria: [
          "At least 2 distinct personas are generated",
          "Each persona has goals, pain points, and behaviors",
          "Personas are relevant to the stated audience",
        ],
        priority: "High",
        estimatedEffort: "5 points",
      },
      {
        id: "US-004",
        asA: "Product Manager",
        iWant: "to export all artifacts as a PDF package",
        soThat: "I can share with stakeholders and archive documentation",
        acceptanceCriteria: [
          "Export includes all generated artifacts",
          "PDF is well-formatted and readable",
          "Download completes within 5 seconds",
        ],
        priority: "Medium",
        estimatedEffort: "8 points",
      },
      {
        id: "US-005",
        asA: "Product Manager",
        iWant: "to see prioritized user stories with acceptance criteria",
        soThat: "I can hand off clear requirements to engineering",
        acceptanceCriteria: [
          "Stories follow standard format (As a/I want/So that)",
          "Acceptance criteria are specific and testable",
          "Priority and effort estimates are included",
        ],
        priority: "High",
        estimatedEffort: "8 points",
      },
    ],
    backlogItems: [
      {
        epic: "Core Workflow",
        stories: ["US-001", "US-002", "US-003"],
      },
      {
        epic: "Artifact Generation",
        stories: ["US-005"],
      },
      {
        epic: "Export & Distribution",
        stories: ["US-004"],
      },
    ],
    testCases: [
      {
        id: "TC-001",
        scenario: "Submit valid idea and generate artifacts",
        steps: [
          "Navigate to intake form",
          "Fill all required fields with valid data",
          "Click 'Analyze Idea'",
          "Wait for generation to complete",
        ],
        expectedResult: "All artifacts generated successfully within 10 seconds",
        priority: "High",
      },
      {
        id: "TC-002",
        scenario: "Attempt submission with missing required fields",
        steps: [
          "Navigate to intake form",
          "Leave title field empty",
          "Attempt to submit",
        ],
        expectedResult: "Submit button disabled, validation message shown",
        priority: "High",
      },
      {
        id: "TC-003",
        scenario: "Navigate backward through workflow",
        steps: [
          "Complete idea submission",
          "Navigate to scope review",
          "Click 'Back' button",
        ],
        expectedResult: "Return to intake form with data preserved",
        priority: "Medium",
      },
      {
        id: "TC-004",
        scenario: "Export artifacts as PDF",
        steps: [
          "Complete full workflow",
          "Navigate to export screen",
          "Click 'PDF Package'",
        ],
        expectedResult: "PDF downloads with all sections included",
        priority: "Medium",
      },
    ],
    risks: [
      {
        category: "Technical",
        description: "AI generation quality inconsistent across different idea types",
        impact: "High",
        mitigation: "Implement validation layer, gather user feedback, build prompt library for common patterns",
      },
      {
        category: "User Experience",
        description: "Users bypass review steps and export without validation",
        impact: "Medium",
        mitigation: "Add explicit confirmation prompts, track skip rates, surface quality warnings",
      },
      {
        category: "Business",
        description: "Low adoption due to preference for existing tools (Notion, Confluence)",
        impact: "High",
        mitigation: "Integrate with existing tools via export, offer templates, demonstrate time savings",
      },
      {
        category: "Operational",
        description: "AI costs scale faster than user value, affecting unit economics",
        impact: "Medium",
        mitigation: "Implement caching for similar requests, offer tiered pricing, optimize prompt efficiency",
      },
    ],
    architecture: {
      recommendation: "Lightweight Web Application with AI Service Integration",
      rationale:
        "Given the MVP scope focuses on single-user workflows and artifact generation, a simple client-server architecture with a managed AI service provides the best balance of speed-to-market and scalability. This avoids premature complexity while allowing future expansion.",
      components: [
        "React frontend with form state management",
        "Node.js API server handling workflow orchestration",
        "AI service integration (OpenAI/Anthropic) for generation",
        "PostgreSQL for persisting submissions and artifacts",
        "PDF generation service for exports",
        "Object storage (S3) for generated documents",
      ],
      dataFlow: `1. User submits idea via React form
2. API validates and stores submission in PostgreSQL
3. API calls AI service with structured prompts for each artifact type
4. Generated artifacts stored in database and displayed to user
5. On export, artifacts are compiled and PDF generated
6. PDF stored in S3 and download link returned`,
      considerations: [
        "Start with synchronous generation (5-10s wait) before adding async queues",
        "Use prompt templates with variable injection for consistent artifact quality",
        "Implement basic rate limiting on AI calls to control costs during beta",
        "Store generated artifacts for reuse if user re-submits similar ideas",
        "Plan for export format extensibility (Markdown, CSV) from the start",
        "Consider versioning artifacts if users iterate on their submissions",
      ],
    },
  };
}
