import { createBrowserRouter, Navigate } from "react-router";
import { LoginPage } from "./components/auth/LoginPage";
import { SignupPage } from "./components/auth/SignupPage";
import { Dashboard } from "./components/dashboard/Dashboard";
import { WorkflowLayout } from "./components/WorkflowLayout";
import { IdeaIntake } from "./components/steps/IdeaIntake";
import { ScopeReview } from "./components/steps/ScopeReview";
import { MVPBrief } from "./components/steps/MVPBrief";
import { Backlog } from "./components/steps/Backlog";
import { Architecture } from "./components/steps/Architecture";
import { QAEvaluation } from "./components/steps/QAEvaluation";
import { ApprovalReview } from "./components/steps/ApprovalReview";
import { ExportPack } from "./components/steps/ExportPack";
import { RequireAuth } from "./components/auth/RequireAuth";

export const router = createBrowserRouter([
  // ── Public ──────────────────────────────────────────────────────────────────
  { path: "/login", Component: LoginPage },
  { path: "/signup", Component: SignupPage },

  // ── Root redirect ──────────────────────────────────────────────────────────
  { index: true, element: <Navigate to="/dashboard" replace /> },

  // ── Protected ──────────────────────────────────────────────────────────────
  {
    path: "/dashboard",
    element: (
      <RequireAuth>
        <Dashboard />
      </RequireAuth>
    ),
  },

  // ── New run (intake form) ───────────────────────────────────────────────────
  {
    path: "/new",
    element: (
      <RequireAuth>
        <IdeaIntake />
      </RequireAuth>
    ),
  },

  // ── Run workflow ───────────────────────────────────────────────────────────
  {
    path: "/runs/:runId",
    element: (
      <RequireAuth>
        <WorkflowLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="scope" replace /> },
      { path: "processing", Component: ScopeReview },
      { path: "scope", Component: ScopeReview },
      { path: "mvp", Component: MVPBrief },
      { path: "backlog", Component: Backlog },
      { path: "architecture", Component: Architecture },
      { path: "qa", Component: QAEvaluation },
      { path: "approval", Component: ApprovalReview },
      { path: "export", Component: ExportPack },
    ],
  },
]);
