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
        "ascii": "#555862",
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
        "ascii": "#908caa",
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


def make_tree_path(x: float, ys: list[float], tick_len: float = 16.0) -> str:
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


def render_svg(stats: dict, ascii_lines: list[str], theme_name: str) -> str:
    """Render a 920x680 SVG profile card matching the minimal.css aesthetic."""
    p = THEMES[theme_name]

    # Stats values
    total_stars = stats.get("total_stars", 0)
    contributions = stats.get("contributions_1y", 0)
    commits_1y = stats.get("commits_1y", 0)
    total_prs = stats.get("total_prs", 0)
    total_issues = stats.get("total_issues", 0)
    repo_stars = stats.get("repo_stars", {})
    external = stats.get("external", {})

    # Language bar calculation (width = 612, x = 266, y = 204, height = 5, rx = 2.5)
    languages = stats.get("languages", [])
    bar_width = 612.0
    bar_segments = []
    if languages:
        total_size = sum(l["size"] for l in languages) or 1
        curr_x = 266.0
        for i, lang in enumerate(languages):
            is_last = (i == len(languages) - 1)
            if is_last:
                seg_w = max(0.0, (266.0 + bar_width) - curr_x)
            else:
                seg_w = round(lang["size"] / total_size * bar_width, 1)
            if seg_w > 0:
                bar_segments.append(
                    f'<rect x="{curr_x:.1f}" y="204" width="{seg_w:.1f}" height="5" fill="{lang["color"]}"/>'
                )
                curr_x += seg_w
    else:
        bar_segments.append(
            f'<rect x="266" y="204" width="612" height="5" fill="{p["section_accent"]}"/>'
        )

    # Sidebar tree items
    nav_ys = [108.0, 128.0, 148.0, 168.0, 188.0, 208.0]
    nav_tree_path = make_tree_path(45.0, nav_ys, tick_len=13.0)

    # Section 2 tree rows
    sec2_ys = [230.0, 252.0, 274.0]
    sec2_tree_path = make_tree_path(266.0, sec2_ys, tick_len=16.0)

    # Section 3 tree rows
    sec3_ys = [342.0, 364.0, 386.0, 408.0, 430.0, 452.0]
    sec3_tree_path = make_tree_path(266.0, sec3_ys, tick_len=16.0)

    # Section 4 tree rows
    sec4_ys = [520.0, 542.0, 564.0, 586.0, 608.0]
    sec4_tree_path = make_tree_path(266.0, sec4_ys, tick_len=16.0)

    # Selected work rows
    selected_work = [
        ("magpie-gemini-web", "Gemini Web & native Argon Task provider for Magpie", "Python · JS", repo_stars.get("magpie-gemini-web", 0)),
        ("trace", "Content-addressed local version tracker for CLI agents", "Python", repo_stars.get("trace", 0)),
        ("hotcorners", "Interactive macOS Hot Corners CLI manager", "Shell", repo_stars.get("hotcorners", 0)),
        ("scrollwm", "niri-style scrollable tiling window manager for macOS", "Swift", repo_stars.get("scrollwm", 0)),
        ("pi-fusion", "Persistent lead/sidekick orchestration for Pi", "TypeScript", repo_stars.get("pi-fusion", 0)),
        ("nixos-config", "Daily NixOS configuration built around flakes", "Nix", repo_stars.get("nixos-config", 0)),
    ]

    # Open source rows
    def fmt_pr_issue(prs: int, issues: int) -> str:
        pr_str = f"{prs} PR" if prs == 1 else f"{prs} PRs"
        if issues <= 0:
            return pr_str
        issue_str = "1 issue" if issues == 1 else f"{issues} issues"
        return f"{pr_str} · {issue_str}"

    cb = external.get("CodexBar", {})
    av = external.get("agentsview", {})
    sr = external.get("School_Running", {})
    bc = external.get("BewlyCat", {})
    comm = external.get("community", {})

    open_source = [
        ("CodexBar", "Grok token history, StepFun credits & Claude/Codex pricing", fmt_pr_issue(cb.get("prs", 5), cb.get("issues", 5))),
        ("agentsview", "StepCode ingestion, Devin dedup & Antigravity effort", fmt_pr_issue(av.get("prs", 4), av.get("issues", 6))),
        ("School_Running", "macOS native console, curve trajectory & DMG release CI", fmt_pr_issue(sr.get("prs", 10), sr.get("issues", 0))),
        ("BewlyCat", "Homepage filter empty-state interaction & fixes", fmt_pr_issue(bc.get("prs", 2), bc.get("issues", 1))),
        ("community", "models.dev · Wake · harness-perf · codex-mcp · pi · magpie", fmt_pr_issue(comm.get("prs", 12), comm.get("issues", 18))),
    ]

    # Format ASCII art lines
    ascii_tspans = []
    for i, line in enumerate(ascii_lines[:28]):
        y_pos = 292.0 + (i * 10.8)
        ascii_tspans.append(
            f'    <tspan x="34" y="{y_pos:.1f}">{html.escape(line)}</tspan>'
        )
    ascii_block = "\n".join(ascii_tspans)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 920 680" width="920" height="680" style="max-width: 100%; height: auto;">
  <defs>
    <style>
      .mono {{ font-family: 'Paper Mono', 'JetBrains Mono', 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; }}
      .serif {{ font-family: 'Paper Latin', 'Songti SC', 'Noto Serif SC', Georgia, serif; }}
      .art {{ font-family: 'JetBrains Mono NF', 'JetBrains Mono', 'SFMono-Regular', Menlo, monospace; }}
      .branch {{ stroke: {p["faint"]}; stroke-width: 1.2; fill: none; stroke-linecap: square; }}
    </style>
    <clipPath id="card-clip">
      <rect width="920" height="680" rx="10"/>
    </clipPath>
    <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
      <path d="M 24 0 L 0 0 0 24" fill="none" stroke="{p["grid"]}" stroke-width="0.6"/>
    </pattern>
    <clipPath id="lang-bar-clip">
      <rect x="266" y="204" width="612" height="5" rx="2.5"/>
    </clipPath>
  </defs>

  <!-- Background Card & Paper Grid -->
  <rect width="920" height="680" rx="10" fill="{p["paper"]}"/>
  <rect width="920" height="680" clip-path="url(#card-clip)" fill="url(#grid)"/>
  <rect x="0.5" y="0.5" width="919" height="679" rx="9.5" fill="none" stroke="{p["border"]}" stroke-width="1"/>

  <!-- Left Sidebar (x = 42) -->
  <g class="mono">
    <text x="42" y="50" font-size="12.5" font-weight="700" letter-spacing="1.2" fill="{p["muted"]}">BUKOWSKIIIII</text>
    <text x="42" y="86" font-size="12" fill="{p["muted"]}">~/</text>

    <!-- Sidebar Tree Navigation -->
    <path class="branch" d="{nav_tree_path}"/>
    <text x="64" y="108" font-size="11.5" fill="{p["muted"]}">home</text>
    <text x="64" y="128" font-size="11.5" fill="{p["muted"]}">cv/</text>
    <text x="64" y="148" font-size="11.5" fill="{p["muted"]}">blog/</text>
    <text x="64" y="168" font-size="11.5" fill="{p["muted"]}">travel/</text>
    <text x="64" y="188" font-size="11.5" fill="{p["muted"]}">status/</text>
    <text x="64" y="208" font-size="11.5" font-weight="700" fill="{p["nav_active"]}">github.url</text>

    <text x="42" y="240" font-size="10.5" fill="{p["faint"]}">site: bukowskiiiiii.uk</text>
    <text x="42" y="258" font-size="10.5" fill="{p["faint"]}">mode: &gt;_ cli / web</text>
  </g>

  <!-- Braille ASCII Art -->
  <text class="art" font-size="9.2" fill="{p["ascii"]}" xml:space="preserve">
{ascii_block}
  </text>

  <!-- Left Sidebar Footer -->
  <g class="mono">
    <text x="42" y="626" font-size="10.5" fill="{p["muted"]}">bukaosiji@outlook.com</text>
    <text x="42" y="644" font-size="10.5" fill="{p["faint"]}">make impact.</text>
  </g>

  <!-- Right Sheet (x = 248 to 878) -->
  <text x="248" y="50" class="mono" font-size="12" fill="{p["muted"]}">~/github</text>
  <text x="248" y="82" class="mono" font-size="24" font-weight="600" fill="{p["ink"]}">bukowskiiiiii</text>
  <text x="878" y="82" class="serif" font-size="12" text-anchor="end" fill="{p["muted"]}">Life is one long regression to the mean.</text>

  <!-- Section 1: activity/ · overview -->
  <text x="248" y="122" class="mono" font-size="12.5" font-weight="500" fill="{p["section_accent"]}">▾ activity/ · overview</text>
  <text x="266" y="148" class="mono" font-size="12">
    <tspan font-weight="600" fill="{p["ink"]}">{total_stars}</tspan><tspan fill="{p["muted"]}"> stars earned   </tspan><tspan font-weight="600" fill="{p["ink"]}">{contributions}</tspan><tspan fill="{p["muted"]}"> contributions (1y)   </tspan><tspan font-weight="600" fill="{p["ink"]}">{total_prs}</tspan><tspan fill="{p["muted"]}"> pull requests   </tspan><tspan font-weight="600" fill="{p["ink"]}">{total_issues}</tspan><tspan fill="{p["muted"]}"> issues   </tspan><tspan font-weight="600" fill="{p["ink"]}">{commits_1y}</tspan><tspan fill="{p["muted"]}"> commits</tspan>
  </text>

  <!-- Section 2: stack/ -->
  <text x="248" y="188" class="mono" font-size="12.5" font-weight="500" fill="{p["section_accent"]}">▾ stack/</text>
  <g clip-path="url(#lang-bar-clip)">
    {''.join(bar_segments)}
  </g>
  <path class="branch" d="{sec2_tree_path}"/>

  <g class="mono" font-size="12" font-weight="500" fill="{p["ink"]}">
    <text x="298" y="230">languages</text>
    <text x="298" y="252">systems</text>
    <text x="298" y="274">focus</text>
  </g>

  <g class="serif" font-size="12" fill="{p["body"]}">
    <text x="438" y="230">{html.escape("Python · TypeScript · Swift · JavaScript · Go")}</text>
    <text x="438" y="252">{html.escape("macOS (Accessibility / Cocoa) · NixOS Flakes · Linux")}</text>
    <text x="438" y="274">{html.escape("Coding Agents · Local-First Tooling · Reverse Engineering")}</text>
  </g>

  <g class="mono" font-size="11" text-anchor="end" fill="{p["muted"]}">
    <text x="878" y="230">{html.escape("Nix · Shell · Typst")}</text>
    <text x="878" y="252">{html.escape("SQLite · Docker")}</text>
    <text x="878" y="274">{html.escape("System-One AI")}</text>
  </g>

  <!-- Section 3: selected-work/ -->
  <text x="248" y="316" class="mono" font-size="12.5" font-weight="500" fill="{p["section_accent"]}">▾ selected-work/</text>
  <path class="branch" d="{sec3_tree_path}"/>

  <g class="mono" font-size="12" font-weight="500" fill="{p["ink"]}">
    <text x="298" y="342">{html.escape(selected_work[0][0])}</text>
    <text x="298" y="364">{html.escape(selected_work[1][0])}</text>
    <text x="298" y="386">{html.escape(selected_work[2][0])}</text>
    <text x="298" y="408">{html.escape(selected_work[3][0])}</text>
    <text x="298" y="430">{html.escape(selected_work[4][0])}</text>
    <text x="298" y="452">{html.escape(selected_work[5][0])}</text>
  </g>

  <g class="serif" font-size="12" fill="{p["body"]}">
    <text x="438" y="342">{html.escape(selected_work[0][1])}</text>
    <text x="438" y="364">{html.escape(selected_work[1][1])}</text>
    <text x="438" y="386">{html.escape(selected_work[2][1])}</text>
    <text x="438" y="408">{html.escape(selected_work[3][1])}</text>
    <text x="438" y="430">{html.escape(selected_work[4][1])}</text>
    <text x="438" y="452">{html.escape(selected_work[5][1])}</text>
  </g>

  <g class="mono" font-size="11" text-anchor="end">
    <text x="878" y="342"><tspan fill="{p["muted"]}">{html.escape(selected_work[0][2])} · </tspan><tspan fill="{p["star_accent"]}">★</tspan><tspan fill="{p["muted"]}"> {selected_work[0][3]}</tspan></text>
    <text x="878" y="364"><tspan fill="{p["muted"]}">{html.escape(selected_work[1][2])} · </tspan><tspan fill="{p["star_accent"]}">★</tspan><tspan fill="{p["muted"]}"> {selected_work[1][3]}</tspan></text>
    <text x="878" y="386"><tspan fill="{p["muted"]}">{html.escape(selected_work[2][2])} · </tspan><tspan fill="{p["star_accent"]}">★</tspan><tspan fill="{p["muted"]}"> {selected_work[2][3]}</tspan></text>
    <text x="878" y="408"><tspan fill="{p["muted"]}">{html.escape(selected_work[3][2])} · </tspan><tspan fill="{p["star_accent"]}">★</tspan><tspan fill="{p["muted"]}"> {selected_work[3][3]}</tspan></text>
    <text x="878" y="430"><tspan fill="{p["muted"]}">{html.escape(selected_work[4][2])} · </tspan><tspan fill="{p["star_accent"]}">★</tspan><tspan fill="{p["muted"]}"> {selected_work[4][3]}</tspan></text>
    <text x="878" y="452"><tspan fill="{p["muted"]}">{html.escape(selected_work[5][2])} · </tspan><tspan fill="{p["star_accent"]}">★</tspan><tspan fill="{p["muted"]}"> {selected_work[5][3]}</tspan></text>
  </g>

  <!-- Section 4: open-source/ -->
  <text x="248" y="494" class="mono" font-size="12.5" font-weight="500" fill="{p["section_accent"]}">▾ open-source/</text>
  <path class="branch" d="{sec4_tree_path}"/>

  <g class="mono" font-size="12" font-weight="500" fill="{p["ink"]}">
    <text x="298" y="520">{html.escape(open_source[0][0])}</text>
    <text x="298" y="542">{html.escape(open_source[1][0])}</text>
    <text x="298" y="564">{html.escape(open_source[2][0])}</text>
    <text x="298" y="586">{html.escape(open_source[3][0])}</text>
    <text x="298" y="608">{html.escape(open_source[4][0])}</text>
  </g>

  <g class="serif" fill="{p["body"]}">
    <text x="438" y="520" font-size="12">{html.escape(open_source[0][1])}</text>
    <text x="438" y="542" font-size="12">{html.escape(open_source[1][1])}</text>
    <text x="438" y="564" font-size="12">{html.escape(open_source[2][1])}</text>
    <text x="438" y="586" font-size="12">{html.escape(open_source[3][1])}</text>
    <text x="438" y="608" font-size="10.8">{html.escape(open_source[4][1])}</text>
  </g>

  <g class="mono" font-size="11" text-anchor="end" fill="{p["muted"]}">
    <text x="878" y="520">{html.escape(open_source[0][2])}</text>
    <text x="878" y="542">{html.escape(open_source[1][2])}</text>
    <text x="878" y="564">{html.escape(open_source[2][2])}</text>
    <text x="878" y="586">{html.escape(open_source[3][2])}</text>
    <text x="878" y="608">{html.escape(open_source[4][2])}</text>
  </g>
</svg>
"""
    return svg


def main():
    parser = argparse.ArgumentParser(description="Generate GitHub profile SVGs.")
    parser.add_argument("--refresh", action="store_true", help="Fetch fresh data from GitHub API")
    parser.add_argument("--root", type=str, default="", help="Project root directory")
    args = parser.parse_args()

    root_dir = Path(args.root) if args.root else Path(__file__).resolve().parent.parent
    data_dir = root_dir / "data"
    assets_dir = root_dir / "assets"
    stats_file = data_dir / "github-stats.json"
    ascii_file = assets_dir / "coding-at-desk.txt"

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

    if not ascii_file.exists():
        raise FileNotFoundError(f"ASCII file not found: {ascii_file}")

    with open(ascii_file, "r", encoding="utf-8") as f:
        ascii_lines = [l.rstrip("\r\n") for l in f]

    # Render light and dark SVGs
    light_svg = render_svg(stats, ascii_lines, "light")
    dark_svg = render_svg(stats, ascii_lines, "dark")

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
