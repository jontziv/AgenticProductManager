"""
Centralized prompt registry.
All system prompts and message builders live here — no prompt text in node files.
Prompts are kept stable to maximize caching prefix reuse.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class PromptTemplate:
    system: str
    user_template: str

    def render_user(self, **kwargs: Any) -> str:
        return self.user_template.format(**kwargs)

    def build_messages(self, **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.system},
            {"role": "user", "content": self.render_user(**kwargs)},
        ]


# ── System instruction shared prefix (cached by Groq) ─────────────────────────

_PM_CONTEXT = (
    "You are a senior product manager assistant. "
    "Output structured JSON matching the required schema exactly. "
    "Separate facts from assumptions. "
    "Never invent metrics, user counts, integrations, or market evidence not present in the input. "
    "Be concise, specific, and decision-ready."
)

# ── Prompt registry ───────────────────────────────────────────────────────────

PROMPTS: dict[str, PromptTemplate] = {
    "detect_missing_info": PromptTemplate(
        system=_PM_CONTEXT,
        user_template=(
            "Review this intake submission and identify any CRITICAL missing information "
            "that would prevent generating high-quality PM artifacts.\n\n"
            "CRITICAL fields if absent: target user or user group, core problem/pain, "
            "primary outcome, major constraints, timeline or urgency.\n\n"
            "Submission:\n{submission}\n\n"
            "Return a list of missing_fields (empty if sufficient) and "
            "can_proceed (true if we can generate with assumptions)."
        ),
    ),
    "classify_idea": PromptTemplate(
        system=_PM_CONTEXT,
        user_template=(
            "Classify this product idea into ONE of these types:\n"
            "- new_product: entirely new standalone product\n"
            "- feature_addition: adds capability to an existing product\n"
            "- platform_improvement: infrastructure or developer-facing\n"
            "- internal_tool: built for internal teams only\n"
            "- api_product: API-first developer product\n"
            "- marketplace: connects buyers and sellers\n\n"
            "Idea: {business_idea}\n"
            "Target users: {target_users}"
        ),
    ),
    "choose_pattern": PromptTemplate(
        system=_PM_CONTEXT,
        user_template=(
            "Given the idea classification '{idea_type}', choose the best product pattern:\n"
            "- saas_webapp, mobile_first, api_first, data_platform, marketplace, internal_tool\n\n"
            "Idea summary: {business_idea}\n"
            "Return: selected_pattern and pattern_rationale."
        ),
    ),
    "problem_framing": PromptTemplate(
        system=_PM_CONTEXT,
        user_template=(
            "Generate a problem framing document for this product idea.\n\n"
            "Business idea: {business_idea}\n"
            "Target users: {target_users}\n"
            "Meeting notes: {meeting_notes}\n"
            "Raw requirements: {raw_requirements}\n"
            "Constraints: {constraints}\n"
            "Timeline: {timeline}\n"
            "Assumptions provided: {assumptions}\n\n"
            "Rules:\n"
            "- problem_statement: 1-2 sentences, grounded in user pain\n"
            "- opportunity: quantified business opportunity if evidence exists; otherwise indicate it's estimated\n"
            "- hypothesis: testable if/then statement\n"
            "- goals: 3-5 measurable goals\n"
            "- non_goals: what this explicitly does NOT address\n"
            "- assumptions: list what you had to assume due to missing data"
        ),
    ),
    "personas": PromptTemplate(
        system=_PM_CONTEXT,
        user_template=(
            "Generate 2-3 distinct user personas for this product.\n\n"
            "Target users: {target_users}\n"
            "Problem statement: {problem_statement}\n"
            "Business idea: {business_idea}\n\n"
            "Each persona needs: name, role, archetype (1-2 words), goals (3-4), "
            "pain_points (3-4), behaviors (3-4), jobs_to_be_done (2-3).\n"
            "Make personas distinct — different roles, different needs."
        ),
    ),
    "mvp_scope": PromptTemplate(
        system=_PM_CONTEXT,
        user_template=(
            "Define the MVP scope for this product.\n\n"
            "Problem statement: {problem_statement}\n"
            "Goals: {goals}\n"
            "Business idea: {business_idea}\n"
            "Constraints: {constraints}\n"
            "Timeline: {timeline}\n\n"
            "Define:\n"
            "- in_scope: what is included in the MVP (list)\n"
            "- out_of_scope: explicitly excluded with brief reason\n"
            "- core_features: 5-8 features, each with id (F001...), name, description, "
            "rationale, priority (P0/P1/P2)\n"
            "- deferred_features: post-MVP candidates"
        ),
    ),
    "success_metrics": PromptTemplate(
        system=_PM_CONTEXT,
        user_template=(
            "Define 4-6 success metrics for this MVP.\n\n"
            "Goals: {goals}\n"
            "Product pattern: {selected_pattern}\n"
            "Target users: {target_users}\n\n"
            "Each metric needs: id (M001...), category, metric_name, description, "
            "target (specific number/threshold), baseline (if known, else null), "
            "signal_type (leading/lagging), measurement_method.\n"
            "Include a mix of leading and lagging indicators."
        ),
    ),
    "user_stories": PromptTemplate(
        system=_PM_CONTEXT,
        user_template=(
            "Generate user stories for this MVP.\n\n"
            "Core features: {core_features}\n"
            "Personas: {persona_names}\n"
            "MVP scope: {in_scope}\n\n"
            "Rules:\n"
            "- One story per core feature minimum (P0 features get multiple)\n"
            "- Each story: id (US-001...), persona_ref (persona name), as_a, i_want, so_that\n"
            "- acceptance_criteria: 3-5 specific, testable criteria\n"
            "- priority: High/Medium/Low\n"
            "- estimated_effort: story points (1/2/3/5/8/13)\n"
            "- epic: grouping category\n"
            "- linked_test_ids: leave empty for now ([])"
        ),
    ),
    "backlog_items": PromptTemplate(
        system=_PM_CONTEXT,
        user_template=(
            "Organize user stories into epics with priority rationale.\n\n"
            "Stories: {stories_json}\n\n"
            "Group into 3-5 epics. Each epic needs: epic name, epic_description, "
            "story_ids list, priority_rationale.\n"
            "Return total_story_count."
        ),
    ),
    "test_cases": PromptTemplate(
        system=_PM_CONTEXT,
        user_template=(
            "Generate test cases for these user stories.\n\n"
            "Stories: {stories_json}\n"
            "Acceptance criteria: {acceptance_criteria}\n\n"
            "Rules:\n"
            "- Cover all P0/High priority acceptance criteria\n"
            "- Each test: id (TC-001...), story_id, scenario, preconditions, "
            "steps, expected_result, test_type (unit/integration/e2e/manual), priority\n"
            "- Include happy path, validation errors, and one edge case per story"
        ),
    ),
    "risks": PromptTemplate(
        system=_PM_CONTEXT,
        user_template=(
            "Identify product and technical risks.\n\n"
            "MVP scope: {in_scope}\n"
            "Architecture pattern: {selected_pattern}\n"
            "Constraints: {constraints}\n"
            "Assumptions: {assumptions}\n\n"
            "Generate 4-8 risks across: technical, business, user_experience, operational, compliance.\n"
            "Each risk: id (R001...), category, description, likelihood (High/Medium/Low), "
            "impact (High/Medium/Low), mitigation (specific action), owner (role), "
            "linked_artifact (which artifact this risk threatens, or null)."
        ),
    ),
    "architecture": PromptTemplate(
        system=_PM_CONTEXT,
        user_template=(
            "Generate 2 architecture options for this MVP (recommend 1).\n\n"
            "Product pattern: {selected_pattern}\n"
            "Core features: {core_features}\n"
            "Constraints: {constraints}\n"
            "Non-functional requirements context: scalability, cost, maintainability\n\n"
            "Each option: name, description, components (list), data_flow (narrative), "
            "pros (list), cons (list), cost_profile, recommended (true for 1, false for the other).\n"
            "Also provide: recommended_option (name), rationale, "
            "non_functional_requirements (list), technical_considerations (list)."
        ),
    ),
    "consistency_check": PromptTemplate(
        system=_PM_CONTEXT,
        user_template=(
            "Check cross-artifact consistency. Return issues (list of strings) and is_consistent (bool).\n\n"
            "Artifact summary:\n{summary}\n\n"
            "Check: do story_epics map to feature_ids? Do persona_roles align with story content? "
            "Do metric_names connect to goals? Are there contradictions or obvious gaps?"
        ),
    ),
}


def get_prompt(name: str) -> PromptTemplate:
    if name not in PROMPTS:
        raise KeyError(f"No prompt registered for: {name}")
    return PROMPTS[name]
