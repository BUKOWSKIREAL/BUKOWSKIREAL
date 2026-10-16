#!/usr/bin/env python3
"""
Refresh the generated stats, project and open-source blocks in the profile README.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import urllib.parse
import urllib.request


LANG_COLORS = {
    "Python": "#3572A5",
    "Swift": "#F05138",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Shell": "#89e051",
    "Nix": "#7e7eff",
    "Go": "#00ADD8",
    "Typst": "#239dad",
    "CSS": "#563d7c",
    "HTML": "#e34c26",
    "C": "#555555",
    "C++": "#f34b7d",
}


def get_github_token() -> str:
    """Retrieve GitHub token from environment or gh CLI."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token.strip()
    try:
        res = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return ""


def github_graphql(query: str, token: str) -> dict:
    """Execute a GraphQL query against GitHub API."""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode("utf-8"),
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "BUKOWSKIREAL-ProfileGenerator",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def github_search(query: str, token: str) -> dict:
    """Search issues/PRs on GitHub API."""
    url = f"https://api.github.com/search/issues?q={urllib.parse.quote(query)}&per_page=100"
    headers = {
        "User-Agent": "BUKOWSKIREAL-ProfileGenerator",
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_stats(token: str) -> dict:
    """Fetch GitHub stats for user BUKOWSKIREAL."""
    gql = """
    query {
      user(login: "BUKOWSKIREAL") {
        contributionsCollection {
          contributionCalendar {
            totalContributions
          }
          totalCommitContributions
          totalPullRequestContributions
          totalIssueContributions
        }
        pullRequests(first: 1) {
          totalCount
        }
        issues(first: 1) {
          totalCount
        }
        repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
          totalCount
          nodes {
            name
            isPrivate
            stargazerCount
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                  color
                }
              }
            }
          }
        }
      }
    }
    """
    gql_resp = github_graphql(gql, token)
    user_data = gql_resp["data"]["user"]
    col = user_data["contributionsCollection"]

    total_contributions = col["contributionCalendar"]["totalContributions"]
    commits_1y = col["totalCommitContributions"]
    prs_1y = col["totalPullRequestContributions"]
    issues_1y = col["totalIssueContributions"]
    total_prs = user_data["pullRequests"]["totalCount"]
    total_issues = user_data["issues"]["totalCount"]

    repo_nodes = user_data["repositories"]["nodes"]
    total_stars = sum(r["stargazerCount"] for r in repo_nodes)
    repo_stars = {r["name"]: r["stargazerCount"] for r in repo_nodes}

    # Aggregate languages across public repos
    lang_sizes: dict[str, int] = {}
    lang_colors: dict[str, str] = {}
    for r in repo_nodes:
        if not r["isPrivate"]:
            for edge in r["languages"]["edges"]:
                lname = edge["node"]["name"]
                lcolor = edge["node"]["color"]
                lsize = edge["size"]
                lang_sizes[lname] = lang_sizes.get(lname, 0) + lsize
                if lcolor:
                    lang_colors[lname] = lcolor

    total_lang_size = sum(lang_sizes.values()) or 1
    languages = []
    for lname, lsize in sorted(lang_sizes.items(), key=lambda x: x[1], reverse=True):
        languages.append({
            "name": lname,
            "size": lsize,
            "percentage": round(lsize / total_lang_size * 100, 1),
            "color": lang_colors.get(lname) or LANG_COLORS.get(lname, "#888888"),
        })

    # Fetch external PRs and Issues
    prs_data = github_search("is:pr author:BUKOWSKIREAL -user:BUKOWSKIREAL", token)
    issues_data = github_search("is:issue author:BUKOWSKIREAL -user:BUKOWSKIREAL", token)

    pr_counts: dict[str, int] = {}
    for item in prs_data.get("items", []):
        repo = "/".join(item["repository_url"].split("/")[-2:])
        pr_counts[repo] = pr_counts.get(repo, 0) + 1

    issue_counts: dict[str, int] = {}
    for item in issues_data.get("items", []):
        repo = "/".join(item["repository_url"].split("/")[-2:])
        issue_counts[repo] = issue_counts.get(repo, 0) + 1

    target_repos = [
        "yetone/magpie",
        "steipete/CodexBar",
        "kenn-io/agentsview",
        "goodsmellvegetable/School_Running",
        "keleus/BewlyCat",
    ]

    external = {}
    for r in target_repos:
        name = r.split("/")[-1]
        external[name] = {
            "repo": r,
            "prs": pr_counts.get(r, 0),
            "issues": issue_counts.get(r, 0),
        }

    # Community = other external repos
    comm_prs = sum(v for k, v in pr_counts.items() if k not in target_repos)
    comm_issues = sum(v for k, v in issue_counts.items() if k not in target_repos)
    all_other_repos = sorted(list(
        set(list(pr_counts.keys()) + list(issue_counts.keys())) - set(target_repos)
    ))
    external["community"] = {
        "prs": comm_prs,
        "issues": comm_issues,
        "repos": all_other_repos,
    }

    return {
        "user": "BUKOWSKIREAL",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_stars": total_stars,
        "contributions_1y": total_contributions,
        "commits_1y": commits_1y,
        "prs_1y": prs_1y,
        "issues_1y": issues_1y,
        "total_prs": total_prs,
        "total_issues": total_issues,
        "repo_stars": repo_stars,
        "languages": languages,
        "external": external,
    }


USER = "BUKOWSKIREAL"

SELECTED_WORK = [
    ("🐦", "magpie-gemini-web", "Gemini Web & native Argon Task provider for Magpie", "Python · JS"),
    ("🧵", "trace", "Content-addressed local version tracker for CLI agents", "Python"),
    ("🖥️", "hotcorners", "Interactive macOS Hot Corners CLI manager", "Shell"),
    ("🪟", "scrollwm", "niri-style scrollable tiling window manager for macOS", "Swift"),
    ("🤝", "pi-fusion", "Persistent lead/sidekick orchestration for Pi", "TypeScript"),
    ("❄️", "nixos-config", "Daily NixOS configuration built around flakes", "Nix"),
]

OPEN_SOURCE = [
    ("magpie", "StepCode agent adaptation: model config & disconnect restore "
               "(merged in [8b39393](https://github.com/yetone/magpie/commit/8b393938f5a2a37a75b3b5ae034f51e3b5d12ef4), "
               "shipped in v0.1.1172)"),
    ("CodexBar", "Grok token history, StepFun credits & Claude/Codex pricing"),
    ("agentsview", "StepCode ingestion, Devin dedup & Antigravity effort"),
    ("School_Running", "macOS native console, curve trajectory & DMG release CI"),
    ("BewlyCat", "Homepage filter empty-state interaction & fixes"),
]

DISPLAY_NAMES = {"magpie": "Magpie"}

# Shown by name in the community row; the rest are counted
COMMUNITY_SHOWN = [
    "anomalyco/models.dev",
    "iAmCorey/Wake",
    "earendil-works/pi",
    "openai/codex",
]


def plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def render_stats(stats: dict) -> str:
    languages = [l for l in stats.get("languages", []) if l.get("percentage", 0) >= 1][:4]
    langs = " · ".join(f"{l['name']} {l['percentage']:.0f}%" for l in languages)
    return (
        f"⭐ **{stats.get('total_stars', 0)}** stars · "
        f"🔥 **{stats.get('contributions_1y', 0)}** contributions this year · "
        f"📝 **{stats.get('commits_1y', 0)}** commits · "
        f"🔀 **{stats.get('total_prs', 0)}** PRs · "
        f"🐛 **{stats.get('total_issues', 0)}** issues\n"
        f"<br/><sub>{langs}</sub>"
    )


def render_work(stats: dict) -> str:
    repo_stars = stats.get("repo_stars", {})
    lines = ["| | Project | What it does | ⭐ |", "|:-:|:--|:--|--:|"]
    for emoji, name, desc, lang in SELECTED_WORK:
        lines.append(
            f"| {emoji} | [**{name}**](https://github.com/{USER}/{name}) "
            f"| {desc} <sub>`{lang}`</sub> | {repo_stars.get(name, 0)} |"
        )
    return "\n".join(lines)


def render_open_source(stats: dict) -> str:
    external = stats.get("external", {})
    lines = ["| Project | What I worked on | PRs | Issues |", "|:--|:--|--:|--:|"]
    for name, desc in OPEN_SOURCE:
        e = external.get(name, {})
        repo = e.get("repo", "")
        prs, issues = e.get("prs", 0), e.get("issues", 0)
        pr_link = f"[{prs}](https://github.com/{repo}/pulls?q=is%3Apr+author%3A{USER})" if prs else "–"
        issue_link = f"[{issues}](https://github.com/{repo}/issues?q=is%3Aissue+author%3A{USER})" if issues else "–"
        lines.append(f"| [**{DISPLAY_NAMES.get(name, name)}**](https://github.com/{repo}) | {desc} | {pr_link} | {issue_link} |")

    comm = external.get("community", {})
    repos = comm.get("repos", [])
    shown = [r for r in COMMUNITY_SHOWN if r in repos]
    names = ", ".join(f"[{r.split('/')[-1]}](https://github.com/{r})" for r in shown)
    more = len(repos) - len(shown)
    if more > 0:
        names += f" and {plural(more, 'other repo')}"
    lines.append(
        f"| 🌍 **community** | {names} "
        f"| {comm.get('prs', 0) or '–'} "
        f"| {comm.get('issues', 0) or '–'} |"
    )
    return "\n".join(lines)


def replace_block(text: str, name: str, content: str) -> str:
    """Replace what sits between <!-- name:start --> and <!-- name:end -->."""
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    i, j = text.find(start), text.find(end)
    if i < 0 or j < i:
        raise ValueError(f"README is missing the {start} … {end} markers")
    return text[: i + len(start)] + "\n" + content + "\n" + text[j:]


def main():
    parser = argparse.ArgumentParser(description="Refresh the generated blocks in the profile README.")
    parser.add_argument("--refresh", action="store_true", help="Fetch fresh data from GitHub API")
    parser.add_argument("--root", type=str, default="", help="Project root directory")
    args = parser.parse_args()

    root_dir = Path(args.root) if args.root else Path(__file__).resolve().parent.parent
    stats_file = root_dir / "data" / "github-stats.json"
    readme_file = root_dir / "README.md"

    if args.refresh or not stats_file.exists():
        print("Fetching fresh GitHub statistics...")
        stats = fetch_stats(get_github_token())
        stats_file.parent.mkdir(parents=True, exist_ok=True)
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"Saved stats to {stats_file}")
    else:
        print(f"Reading cached stats from {stats_file}")
        with open(stats_file, "r", encoding="utf-8") as f:
            stats = json.load(f)

    readme = readme_file.read_text(encoding="utf-8")
    readme = replace_block(readme, "stats", render_stats(stats))
    readme = replace_block(readme, "work", render_work(stats))
    readme = replace_block(readme, "oss", render_open_source(stats))
    readme_file.write_text(readme, encoding="utf-8")
    print(f"Updated {readme_file}")


if __name__ == "__main__":
    main()
