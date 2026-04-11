import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router";
import { useAuth } from "../../context/AuthContext";
import { runsApi } from "../../api/runs";
import { useAutosave, loadDraft, clearDraft } from "../../hooks/useAutosave";
import type { CreateRunPayload } from "../../types/api";
import { ArrowRight, Loader2, Zap, LayoutDashboard, Upload, X } from "lucide-react";

const DRAFT_KEY = "new_run_intake";

type FormData = Omit<CreateRunPayload, "audio_file_url">;

const inputClass =
  "w-full rounded-lg border border-border bg-input-background px-4 py-2.5 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none";

function Field({
  id,
  label,
  required,
  hint,
  children,
}: {
  id: string;
  label: string;
  required?: boolean;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium">
        {label}
        {required && <span className="ml-1 text-destructive">*</span>}
        {hint && <span className="ml-2 text-xs font-normal text-muted-foreground">{hint}</span>}
      </label>
      {children}
    </div>
  );
}

const EMPTY_FORM: FormData = {
  title: "",
  business_idea: "",
  target_users: "",
  meeting_notes: "",
  raw_requirements: "",
  constraints: "",
  timeline: "",
  assumptions: "",
};

export function IdeaIntake() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [form, setForm] = useState<FormData>(() => {
    const draft = loadDraft<FormData>(DRAFT_KEY);
    // Merge with EMPTY_FORM so any old draft missing new required fields gets defaults
    return draft ? { ...EMPTY_FORM, ...draft } : EMPTY_FORM;
  });
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useAutosave(DRAFT_KEY, form);

  // Redirect to login if somehow landed here unauthenticated
  useEffect(() => {
    if (!user) navigate("/login");
  }, [user, navigate]);

  const isValid = form.title?.trim() && form.business_idea?.trim() && form.target_users?.trim() && form.raw_requirements?.trim();

  const handleChange = (field: keyof FormData, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid) return;
    setError(null);
    setLoading(true);

    try {
      const run = await runsApi.create({
        ...form,
        // Audio upload would be handled separately via storage presigned URL
      });
      clearDraft(DRAFT_KEY);
      navigate(`/runs/${run.id}/processing`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create run");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            <span className="font-semibold">PM Sidekick</span>
          </div>
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-10">
        <div className="mb-8">
          <h1 className="mb-2">New Intake Run</h1>
          <p className="text-muted-foreground">
            Provide your business context. The more detail you include, the higher the artifact quality. Required fields are marked <span className="text-destructive">*</span>.
          </p>
        </div>

        {error && (
          <div className="mb-6 rounded-xl border border-destructive/20 bg-destructive/5 px-5 py-4 text-sm text-destructive">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="rounded-xl border border-border bg-card p-6">
            <h2 className="mb-5 text-base">Core information</h2>
            <div className="space-y-5">
              <Field id="title" label="Run title" required hint="A short internal label for this run">
                <input
                  id="title"
                  type="text"
                  value={form.title}
                  onChange={(e) => handleChange("title", e.target.value)}
                  placeholder="e.g., Customer Feedback Analytics Dashboard — Q2 2026"
                  className={inputClass}
                  required
                />
              </Field>

              <Field id="business_idea" label="Business idea / opportunity" required>
                <textarea
                  id="business_idea"
                  value={form.business_idea}
                  onChange={(e) => handleChange("business_idea", e.target.value)}
                  placeholder="Describe the product opportunity, the pain being solved, and why it matters now..."
                  rows={5}
                  className={`${inputClass} resize-none`}
                  required
                />
              </Field>

              <Field id="target_users" label="Target users" required>
                <input
                  id="target_users"
                  type="text"
                  value={form.target_users}
                  onChange={(e) => handleChange("target_users", e.target.value)}
                  placeholder="e.g., Product managers at mid-market B2B SaaS companies (50–500 employees)"
                  className={inputClass}
                  required
                />
              </Field>

              <Field id="raw_requirements" label="Raw requirements" required hint="What the system must do — stakeholder language is fine">
                <textarea
                  id="raw_requirements"
                  value={form.raw_requirements ?? ""}
                  onChange={(e) => handleChange("raw_requirements", e.target.value)}
                  placeholder="Users need to be able to... The system must... It would be great if..."
                  rows={4}
                  className={`${inputClass} resize-none`}
                  required
                />
              </Field>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-6">
            <h2 className="mb-5 text-base">Supporting context</h2>
            <div className="space-y-5">
              <Field id="meeting_notes" label="Meeting notes" hint="Paste raw notes from stakeholder sessions">
                <textarea
                  id="meeting_notes"
                  value={form.meeting_notes ?? ""}
                  onChange={(e) => handleChange("meeting_notes", e.target.value)}
                  placeholder="Paste meeting notes, conversation summaries, or call transcripts..."
                  rows={5}
                  className={`${inputClass} resize-none`}
                />
              </Field>

              <div className="grid grid-cols-2 gap-5">
                <Field id="constraints" label="Known constraints">
                  <input
                    id="constraints"
                    type="text"
                    value={form.constraints ?? ""}
                    onChange={(e) => handleChange("constraints", e.target.value)}
                    placeholder="Budget, team size, tech stack, compliance..."
                    className={inputClass}
                  />
                </Field>

                <Field id="timeline" label="Timeline">
                  <input
                    id="timeline"
                    type="text"
                    value={form.timeline ?? ""}
                    onChange={(e) => handleChange("timeline", e.target.value)}
                    placeholder="e.g., Q2 2026, 3 months, ASAP"
                    className={inputClass}
                  />
                </Field>
              </div>

              <Field id="assumptions" label="Assumptions" hint="What are you assuming is true?">
                <textarea
                  id="assumptions"
                  value={form.assumptions ?? ""}
                  onChange={(e) => handleChange("assumptions", e.target.value)}
                  placeholder="We assume users already have X... We assume the backend team can deliver Y by..."
                  rows={3}
                  className={`${inputClass} resize-none`}
                />
              </Field>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-6">
            <h2 className="mb-2 text-base">Audio notes</h2>
            <p className="mb-4 text-sm text-muted-foreground">
              Upload a recording and it will be transcribed and included as source context.
            </p>
            {audioFile ? (
              <div className="flex items-center justify-between rounded-lg border border-border bg-accent/30 px-4 py-3">
                <div>
                  <div className="text-sm font-medium">{audioFile.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {(audioFile.size / (1024 * 1024)).toFixed(1)} MB
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setAudioFile(null)}
                  className="rounded p-1 text-muted-foreground hover:text-foreground"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <label className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border border-dashed border-border p-6 text-center transition-colors hover:border-primary/40 hover:bg-accent/20">
                <Upload className="h-6 w-6 text-muted-foreground" />
                <div className="text-sm text-muted-foreground">
                  Click to upload or drag and drop
                  <div className="text-xs">MP3, MP4, WAV, M4A · max 25 MB</div>
                </div>
                <input
                  type="file"
                  accept="audio/*,video/mp4"
                  className="hidden"
                  onChange={(e) => setAudioFile(e.target.files?.[0] ?? null)}
                />
              </label>
            )}
          </div>

          <div className="flex items-center justify-between pt-2">
            <p className="text-xs text-muted-foreground">
              Draft auto-saved to browser storage
            </p>
            <button
              type="submit"
              disabled={!isValid || loading}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-sm text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ArrowRight className="h-4 w-4" />
              )}
              {loading ? "Submitting..." : "Start analysis"}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
