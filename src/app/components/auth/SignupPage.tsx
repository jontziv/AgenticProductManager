import { useState } from "react";
import { useNavigate, Link } from "react-router";
import { useAuth } from "../../context/AuthContext";
import { Loader2, Zap } from "lucide-react";

export function SignupPage() {
  const navigate = useNavigate();
  const { signUp } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    try {
      await signUp(email, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign up failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
            <Zap className="h-6 w-6 text-primary-foreground" />
          </div>
          <h1 className="mb-1">PM Sidekick</h1>
          <p className="text-sm text-muted-foreground">Intake-to-Backlog Workbench</p>
        </div>

        <div className="rounded-xl border border-border bg-card p-8">
          {done ? (
            <div className="text-center">
              <div className="mb-3 text-2xl">✅</div>
              <h2 className="mb-2">Check your email</h2>
              <p className="text-sm text-muted-foreground">
                We sent a confirmation link to <strong>{email}</strong>. Once confirmed, you can{" "}
                <button
                  className="text-primary underline underline-offset-2"
                  onClick={() => navigate("/login")}
                >
                  sign in
                </button>
                .
              </p>
            </div>
          ) : (
            <>
              <h2 className="mb-6">Create account</h2>

              {error && (
                <div className="mb-4 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label htmlFor="email" className="mb-1.5 block text-sm">Email</label>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="w-full rounded-lg border border-border bg-input-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none"
                    placeholder="you@company.com"
                  />
                </div>
                <div>
                  <label htmlFor="password" className="mb-1.5 block text-sm">Password</label>
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={8}
                    className="w-full rounded-lg border border-border bg-input-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none"
                    placeholder="Min 8 characters"
                  />
                </div>
                <div>
                  <label htmlFor="confirm" className="mb-1.5 block text-sm">Confirm password</label>
                  <input
                    id="confirm"
                    type="password"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    required
                    className="w-full rounded-lg border border-border bg-input-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none"
                    placeholder="••••••••"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
                >
                  {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                  Create account
                </button>
              </form>

              <p className="mt-4 text-center text-sm text-muted-foreground">
                Already have an account?{" "}
                <Link to="/login" className="text-primary hover:underline">
                  Sign in
                </Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
