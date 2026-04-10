-- ============================================================================
-- Seed data: realistic example run for local development / demos
-- Run: psql $DATABASE_URL -f supabase/seed.sql
-- NOTE: uses a hardcoded demo user UUID that matches the local Supabase
--       dev seed user. Change DEMO_USER_ID to match your local auth.users row.
-- ============================================================================

DO $$
DECLARE
    demo_user_id    UUID := '00000000-0000-0000-0000-000000000001';
    demo_run_id     UUID := '10000000-0000-0000-0000-000000000001';
    demo_job_id     UUID := '20000000-0000-0000-0000-000000000001';
BEGIN

-- ── Seed user profile (assumes auth.users row exists in local Supabase) ──────
INSERT INTO public.user_profiles (id, email, full_name)
VALUES (demo_user_id, 'demo@pm-sidekick.local', 'Demo PM')
ON CONFLICT (id) DO NOTHING;


-- ── Seed a completed intake run ───────────────────────────────────────────────
INSERT INTO public.intake_runs (
    id, user_id, title, status,
    raw_input, input_type, target_users, business_context, constraints,
    idea_type, completed_at
) VALUES (
    demo_run_id,
    demo_user_id,
    'Unified Customer Feedback Dashboard',
    'qa_passed',
    'Product managers at B2B SaaS companies spend 3+ hours weekly manually aggregating '
    'customer feedback from Intercom, Zendesk, and Slack. We want a unified dashboard '
    'that auto-classifies feedback by theme, sentiment, and urgency.',
    'text',
    'Product managers at B2B SaaS companies (50-500 employees)',
    'Internal tooling initiative. Q2 delivery target. Budget $50k.',
    '3-month timeline, team of 3 engineers, must integrate with Intercom first.',
    'feature',
    NOW()
) ON CONFLICT (id) DO NOTHING;


-- ── Seed problem_framing artifact ────────────────────────────────────────────
INSERT INTO public.artifacts (run_id, user_id, artifact_type, status, content, version)
VALUES (
    demo_run_id, demo_user_id, 'problem_framing', 'ready',
    '{
        "problem_statement": "Product managers at B2B SaaS companies spend 3+ hours weekly manually aggregating customer feedback from disparate tools, leading to delayed prioritization and missed signals.",
        "opportunity": "By automating feedback aggregation and classification, we can reclaim 2.5+ hours per PM per week across a target market of 50,000+ PMs.",
        "hypothesis": "If PMs have unified, auto-classified feedback in a single dashboard, they will make roadmap prioritization decisions 40% faster and catch critical issues 2x sooner.",
        "goals": [
            "Reduce weekly feedback aggregation time from 3h to <30 min",
            "Improve critical issue detection time by 50%",
            "Achieve >80% classification accuracy for theme and sentiment"
        ],
        "non_goals": [
            "Replace Intercom, Zendesk, or Slack",
            "Provide customer success or support workflows",
            "Mobile-native app in MVP"
        ],
        "assumptions": [
            "Target users already have active Intercom accounts",
            "Intercom API rate limits are acceptable for MVP polling frequency",
            "PMs are the primary consumers, not support agents"
        ]
    }'::jsonb,
    1
) ON CONFLICT DO NOTHING;


-- ── Seed personas artifact ────────────────────────────────────────────────────
INSERT INTO public.artifacts (run_id, user_id, artifact_type, status, content, version)
VALUES (
    demo_run_id, demo_user_id, 'personas', 'ready',
    '{
        "personas": [
            {
                "name": "Sarah Chen",
                "role": "Senior Product Manager",
                "company_size": "200-person SaaS company",
                "archetype": "Data-driven Analyst",
                "goals": [
                    "Make roadmap decisions backed by customer evidence",
                    "Reduce time spent on weekly feedback synthesis",
                    "Communicate prioritization rationale to engineering clearly"
                ],
                "pain_points": [
                    "Spends Sunday evenings copy-pasting feedback from 4 tools",
                    "Misses urgent signals buried in Slack threads",
                    "Cannot show stakeholders which themes are trending"
                ],
                "behaviors": [
                    "Checks Intercom and Zendesk daily",
                    "Runs weekly theme-tagging sessions with the team",
                    "Exports to spreadsheets for board presentations"
                ],
                "jobs_to_be_done": [
                    "Know which customer problems are trending this week",
                    "Build a defensible backlog for quarterly planning",
                    "Report to leadership on what customers are asking for"
                ]
            },
            {
                "name": "Marcus Rodriguez",
                "role": "Head of Product",
                "company_size": "400-person SaaS company",
                "archetype": "Strategic Decision Maker",
                "goals": [
                    "Set clear quarterly OKRs grounded in customer reality",
                    "Keep PM team focused, not buried in research",
                    "Demonstrate product ROI to the board"
                ],
                "pain_points": [
                    "PMs give conflicting signals because they sample feedback differently",
                    "No single source of truth for customer-driven prioritization",
                    "Cannot quickly validate if a theme is growing or shrinking"
                ],
                "behaviors": [
                    "Reviews product metrics weekly",
                    "Runs bi-weekly roadmap reviews",
                    "Strongly data-driven in investment decisions"
                ],
                "jobs_to_be_done": [
                    "Allocate team focus to highest-signal customer problems",
                    "Justify roadmap decisions with quantified customer evidence",
                    "Identify emerging segments worth investing in"
                ]
            }
        ]
    }'::jsonb,
    1
) ON CONFLICT DO NOTHING;


