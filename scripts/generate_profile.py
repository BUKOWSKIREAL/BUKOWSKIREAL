#!/usr/bin/env python3
"""
Generate GitHub profile SVGs matching https://bukowskiiiiii.uk/ minimal aesthetic.
"""

import argparse
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import subprocess
import urllib.parse
import urllib.request


THEMES = {
    "light": {
        "paper": "#f8f8f8",
        "grid": "#ececef",
        "border": "#dedee1",
        "hairline": "#d9d9dc",
        "ink": "#2a2b33",
        "body": "#4f515b",
        "muted": "#6a737d",
        "faint": "#959da5",
        "section_accent": "#2f5af3",
        "nav_active": "#2f5af3",
        "star_accent": "#8a5a00",
    },
    "dark": {
        "paper": "#191724",
        "grid": "#211f31",
        "border": "#403d52",
        "hairline": "#403d52",
        "ink": "#e0def4",
        "body": "#c8c5dc",
        "muted": "#908caa",
        "faint": "#6e6a86",
        "section_accent": "#bd93f9",
        "nav_active": "#8be9fd",
        "star_accent": "#f1fa8c",
    },
}

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


def make_tree_path(x: float, ys: list[float], tick_len: float = 14.0) -> str:
    """Generate crisp SVG path for tree branch connectors (vertical trunk + ticks)."""
    if not ys:
        return ""
    step = ys[1] - ys[0] if len(ys) > 1 else 22.0
    yt = ys[0] - 4.2 - (step / 2.0)
    yb = ys[-1] - 4.2
    d = [f"M {x:.1f} {yt:.1f} V {yb:.1f}"]
    for y in ys:
        ym = y - 4.2
        d.append(f"M {x:.1f} {ym:.1f} H {x + tick_len:.1f}")
    return " ".join(d)


# Card size and layout columns
WIDTH = 682
HEIGHT = 584
X_HEAD = 32.0
X_TRUNK = 40.0
X_NAME = 62.0
X_DESC = 202.0
X_RIGHT = 650.0
ROW = 22.0


