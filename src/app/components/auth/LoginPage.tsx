import { useState } from "react";
import { useNavigate, Link } from "react-router";
import { useAuth } from "../../context/AuthContext";
import { Loader2, Zap } from "lucide-react";

export function LoginPage() {
  const navigate = useNavigate();
  const { signIn, signInWithMagicLink } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [magicMode, setMagicMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [magicSent, setMagicSent] = useState(false);

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await signIn(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleMagicLink = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await signInWithMagicLink(email);
      setMagicSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send magic link");
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
          {magicSent ? (
            <div className="text-center">
              <div className="mb-3 text-2xl">✉️</div>
              <h2 className="mb-2">Check your email</h2>
              <p className="text-sm text-muted-foreground">
                We sent a magic link to <strong>{email}</strong>. Click the link to sign in.
              </p>
            </div>
          ) : (
            <>
              <h2 className="mb-6">Sign in</h2>

              {error && (
                <div className="mb-4 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                  {error}
                </div>
              )}

              {!magicMode ? (
                <form onSubmit={handlePasswordLogin} className="space-y-4">
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
                    Sign in
                  </button>
                </form>
              ) : (
                <form onSubmit={handleMagicLink} className="space-y-4">
                  <div>
                    <label htmlFor="magic-email" className="mb-1.5 block text-sm">Email</label>
                    <input
                      id="magic-email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      className="w-full rounded-lg border border-border bg-input-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none"
                      placeholder="you@company.com"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
                  >
                    {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                    Send magic link
                  </button>
                </form>
              )}

              <div className="mt-4 space-y-3">
                <button
                  type="button"
                  onClick={() => { setMagicMode(!magicMode); setError(null); }}
                  className="w-full text-sm text-muted-foreground underline underline-offset-2 hover:text-foreground"
                >
                  {magicMode ? "Use password instead" : "Sign in with magic link"}
                </button>

                <p className="text-center text-sm text-muted-foreground">
                  No account?{" "}
                  <Link to="/signup" className="text-primary hover:underline">
                    Sign up
                  </Link>
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
