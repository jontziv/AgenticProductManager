import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { runsApi } from "../../api/runs";
import { useAuth } from "../../context/AuthContext";
import { RunCard } from "./RunCard";
import type { IntakeRunSummary } from "../../types/api";
import { Plus, Loader2, Zap, LogOut } from "lucide-react";

export function Dashboard() {
  const navigate = useNavigate();
  const { user, signOut } = useAuth();
  const [runs, setRuns] = useState<IntakeRunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    runsApi.list()
      .then(setRuns)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleSignOut = async () => {
    await signOut();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Zap className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="font-semibold">PM Sidekick</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{user?.email}</span>
            <button
              onClick={handleSignOut}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent"
            >
              <LogOut className="h-3.5 w-3.5" />
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-10">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="mb-1">Intake Runs</h1>
            <p className="text-muted-foreground">
              Each run converts your input into a full PM artifact pack.
            </p>
          </div>
          <button
            onClick={() => navigate("/new")}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm text-primary-foreground transition-opacity hover:opacity-90"
          >
            <Plus className="h-4 w-4" />
            New run
          </button>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-6 text-sm text-destructive">
            Failed to load runs: {error}
          </div>
        )}

        {!loading && !error && runs.length === 0 && (
          <div className="rounded-xl border border-dashed border-border bg-card py-20 text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <Zap className="h-6 w-6 text-primary" />
            </div>
            <h3 className="mb-2">No runs yet</h3>
            <p className="mb-6 text-sm text-muted-foreground">
              Start by submitting your first business idea or meeting notes.
            </p>
            <button
              onClick={() => navigate("/new")}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm text-primary-foreground transition-opacity hover:opacity-90"
            >
              <Plus className="h-4 w-4" />
              Create first run
            </button>
          </div>
        )}

        {!loading && !error && runs.length > 0 && (
          <div className="space-y-3">
            {runs.map((run) => (
              <RunCard key={run.id} run={run} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