-- ── Seed user_stories artifact (2 stories) ───────────────────────────────────
INSERT INTO public.artifacts (run_id, user_id, artifact_type, status, content, version)
VALUES (
    demo_run_id, demo_user_id, 'user_stories', 'ready',
    '{
        "stories": [
            {
                "id": "US-001",
                "persona_ref": "Sarah Chen",
                "as_a": "Senior Product Manager",
                "i_want": "to view all customer feedback from Intercom in a single dashboard",
                "so_that": "I can identify trending themes without switching between tools",
                "acceptance_criteria": [
                    "Dashboard loads all Intercom conversations from the last 30 days by default",
                    "Feedback is auto-classified by theme (bug, feature request, UX friction, praise)",
                    "Dashboard renders in under 2 seconds for up to 500 items",
                    "Filter by date range, theme, and sentiment is available without page reload"
                ],
                "priority": "High",
                "estimated_effort": "8",
                "epic": "Core Dashboard",
                "linked_test_ids": ["TC-001", "TC-002"]
            },
            {
                "id": "US-002",
                "persona_ref": "Marcus Rodriguez",
                "as_a": "Head of Product",
                "i_want": "to see a weekly trend chart of feedback themes",
                "so_that": "I can track whether critical issues are growing or resolving",
                "acceptance_criteria": [
                    "Trend chart shows theme frequency over the last 12 weeks",
                    "Chart updates automatically when new feedback is ingested",
                    "Can export chart as PNG for board presentations",
                    "Each theme is clickable to drill into individual feedback items"
                ],
                "priority": "Medium",
                "estimated_effort": "5",
                "epic": "Analytics",
                "linked_test_ids": ["TC-003"]
            }
        ]
    }'::jsonb,
    1
) ON CONFLICT DO NOTHING;


-- ── Seed architecture artifact ────────────────────────────────────────────────
INSERT INTO public.artifacts (run_id, user_id, artifact_type, status, content, version)
VALUES (
    demo_run_id, demo_user_id, 'architecture', 'ready',
    '{
        "options": [
            {
                "name": "Lightweight SaaS (Recommended)",
                "description": "React frontend + FastAPI backend + Supabase (auth/DB/storage) + Groq for classification",
                "components": ["Vercel (React)", "Render (FastAPI + Worker)", "Supabase (Postgres + Auth + Storage)", "Groq (llama-3.1-8b for classification)"],
                "data_flow": "User -> React (Vercel) -> FastAPI (Render) -> Groq classification -> Supabase Postgres",
                "pros": ["Ships in 3 months", "Low infrastructure overhead", "Predictable cost under $200/month at launch"],
                "cons": ["Groq rate limits may require throttling at scale", "MemorySaver checkpoints are in-process only"],
                "cost_profile": "$50-150/month for first 100 active users",
                "recommended": true
            },
            {
                "name": "Self-hosted ML Pipeline",
                "description": "Same frontend but with self-hosted Llama + Kafka for ingestion + Redis for job queue",
                "components": ["Vercel (React)", "AWS ECS (API)", "Self-hosted Llama (GPU instance)", "Kafka", "Redis", "RDS Postgres"],
                "data_flow": "User -> React -> FastAPI -> Kafka -> Llama worker -> RDS",
                "pros": ["No vendor LLM dependency", "Higher throughput ceiling"],
                "cons": ["3-4 months extra to set up", "GPU instance cost ~$600/month", "Overkill for MVP scale"],
                "cost_profile": "$800-1500/month baseline",
                "recommended": false
            }
        ],
        "recommended_option": "Lightweight SaaS (Recommended)",
        "rationale": "Matches the 3-month timeline and $50k budget. Groq provides sufficient classification quality for MVP. Supabase eliminates auth and storage infrastructure work. Can migrate to self-hosted if usage exceeds 1000 daily active users.",
        "non_functional_requirements": [
            "Dashboard loads in <2s for 500 items",
            "99.5% API uptime SLA",
            "Feedback classification <3s per item",
            "GDPR-compliant data storage"
        ],
        "technical_considerations": [
            "Implement webhook ingestion from Intercom to avoid polling limits",
            "Use Supabase Realtime for live dashboard updates",
            "Cache classification results to reduce Groq API costs",
            "Rate-limit ingestion worker to stay within Groq free-tier limits during development"
        ]
    }'::jsonb,
    1
) ON CONFLICT DO NOTHING;


-- ── Seed QA report ────────────────────────────────────────────────────────────
INSERT INTO public.qa_reports (
    run_id, user_id, overall_score, max_score, pass_rate,
    critical_issues, export_ready, checks, remediation_tasks
) VALUES (
    demo_run_id, demo_user_id, 87, 100, 87.0,
    0, true,
    '[
        {"id": "F001", "category": "Faithfulness", "name": "Problem Grounding", "status": "passed", "score": 10, "max_score": 10, "detail": "Problem statement grounded in stated user pain points."},
        {"id": "C001", "category": "Completeness", "name": "Artifact Coverage", "status": "passed", "score": 15, "max_score": 15, "detail": "All required artifact types present."},
        {"id": "C002", "category": "Compliance", "name": "Story AC Count", "status": "passed", "score": 10, "max_score": 10, "detail": "All high-priority stories have >=3 acceptance criteria."},
        {"id": "P004", "category": "Completeness", "name": "Architecture Recommendation", "status": "passed", "score": 10, "max_score": 10, "detail": "Recommended option specified with rationale."}
    ]'::jsonb,
    '[]'::jsonb
) ON CONFLICT (run_id) DO NOTHING;


-- ── Seed a completed job record ───────────────────────────────────────────────
INSERT INTO public.queued_jobs (
    id, run_id, user_id, job_type, status,
    payload, retry_count, completed_at
) VALUES (
    demo_job_id,
    demo_run_id,
    demo_user_id,
    'orchestrate_run',
    'completed',
    '{"run_id": "10000000-0000-0000-0000-000000000001"}'::jsonb,
    0,
    NOW()
) ON CONFLICT (id) DO NOTHING;

END;
$$;
