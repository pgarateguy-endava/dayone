"""Seed the bench DB with dummy catalog data (dev migration).

Idempotent: running it twice does not duplicate rows (it wipes and reloads the
catalog tables, preserving people / person_tasks / check_ins).

    BENCH_ENABLED=1 uv run python -m bench.seed
"""
from __future__ import annotations

from bench.db import connect

PROFILES = [
    ("backend-dev", "Backend Developer",
     "Backend developers working on API services, integration, testing and staging deployment."),
    ("frontend-dev", "Frontend Developer",
     "Frontend developers working on web apps, the design system and API consumption."),
    ("senior-dev", "Senior Developer",
     "Senior engineers expected to lead modules, review PRs and mentor while on bench."),
]

PROFILE_PERMISSIONS = {
    "backend-dev": [("aws", "staging-read-write"), ("aws", "prod-read-only"),
                    ("aws", "cloudwatch-read"), ("aws", "secrets-read-dev"),
                    ("repositories", "read-write"),
                    ("ci_cd", "view-build-logs"), ("ci_cd", "trigger-staging-pipeline"),
                    ("ci_cd", "deploy-to-staging")],
    "frontend-dev": [("aws", "staging-read"), ("aws", "cloudwatch-read"),
                     ("repositories", "read-write"),
                     ("ci_cd", "view-build-logs"), ("ci_cd", "trigger-preview-deploy")],
    "senior-dev": [("aws", "staging-read-write"), ("aws", "prod-read-only"),
                   ("aws", "cloudwatch-read"), ("repositories", "read-write"),
                   ("ci_cd", "view-build-logs"), ("ci_cd", "deploy-to-staging"),
                   ("ci_cd", "approve-prod-pipeline")],
}

PROFILE_APPROVALS = {
    "backend-dev": ["prod-write", "secrets-prod-read", "admin-access"],
    "frontend-dev": ["production-deploy", "prod-secrets-read"],
    "senior-dev": ["prod-write", "admin-access"],
}

TRACKS = [
    ("aws-backend-track", "AWS Backend Upskilling Track", 6,
     ["backend-dev", "senior-dev"]),
    ("frontend-modern-track", "Modern Frontend Upskilling Track", 4,
     ["frontend-dev"]),
]

RESPONSIBLES = {
    "aws-backend-track": [("People Lead (example)", "people.lead@example.com", "people-lead"),
                          ("Resourcing (example)", "resourcing@example.com", "resourcing")],
    "frontend-modern-track": [("People Lead (example)", "people.lead@example.com", "people-lead")],
}

# (track, title, description, category, due_date, follow_up, est_hours, link,
#  evidence_required, requires_approval, sort, contacts[(name, email, note)])
TASKS = [
    ("aws-backend-track", "AWS Cloud Practitioner Essentials",
     "Complete the full course and log progress percentage daily.",
     "course", "2026-07-24", "twice_daily", 12,
     "https://skillbuilder.aws/", 1, 0, 1,
     [("Juan Pérez", "juan.perez@example.com", "Took this course last quarter, ask him anything.")]),
    ("aws-backend-track", "Building Serverless APIs on AWS",
     "Udemy Business course; do the hands-on labs, not just the videos.",
     "course", "2026-08-01", "daily", 10,
     "https://www.udemy.com/", 1, 0, 2,
     [("María Gómez", "maria.gomez@example.com", "Discipline lead for backend, can review your labs.")]),
    ("aws-backend-track", "Generative AI agents with Amazon Bedrock",
     "Focus on AgentCore and agent-with-tools patterns.",
     "course", "2026-08-08", "daily", 8,
     "https://skillbuilder.aws/", 1, 0, 3,
     [("Juan Pérez", "juan.perez@example.com", "Ran the internal AgentCore workshop.")]),
    ("aws-backend-track", "Update Endava profile",
     "Summary, AWS and agentic-AI skills with evidence, certifications section; then request review.",
     "profile_update", "2026-07-21", "daily", 3,
     "docs/endava/profile-guidelines.md", 1, 0, 4,
     [("People Lead (example)", "people.lead@example.com", "Reviews and signs off the profile.")]),
    ("aws-backend-track", "Book certification exam (SAA or DVA)",
     "Choose AWS Solutions Architect Associate (preferred) or Developer Associate; voucher via People Lead.",
     "certification", "2026-08-04", "weekly", 1,
     "https://aws.amazon.com/certification/", 0, 1, 5,
     [("People Lead (example)", "people.lead@example.com", "Approves the exam voucher.")]),
    ("aws-backend-track", "Take the certification exam",
     "Sit the scheduled exam and register the result.",
     "certification", "2026-08-18", "weekly", 3,
     "https://aws.amazon.com/certification/", 1, 0, 6, []),
    ("aws-backend-track", "Portfolio: serverless-notes-api",
     "Small serverless CRUD API with IaC and tests, deployed to a sandbox account.",
     "portfolio", "2026-08-14", "daily", 20,
     "", 1, 0, 7,
     [("María Gómez", "maria.gomez@example.com", "Can review the architecture and the PRs.")]),
    ("aws-backend-track", "Contribute to the bench-onboarding agent repo",
     "Extend the workshop agent with a new tool or track, PR-based.",
     "portfolio", None, "biweekly", 8,
     "", 1, 0, 8, []),

    ("frontend-modern-track", "Advanced React Patterns",
     "Udemy Business course with exercises.",
     "course", "2026-07-28", "twice_daily", 10,
     "https://www.udemy.com/", 1, 0, 1,
     [("Lucía Fernández", "lucia.fernandez@example.com", "Frontend capability lead.")]),
    ("frontend-modern-track", "Web Performance Fundamentals",
     "Frontend Masters; apply the audit to a real app as evidence.",
     "course", "2026-08-04", "daily", 6,
     "https://frontendmasters.com/", 1, 0, 2, []),
    ("frontend-modern-track", "Update Endava profile",
     "Summary, framework and testing skills with evidence; then request review.",
     "profile_update", "2026-07-21", "daily", 3,
     "docs/endava/profile-guidelines.md", 1, 0, 3,
     [("People Lead (example)", "people.lead@example.com", "Reviews and signs off the profile.")]),
    ("frontend-modern-track", "Portfolio: design-system-showcase",
     "Component library with Storybook, tests and CI; demo to the capability lead.",
     "portfolio", "2026-08-04", "daily", 16,
     "", 1, 0, 4,
     [("Lucía Fernández", "lucia.fernandez@example.com", "Audience for the final demo.")]),
]


