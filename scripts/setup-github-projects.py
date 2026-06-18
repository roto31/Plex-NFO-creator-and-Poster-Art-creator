#!/usr/bin/env python3
"""Configure GitHub Project 2 (master) and create per-sprint project boards.

Uses `gh project` CLI subcommands (field-list, item-edit, copy, create) instead of
hand-maintained GraphQL field IDs. Sprint boards are cloned from the master project
via `gh project copy` so custom fields (Status, Sprint, dates, Estimate) carry over.

Optional `gh project mark-template` on the master board only applies to org-owned
projects; user-owned projects (e.g. roto31) receive an API error and copy proceeds
without templating.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from datetime import date, timedelta
from pathlib import Path

OWNER = "roto31"
REPO = "roto31/Plex-NFO-creator-and-Poster-Art-creator"
MASTER_PROJECT = 2

SPRINT_META = [
    (1, "Repo & CI Foundation", "M0"),
    (2, "Core Services Bootstrap", "M0"),
    (3, "Job Runner & Secrets", "M0"),
    (4, "Spikes & Fixtures", "M0"),
    (5, "Rename Module", "M1"),
    (6, "Scraper HTTP Layer", "M1"),
    (7, "Scraper NFO Generation", "M1"),
    (8, "Scraper Tab Complete", "M1"),
    (9, "Artwork Extraction Core", "M1"),
    (10, "Artwork Tab Complete", "M1"),
    (11, "Settings & First Launch", "M2"),
    (12, "Metadata Generator Base", "M2"),
    (13, "Metadata Generator Extended", "M2"),
    (14, "Health Check & Scheduling", "M2"),
    (15, "Release 1.0.0", "M3"),
]

KICKOFF = date(2026, 6, 17)
ROADMAP_ISSUES = {
    87: (KICKOFF, KICKOFF + timedelta(weeks=8) - timedelta(days=1)),
    88: (KICKOFF + timedelta(weeks=8), KICKOFF + timedelta(weeks=20) - timedelta(days=1)),
    89: (KICKOFF + timedelta(weeks=20), KICKOFF + timedelta(weeks=28) - timedelta(days=1)),
    90: (KICKOFF + timedelta(weeks=28), KICKOFF + timedelta(weeks=30) - timedelta(days=1)),
}

GH = shutil.which("gh") or "/opt/homebrew/bin/gh"
ENV = os.environ.copy()
ENV["PATH"] = os.pathsep.join(
    p for p in ["/opt/homebrew/bin", "/usr/local/bin", ENV.get("PATH", "")] if p
)

AUTH_REFRESH_HINT = (
    "GitHub CLI token lacks the `project` scope.\n"
    "Refresh with:\n"
    "  gh auth refresh -h github.com -s project,read:project"
)


def run(cmd: list[str], check: bool = True) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, env=ENV)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{r.stderr or r.stdout}")
    return r.stdout.strip()


def gh_json(cmd: list[str]) -> dict | list:
    out = run([GH, *cmd[1:]] if cmd[0] == "gh" else cmd)
    return json.loads(out) if out else {}


def require_project_scope() -> None:
    r = subprocess.run(
        [GH, "auth", "status"],
        capture_output=True,
        text=True,
        env=ENV,
    )
    combined = f"{r.stdout}\n{r.stderr}"
    if r.returncode != 0 or "Logged in" not in combined:
        raise SystemExit("gh is not authenticated. Run: gh auth login")

    scope_line = ""
    for line in combined.splitlines():
        if "Token scopes:" in line:
            scope_line = line
            break
    if "project" not in scope_line:
        raise SystemExit(AUTH_REFRESH_HINT)


def discover_fields() -> tuple[str, dict[str, str], dict[str, dict[str, str]]]:
    """Return (project_id, field_name→id, field_name→{option_name→option_id})."""
    project = gh_json([
        "gh", "project", "view", str(MASTER_PROJECT),
        "--owner", OWNER, "--format", "json",
    ])
    project_id = project["id"]

    data = gh_json([
        "gh", "project", "field-list", str(MASTER_PROJECT),
        "--owner", OWNER, "--format", "json", "--limit", "50",
    ])
    field_ids: dict[str, str] = {}
    select_options: dict[str, dict[str, str]] = {}
    for field in data.get("fields", []):
        name = field["name"]
        field_ids[name] = field["id"]
        if field.get("options"):
            select_options[name] = {o["name"]: o["id"] for o in field["options"]}
    return project_id, field_ids, select_options


def set_field(
    project_id: str,
    item_id: str,
    field_id: str,
    value: dict,
) -> None:
    cmd = [
        GH, "project", "item-edit",
        "--id", item_id,
        "--project-id", project_id,
        "--field-id", field_id,
    ]
    if "singleSelectOptionId" in value:
        cmd.extend(["--single-select-option-id", value["singleSelectOptionId"]])
    elif "date" in value:
        cmd.extend(["--date", value["date"]])
    elif "number" in value:
        cmd.extend(["--number", str(value["number"])])
    else:
        raise ValueError(value)
    run(cmd)
    time.sleep(0.05)


def sprint_dates(n: int) -> tuple[str, str]:
    start = KICKOFF + timedelta(weeks=2 * (n - 1))
    end = start + timedelta(weeks=2) - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def ensure_sprint_field(
    field_ids: dict[str, str],
    select_options: dict[str, dict[str, str]],
) -> tuple[dict[str, str], str, dict[str, str], dict[str, dict[str, str]]]:
    if "Sprint" in field_ids:
        return select_options["Sprint"], field_ids["Sprint"], field_ids, select_options

    options = [f"Sprint {i:02d}" for i in range(1, 16)] + ["Roadmap"]
    opt_str = ",".join(options)
    try:
        gh_json([
            "gh", "project", "field-create", str(MASTER_PROJECT),
            "--owner", OWNER,
            "--name", "Sprint",
            "--data-type", "SINGLE_SELECT",
            "--single-select-options", opt_str,
            "--format", "json",
        ])
    except RuntimeError as e:
        if "already" not in str(e).lower():
            raise

    _, field_ids, select_options = discover_fields()
    if "Sprint" not in field_ids:
        raise RuntimeError("Sprint field missing after create conflict")
    return select_options["Sprint"], field_ids["Sprint"], field_ids, select_options


def maybe_mark_master_template() -> None:
    r = subprocess.run(
        [GH, "project", "mark-template", str(MASTER_PROJECT), "--owner", OWNER],
        capture_output=True,
        text=True,
        env=ENV,
    )
    if r.returncode == 0:
        print(f"Marked project {MASTER_PROJECT} as template")
    elif "Organization" in (r.stderr or r.stdout):
        print("Skipping mark-template (user-owned projects cannot be templates)")
    elif "already" in (r.stderr or r.stdout).lower():
        print(f"Project {MASTER_PROJECT} already marked as template")


def configure_master(
    project_id: str,
    field_ids: dict[str, str],
    status_options: dict[str, str],
    sprint_options: dict[str, str],
    sprint_field_id: str,
) -> None:
    run([
        GH, "project", "edit", str(MASTER_PROJECT), "--owner", OWNER,
        "--title", "Plex NFO Creator — Native macOS App (Master)",
        "--readme",
        "Master Kanban and Roadmap for all 15 sprints. "
        "Kanban: group by Sprint field. Roadmap: Start/Target dates. "
        "Per-sprint boards: Plex NFO Native — Sprint NN.",
    ])

    urls = gh_json([
        "gh", "issue", "list", "-R", REPO, "--label", "native-macos-app",
        "--state", "open", "--limit", "200", "--json", "url",
    ])
    for row in urls:
        url = row["url"]
        run([GH, "project", "item-add", str(MASTER_PROJECT), "--owner", OWNER, "--url", url], check=False)
        time.sleep(0.1)

    items = gh_json([
        "gh", "project", "item-list", str(MASTER_PROJECT), "--owner", OWNER,
        "--limit", "200", "--format", "json",
    ])["items"]

    status_field = field_ids["Status"]
    start_field = field_ids["Start date"]
    target_field = field_ids["Target date"]
    estimate_field = field_ids["Estimate"]

    configured = 0
    for item in items:
        item_id = item["id"]
        title = item.get("title") or item.get("content", {}).get("title", "")
        labels = item.get("labels") or []
        issue_num = (item.get("content") or {}).get("number")

        sprint_key = None
        pts = None
        m = re.search(r"\[Sprint (\d{2})\]\[(\d+)\]", title)
        if m:
            sprint_key = f"Sprint {m.group(1)}"
            pts = int(m.group(2))
        elif issue_num in ROADMAP_ISSUES:
            sprint_key = "Roadmap"
        else:
            for lb in labels:
                if lb.startswith("sprint-"):
                    sprint_key = f"Sprint {lb.split('-')[1]}"
                    break

        if sprint_key and sprint_key in sprint_options:
            set_field(
                project_id, item_id, sprint_field_id,
                {"singleSelectOptionId": sprint_options[sprint_key]},
            )

        if pts is not None:
            set_field(project_id, item_id, estimate_field, {"number": float(pts)})

        if issue_num in ROADMAP_ISSUES:
            start, end = ROADMAP_ISSUES[issue_num]
            set_field(project_id, item_id, start_field, {"date": start.isoformat()})
            set_field(project_id, item_id, target_field, {"date": end.isoformat()})
            set_field(
                project_id, item_id, status_field,
                {"singleSelectOptionId": status_options["Ready"]},
            )
        elif m:
            sn = int(m.group(1))
            start, end = sprint_dates(sn)
            set_field(project_id, item_id, start_field, {"date": start})
            set_field(project_id, item_id, target_field, {"date": end})
            status = status_options["Ready"] if sn == 1 else status_options["Backlog"]
            set_field(
                project_id, item_id, status_field,
                {"singleSelectOptionId": status},
            )

        configured += 1
        if configured % 10 == 0:
            print(f"  configured {configured}/{len(items)}…")

    print(f"Configured {configured} items on master project {MASTER_PROJECT}")


def add_sprint_items_from_master(pnum: int, sprint_num: int) -> None:
    """Add master-project items matching sprint label to a sprint board."""
    items = gh_json([
        "gh", "project", "item-list", str(MASTER_PROJECT), "--owner", OWNER,
        "--limit", "50", "--format", "json",
        "--query", f"label:sprint-{sprint_num:02d}",
    ]).get("items", [])
    for item in items:
        url = (item.get("content") or {}).get("url")
        if not url:
            continue
        run([GH, "project", "item-add", str(pnum), "--owner", OWNER, "--url", url], check=False)
        time.sleep(0.1)


def create_sprint_boards() -> list[dict]:
    existing = gh_json(["gh", "project", "list", "--owner", OWNER, "--format", "json"]).get("projects", [])
    existing_by_title = {p.get("title", ""): p for p in existing}

    maybe_mark_master_template()
    created: list[dict] = []

    for num, name, milestone in SPRINT_META:
        title = f"Plex NFO Native — Sprint {num:02d}: {name}"
        if title in existing_by_title:
            p = existing_by_title[title]
            created.append({
                "number": p["number"],
                "id": p["id"],
                "title": title,
                "sprint": num,
                "url": p["url"],
            })
            print(f"Exists: {title} (#{p['number']})")
            continue

        proj = gh_json([
            "gh", "project", "copy", str(MASTER_PROJECT),
            "--source-owner", OWNER,
            "--target-owner", OWNER,
            "--title", title,
            "--format", "json",
        ])
        pnum = proj["number"]
        pid = proj["id"]
        run([
            GH, "project", "edit", str(pnum), "--owner", OWNER,
            "--readme",
            f"Sprint {num:02d} board ({milestone}). "
            f"Plan: Native macOS App/Project Plans/Sprint Plans/Sprint-{num:02d}-*.md",
        ])
        run(
            [GH, "project", "link", str(pnum), "--owner", OWNER, "--repo", REPO.split("/")[1]],
            check=False,
        )

        add_sprint_items_from_master(pnum, num)

        entry = {"number": pnum, "id": pid, "title": title, "sprint": num, "url": proj["url"]}
        created.append(entry)
        existing_by_title[title] = entry
        print(f"Created: {title} (#{pnum})")
        time.sleep(0.3)

    return created


def run_check() -> None:
    require_project_scope()
    project_id, field_ids, select_options = discover_fields()
    sprint_opts, sprint_field_id, _, _ = ensure_sprint_field(field_ids, select_options)
    print(f"gh: {GH}")
    print(f"auth: project scope OK")
    print(f"master project id: {project_id}")
    print(f"fields discovered: {len(field_ids)} ({', '.join(sorted(field_ids))})")
    print(f"status options: {list(select_options.get('Status', {}))}")
    print(f"sprint field: {sprint_field_id} ({len(sprint_opts)} options)")
    boards = gh_json(["gh", "project", "list", "--owner", OWNER, "--format", "json"]).get("projects", [])
    sprint_titles = sum(
        1 for p in boards
        if p.get("title", "").startswith("Plex NFO Native — Sprint ")
    )
    print(f"existing sprint boards: {sprint_titles}/15")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate gh auth and field discovery only (no mutations)",
    )
    args = parser.parse_args()

    if not Path(GH).exists() and not shutil.which("gh"):
        raise SystemExit(f"gh not found (tried {GH})")

    require_project_scope()

    if args.check:
        run_check()
        return

    project_id, field_ids, select_options = discover_fields()
    sprint_options, sprint_field_id, field_ids, select_options = ensure_sprint_field(
        field_ids, select_options,
    )
    status_options = select_options.get("Status", {})
    if not status_options:
        raise RuntimeError("Status field or options not found on master project")

    print(f"Sprint field: {len(sprint_options)} options")
    configure_master(
        project_id, field_ids, status_options, sprint_options, sprint_field_id,
    )
    boards = create_sprint_boards()

    out = Path("Native macOS App/Project Plans/github-sprint-boards.json")
    payload = {
        "master": {
            "number": MASTER_PROJECT,
            "url": f"https://github.com/users/{OWNER}/projects/{MASTER_PROJECT}",
            "kanban_view": f"https://github.com/users/{OWNER}/projects/{MASTER_PROJECT}/views/7",
            "roadmap_view": f"https://github.com/users/{OWNER}/projects/{MASTER_PROJECT}/views/4",
            "sprint_field_id": sprint_field_id,
        },
        "sprint_boards": boards,
        "view_setup_note": (
            "Master Sprint Kanban: project view 7 (Sprint Kanban) — Column by Sprint, "
            "saved via GitHub UI (gh project cannot set view group-by). "
            "View 1 (Backlog) remains Status columns. "
            "Roadmap view 4 → ensure Start date / Target date columns visible."
        ),
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