def render_svg(stats: dict, theme_name: str) -> str:
    """Render the profile card: activity, stack, selected work and open source."""
    p = THEMES[theme_name]
    esc = html.escape

    repo_stars = stats.get("repo_stars", {})
    external = stats.get("external", {})

    def rows(y0: float, n: int) -> list[float]:
        return [y0 + i * ROW for i in range(n)]

    def heading(y: float, label: str) -> str:
        return (
            f'<text x="{X_HEAD:.0f}" y="{y:.0f}" class="mono" font-size="12.5" font-weight="500" '
            f'fill="{p["section_accent"]}">▾ {esc(label)}</text>'
        )

    def tree(ys: list[float]) -> str:
        return f'<path class="branch" d="{make_tree_path(X_TRUNK, ys)}"/>'

    def name_desc(y: float, name: str, desc: str) -> str:
        return (
            f'<text x="{X_NAME:.0f}" y="{y:.0f}" class="mono" font-size="12" font-weight="500" fill="{p["ink"]}">{esc(name)}</text>'
            f'<text x="{X_DESC:.0f}" y="{y:.0f}" class="serif" font-size="12" fill="{p["body"]}">{esc(desc)}</text>'
        )

    def meta(x: float, y: float, text: str, fill: str, anchor: str = "end") -> str:
        return (
            f'<text x="{x:.0f}" y="{y:.0f}" class="mono" font-size="11" text-anchor="{anchor}" '
            f'fill="{fill}">{esc(text)}</text>'
        )

    body = []

    # activity/: five number-over-label cells
    stat_cells = [
        (stats.get("total_stars", 0), "stars"),
        (stats.get("contributions_1y", 0), "contribs · 1y"),
        (stats.get("commits_1y", 0), "commits · 1y"),
        (stats.get("total_prs", 0), "pull requests"),
        (stats.get("total_issues", 0), "issues"),
    ]
    body.append(heading(40, "activity/"))
    cell_w = (X_RIGHT - X_NAME) / len(stat_cells)
    for i, (value, label) in enumerate(stat_cells):
        x = X_NAME + i * cell_w
        body.append(
            f'<text x="{x:.1f}" y="68" class="mono" font-size="19" font-weight="600" fill="{p["ink"]}">{value}</text>'
            f'<text x="{x:.1f}" y="87" class="mono" font-size="10.5" fill="{p["muted"]}">{esc(label)}</text>'
        )

    # stack/: languages come from the data, each with its GitHub color
    languages = [l for l in stats.get("languages", []) if l.get("percentage", 0) >= 1][:4]
    lang_spans = []
    for i, lang in enumerate(languages):
        sep = "  " if i else ""
        lang_spans.append(
            f'<tspan fill="{lang["color"]}">{sep}●</tspan>'
            f'<tspan fill="{p["body"]}"> {esc(lang["name"])}</tspan>'
            f'<tspan fill="{p["faint"]}"> {lang["percentage"]:.0f}%</tspan>'
        )
    stack = [
        ("platforms", "macOS (Accessibility / Cocoa) · NixOS Flakes · Linux"),
        ("tools", "Nix · Shell · Typst · SQLite · Docker"),
        ("focus", "Coding Agents · Local-First Tooling · Reverse Engineering"),
    ]
    stack_ys = rows(154.0, 1 + len(stack))
    body.append(heading(128, "stack/"))
    body.append(tree(stack_ys))
    body.append(
        f'<text x="{X_NAME:.0f}" y="{stack_ys[0]:.0f}" class="mono" font-size="12" font-weight="500" '
        f'fill="{p["ink"]}">languages</text>'
        f'<text x="{X_DESC:.0f}" y="{stack_ys[0]:.0f}" class="mono" font-size="11.5" '
        f'xml:space="preserve">{"".join(lang_spans)}</text>'
    )
    for y, (label, value) in zip(stack_ys[1:], stack):
        body.append(name_desc(y, label, value))

    # selected-work/: language right-aligned, stars in their own column
    selected_work = [
        ("magpie-gemini-web", "Gemini Web & native Argon Task provider for Magpie", "Python · JS"),
        ("trace", "Content-addressed local version tracker for CLI agents", "Python"),
        ("hotcorners", "Interactive macOS Hot Corners CLI manager", "Shell"),
        ("scrollwm", "niri-style scrollable tiling window manager for macOS", "Swift"),
        ("pi-fusion", "Persistent lead/sidekick orchestration for Pi", "TypeScript"),
        ("nixos-config", "Daily NixOS configuration built around flakes", "Nix"),
    ]
    work_ys = rows(288.0, len(selected_work))
    body.append(heading(262, "selected-work/"))
    body.append(tree(work_ys))
    for y, (name, desc, lang) in zip(work_ys, selected_work):
        body.append(
            name_desc(y, name, desc)
            + meta(X_RIGHT - 44, y, lang, p["muted"])
            + meta(X_RIGHT - 28, y, "★", p["star_accent"], "start")
            + meta(X_RIGHT, y, str(repo_stars.get(name, 0)), p["muted"])
        )

    # open-source/: PRs and issues in two aligned columns
    def count(n: int, word: str) -> str:
        if n <= 0:
            return ""
        return f"{n} {word}" if n == 1 else f"{n} {word}s"

    comm = external.get("community", {})
    shown = ["models.dev", "Wake", "pi", "codex"]
    more = max(0, len(comm.get("repos", [])) - len(shown))
    comm_desc = " · ".join(shown) + (f" · +{more} more" if more else "")

    open_source = []
    for name, desc in [
        ("CodexBar", "Grok token history, StepFun credits & Claude/Codex pricing"),
        ("agentsview", "StepCode ingestion, Devin dedup & Antigravity effort"),
        ("School_Running", "macOS native console, curve trajectory & DMG release CI"),
        ("BewlyCat", "Homepage filter empty-state interaction & fixes"),
    ]:
        e = external.get(name, {})
        open_source.append((name, desc, e.get("prs", 0), e.get("issues", 0)))
    open_source.append(("community", comm_desc, comm.get("prs", 0), comm.get("issues", 0)))
    os_ys = rows(464.0, len(open_source))
    body.append(heading(438, "open-source/"))
    body.append(tree(os_ys))
    for y, (name, desc, prs, issues) in zip(os_ys, open_source):
        body.append(
            name_desc(y, name, desc)
            + meta(X_RIGHT - 72, y, count(prs, "PR"), p["muted"])
            + meta(X_RIGHT, y, count(issues, "issue"), p["muted"])
        )

    nl = "\n  "
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" style="max-width: 100%; height: auto;">
  <defs>
    <style>
      .mono {{ font-family: 'Paper Mono', 'JetBrains Mono', ui-monospace, 'SFMono-Regular', Menlo, Consolas, 'Liberation Mono', monospace; }}
      .serif {{ font-family: 'Paper Latin', Charter, 'Iowan Old Style', Georgia, 'Songti SC', 'Noto Serif SC', serif; }}
      .branch {{ stroke: {p["faint"]}; stroke-width: 1.2; fill: none; stroke-linecap: square; }}
    </style>
    <clipPath id="card-clip">
      <rect width="{WIDTH}" height="{HEIGHT}" rx="10"/>
    </clipPath>
    <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
      <path d="M 24 0 L 0 0 0 24" fill="none" stroke="{p["grid"]}" stroke-width="0.6"/>
    </pattern>
  </defs>

  <rect width="{WIDTH}" height="{HEIGHT}" rx="10" fill="{p["paper"]}"/>
  <rect width="{WIDTH}" height="{HEIGHT}" clip-path="url(#card-clip)" fill="url(#grid)"/>
  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="9.5" fill="none" stroke="{p["border"]}" stroke-width="1"/>

  {nl.join(body)}
</svg>
"""


def main():
    parser = argparse.ArgumentParser(description="Generate GitHub profile SVGs.")
    parser.add_argument("--refresh", action="store_true", help="Fetch fresh data from GitHub API")
    parser.add_argument("--root", type=str, default="", help="Project root directory")
    args = parser.parse_args()

    root_dir = Path(args.root) if args.root else Path(__file__).resolve().parent.parent
    data_dir = root_dir / "data"
    assets_dir = root_dir / "assets"
    stats_file = data_dir / "github-stats.json"

    data_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    token = get_github_token()

    if args.refresh or not stats_file.exists():
        print("Fetching fresh GitHub statistics...")
        stats = fetch_stats(token)
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"Saved stats to {stats_file}")
    else:
        print(f"Reading cached stats from {stats_file}")
        with open(stats_file, "r", encoding="utf-8") as f:
            stats = json.load(f)

    # Render light and dark SVGs
    light_svg = render_svg(stats, "light")
    dark_svg = render_svg(stats, "dark")

    light_path = assets_dir / "profile-light.svg"
    dark_path = assets_dir / "profile-dark.svg"

    with open(light_path, "w", encoding="utf-8") as f:
        f.write(light_svg)
    print(f"Generated {light_path}")

    with open(dark_path, "w", encoding="utf-8") as f:
        f.write(dark_svg)
    print(f"Generated {dark_path}")


if __name__ == "__main__":
    main()