# (kind, title, provider, url, register_url, tags, notes)
KNOWLEDGE = [
    ("mandatory_course", "Claude Partner Network Learning Path", "Anthropic Skilljar",
     "https://anthropic.skilljar.com/page/claude-partner-network-learning-path",
     "https://endavauniversity.edcast.com/insights/claude-partner-network-learning-path",
     "", "Mandatory for everyone on bench. After finishing, register completion in Endava University."),
    ("certification", "AWS Certified Cloud Practitioner", "AWS", "https://aws.amazon.com/certification/certified-cloud-practitioner/", "", "aws", "Entry level."),
    ("certification", "AWS Certified AI Practitioner", "AWS", "https://aws.amazon.com/certification/certified-ai-practitioner/", "", "aws,ai", "Entry level, AI focus."),
    ("certification", "AWS Certified Solutions Architect - Associate", "AWS", "https://aws.amazon.com/certification/certified-solutions-architect-associate/", "", "aws", "Most requested by clients."),
    ("certification", "AWS Certified Developer - Associate", "AWS", "https://aws.amazon.com/certification/certified-developer-associate/", "", "aws,backend", "Code-focused."),
    ("certification", "AWS Certified Data Engineer - Associate", "AWS", "https://aws.amazon.com/certification/certified-data-engineer-associate/", "", "aws,data", ""),
    ("certification", "AWS Certified Solutions Architect - Professional", "AWS", "https://aws.amazon.com/certification/certified-solutions-architect-professional/", "", "aws,senior", "For seniors with an Associate cert."),
    ("certification", "AWS Certified DevOps Engineer - Professional", "AWS", "https://aws.amazon.com/certification/certified-devops-engineer-professional/", "", "aws,devops,senior", ""),
    ("certification", "Microsoft Azure Fundamentals (AZ-900)", "Microsoft", "https://learn.microsoft.com/credentials/certifications/azure-fundamentals/", "", "azure", "Entry level."),
    ("certification", "Azure Developer Associate (AZ-204)", "Microsoft", "https://learn.microsoft.com/credentials/certifications/azure-developer/", "", "azure,backend", ""),
    ("course", "AWS Certified AI Practitioner - Complete Course", "Udemy",
     "https://www.udemy.com/course/aws-ai-practitioner-certified/", "", "aws,ai", "Popular prep course."),
]


def seed() -> dict:
    """Wipe and reload catalog tables. Returns row counts."""
    with connect() as conn:
        for table in ("task_contacts", "tasks", "responsibles", "track_profiles",
                      "tracks", "profile_approvals", "profile_permissions", "profiles",
                      "knowledge"):
            conn.execute(f"DELETE FROM {table}")

        conn.executemany(
            "INSERT INTO knowledge (kind, title, provider, url, register_url, tags, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)", KNOWLEDGE)

        conn.executemany("INSERT INTO profiles (id, name, summary) VALUES (?, ?, ?)", PROFILES)
        for profile_id, perms in PROFILE_PERMISSIONS.items():
            conn.executemany(
                "INSERT INTO profile_permissions (profile_id, kind, value) VALUES (?, ?, ?)",
                [(profile_id, k, v) for k, v in perms])
        for profile_id, actions in PROFILE_APPROVALS.items():
            conn.executemany(
                "INSERT INTO profile_approvals (profile_id, action) VALUES (?, ?)",
                [(profile_id, a) for a in actions])

        for track_id, name, weeks, profile_ids in TRACKS:
            conn.execute("INSERT INTO tracks (id, name, duration_weeks) VALUES (?, ?, ?)",
                         (track_id, name, weeks))
            conn.executemany(
                "INSERT INTO track_profiles (track_id, profile_id) VALUES (?, ?)",
                [(track_id, p) for p in profile_ids])
        for track_id, rows in RESPONSIBLES.items():
            conn.executemany(
                "INSERT INTO responsibles (track_id, name, email, role) VALUES (?, ?, ?, ?)",
                [(track_id, *r) for r in rows])

        for (track_id, title, desc, cat, due, follow, hours, link,
             evidence, approval, sort, contacts) in TASKS:
            cursor = conn.execute(
                "INSERT INTO tasks (track_id, title, description, category, due_date, follow_up, "
                "est_hours, link, evidence_required, requires_approval, sort) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (track_id, title, desc, cat, due, follow, hours, link, evidence, approval, sort))
            conn.executemany(
                "INSERT INTO task_contacts (task_id, name, email, note) VALUES (?, ?, ?, ?)",
                [(cursor.lastrowid, *c) for c in contacts])

        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("profiles", "tracks", "tasks", "task_contacts")}
    return counts


def seed_if_empty() -> None:
    """Seed only when the catalog is empty (safe to call from app startup)."""
    with connect() as conn:
        empty = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0] == 0
    if empty:
        seed()


if __name__ == "__main__":
    print(seed())
