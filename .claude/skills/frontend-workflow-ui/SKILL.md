---
name: frontend-workflow-ui
description: Frontend architecture for the PM Sidekick React/TypeScript UI — routing, auth context, workflow context, step components, API client patterns, and hook conventions.
triggers:
  - "add a step"
  - "new page"
  - "frontend component"
  - "add a route"
  - "workflow ui"
  - "react component"
---

# Frontend Workflow UI

## Stack
- React 18 + TypeScript 5.7 + Vite
- React Router v7 (nested routes)
- Radix UI / shadcn components + Tailwind CSS
- Supabase JS client for auth
- Custom `ApiClient` for all backend calls

## Route structure

```
/login              → LoginPage (public)
/signup             → SignupPage (public)
/dashboard          → Dashboard (RequireAuth)
/new                → IdeaIntake (RequireAuth)
/runs/:runId        → WorkflowLayout (RequireAuth)
  /runs/:runId/processing → ScopeReview
  /runs/:runId/scope      → ScopeReview
  /runs/:runId/mvp        → MvpBrief
  /runs/:runId/backlog    → BacklogView
  /runs/:runId/architecture → ArchitectureView
  /runs/:runId/qa         → QaReview
  /runs/:runId/approval   → ApprovalReview
  /runs/:runId/export     → ExportPack
```

## Auth pattern

```tsx
// Wrap protected pages
<RequireAuth>
  <Dashboard />
</RequireAuth>

// Access auth state
const { user, signIn, signOut } = useAuth();
```

## Workflow context

```tsx
// Access current run + artifacts + job + QA report
const { state, setRun, setArtifact, setQaReport } = useWorkflow();
const run = state.run;
const problemFraming = state.artifacts["problem_framing"];
```

## API client pattern

```typescript
// All API calls go through apiClient — auto-attaches Bearer token
import { apiClient } from "@/app/api/client";
import { runsApi } from "@/app/api/runs";

// Create a run
const run = await runsApi.create({ title, raw_input, target_users });

// Get artifacts
const artifacts = await runsApi.getArtifacts(runId);

// Submit approval
await runsApi.submitApproval(runId, { approved: true, comment });

// Request export
await exportsApi.requestExport(runId, { format: "markdown" });
```

## Job polling hook

```typescript
// Auto-polls every 2.5s until terminal status
const { job, isPolling } = useJobPolling(runId, {
  onComplete: (job) => {
    // reload artifacts/run on completion
    setRun(await runsApi.get(runId));
  },
  onError: (job) => toast.error(`Job failed: ${job.error_message}`),
});
```

## Autosave hook

```typescript
// Debounced localStorage save — survives page refresh
const { saveDraft, loadDraft, clearDraft } = useAutosave<FormData>(
  "INTAKE_DRAFT",
  800 // ms debounce
);

// On mount: restore draft
useEffect(() => {
  const draft = loadDraft();
  if (draft) setFormData(draft);
}, []);

// On form change: save draft
onChange={(value) => {
  setFormData(value);
  saveDraft(value);
}}

// On successful submit: clear draft
await runsApi.create(formData);
clearDraft();
```

## Adding a new step

1. Create `src/app/components/steps/NewStep.tsx`
2. Add route to `src/app/routes.tsx` under `WorkflowLayout`
3. Add nav item to `StepNav` in `WorkflowLayout.tsx`
4. Connect to `WorkflowContext` for run/artifact state
5. Add any new API calls to the appropriate `src/app/api/*.ts` file
6. Add types to `src/app/types/api.ts` if new shapes are returned

## Artifact display pattern

```tsx
// Typed artifact content from WorkflowContext
const artifact = state.artifacts["problem_framing"];
if (!artifact) return <EmptyArtifact type="problem_framing" />;

const content = artifact.content as ProblemFramingContent;
return (
  <Card>
    <CardHeader><CardTitle>Problem Statement</CardTitle></CardHeader>
    <CardContent>{content.problem_statement}</CardContent>
  </Card>
);
```

## Error handling convention

```typescript
try {
  await runsApi.create(payload);
} catch (err) {
  if (err instanceof ApiClientError && err.isUnauthorized) {
    // Token expired — AuthContext handles redirect
    return;
  }
  toast.error(err instanceof ApiClientError ? err.message : "Unexpected error");
}
```

## Key file locations

| File | Purpose |
|------|---------|
| `src/app/api/client.ts` | Base ApiClient with auth headers |
| `src/app/api/runs.ts` | Run CRUD + artifacts + approvals |
| `src/app/api/jobs.ts` | Jobs, QA, exports API |
| `src/app/context/AuthContext.tsx` | Supabase auth state |
| `src/app/context/WorkflowContext.tsx` | Per-run artifact state |
| `src/app/hooks/useJobPolling.ts` | Polling hook |
| `src/app/hooks/useAutosave.ts` | localStorage draft hook |
| `src/app/types/api.ts` | All TypeScript types |
