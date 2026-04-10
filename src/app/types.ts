export interface IdeaSubmission {
  title: string;
  description: string;
  targetAudience: string;
  businessGoals: string;
  constraints: string;
  timeline: string;
}

export interface UserPersona {
  name: string;
  role: string;
  goals: string[];
  painPoints: string[];
  behaviors: string[];
}

export interface UserStory {
  id: string;
  asA: string;
  iWant: string;
  soThat: string;
  acceptanceCriteria: string[];
  priority: "High" | "Medium" | "Low";
  estimatedEffort: string;
}

export interface TestCase {
  id: string;
  scenario: string;
  steps: string[];
  expectedResult: string;
  priority: "High" | "Medium" | "Low";
}

export interface RiskItem {
  category: string;
  description: string;
  impact: "High" | "Medium" | "Low";
  mitigation: string;
}

export interface GeneratedArtifacts {
  problemFraming: {
    problem: string;
    opportunity: string;
    hypothesis: string;
  };
  personas: UserPersona[];
  mvpScope: {
    inScope: string[];
    outOfScope: string[];
    coreFeatures: string[];
  };
  successMetrics: {
    category: string;
    metric: string;
    target: string;
  }[];
  userStories: UserStory[];
  backlogItems: {
    epic: string;
    stories: string[];
  }[];
  testCases: TestCase[];
  risks: RiskItem[];
  architecture: {
    recommendation: string;
    rationale: string;
    components: string[];
    dataFlow: string;
    considerations: string[];
  };
}

export interface WorkflowState {
  ideaSubmission?: IdeaSubmission;
  artifacts?: GeneratedArtifacts;
  currentStep: number;
}
