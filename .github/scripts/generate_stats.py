#!/usr/bin/env python3
import os
import requests
from datetime import datetime, timezone

TOKEN = os.environ['GITHUB_TOKEN']
USERNAME = os.environ.get('GITHUB_USERNAME', 'truongk23k')
HEADERS = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

# Languages to exclude from the chart (build outputs, markup, etc.)
EXCLUDE_LANGS = {'HTML', 'CSS'}

# Tokyo Night theme
BG = '#1a1b27'
BORDER = '#414868'
TITLE = '#70a5fd'
TEXT = '#a9b1d6'
VALUE = '#e4e9f1'
ICON = '#38bdae'


def gql(query, variables=None):
    r = requests.post(
        'https://api.github.com/graphql',
        json={'query': query, 'variables': variables or {}},
        headers=HEADERS, timeout=30
    )
    r.raise_for_status()
    d = r.json()
    if 'errors' in d:
        print('GraphQL errors:', d['errors'])
    return d.get('data', {})


def get_user_info():
    q = '''query($login: String!) {
      user(login: $login) {
        createdAt
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
          nodes {
            stargazerCount
            forkCount
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node { name color }
              }
            }
          }
        }
        pullRequests { totalCount }
        issues { totalCount }
      }
    }'''
    return gql(q, {'login': USERNAME}).get('user', {})


def get_commits_for_year(year):
    now = datetime.now(timezone.utc)
    from_dt = f"{year}-01-01T00:00:00Z"
    to_dt = f"{year}-12-31T23:59:59Z" if year < now.year else now.strftime('%Y-%m-%dT%H:%M:%SZ')
    q = '''query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          restrictedContributionsCount
        }
      }
    }'''
    data = gql(q, {'login': USERNAME, 'from': from_dt, 'to': to_dt})
    col = data.get('user', {}).get('contributionsCollection', {})
    return col.get('totalCommitContributions', 0) + col.get('restrictedContributionsCount', 0)


def get_total_commits(created_year):
    current_year = datetime.now(timezone.utc).year
    total = 0
    for year in range(created_year, current_year + 1):
        commits = get_commits_for_year(year)
        print(f"  {year}: {commits} commits")
        total += commits
    return total


def calculate_rank(stars, commits, prs, issues, repos):
    score = stars * 4 + commits * 2 + prs * 3 + issues * 1 + repos * 1
    thresholds = [('S', 2000), ('A+', 1000), ('A', 500), ('B+', 200), ('B', 100), ('C+', 50)]
    for rank, threshold in thresholds:
        if score >= threshold:
            return rank
    return 'C'


RANK_COLORS = {
    'S': '#e9c46a', 'A+': '#2dd4bf', 'A': '#4ade80',
    'B+': '#60a5fa', 'B': '#a78bfa', 'C+': '#f472b6', 'C': '#9ca3af'
}


def generate_stats_svg(stars, commits, prs, issues, repos, rank):
    rank_color = RANK_COLORS.get(rank, '#9ca3af')
    stats = [
        ('⭐', 'Total Stars Earned:', f'{stars:,}'),
        ('🔨', 'Total Commits (all time):', f'{commits:,}'),
        ('🔀', 'Total PRs:', f'{prs:,}'),
        ('🐛', 'Total Issues:', f'{issues:,}'),
        ('📦', 'Public Repos:', f'{repos:,}'),
    ]

    rows = ''
    for i, (icon, label, value) in enumerate(stats):
        y = 63 + i * 26
        rows += f'  <text x="30" y="{y}" class="label">{icon} {label}</text>\n'
        rows += f'  <text x="225" y="{y}" class="value">{value}</text>\n'

    updated = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    return f'''<svg width="495" height="195" viewBox="0 0 495 195" xmlns="http://www.w3.org/2000/svg">
  <style>
    .title {{ font: 600 17px "Segoe UI", Ubuntu, sans-serif; fill: {TITLE}; }}
    .label {{ font: 400 13px "Segoe UI", Ubuntu, sans-serif; fill: {TEXT}; }}
    .value {{ font: 600 13px "Segoe UI", Ubuntu, sans-serif; fill: {VALUE}; }}
    .rank  {{ font: 800 28px "Segoe UI", Ubuntu, sans-serif; fill: {rank_color}; }}
    .rlbl  {{ font: 600 12px "Segoe UI", Ubuntu, sans-serif; fill: {TEXT}; }}
    .note  {{ font: 400 10px "Segoe UI", Ubuntu, sans-serif; fill: {BORDER}; }}
  </style>
  <rect x="0.5" y="0.5" width="494" height="194" rx="4.5" fill="{BG}" stroke="{BORDER}"/>
  <text x="25" y="35" class="title">{USERNAME}'s GitHub Stats</text>
{rows}
  <g transform="translate(390,100)">
    <circle r="42" fill="none" stroke="{BORDER}" stroke-width="6"/>
    <circle r="42" fill="none" stroke="{rank_color}" stroke-width="6"
            stroke-dasharray="263.9" stroke-dashoffset="66"
            transform="rotate(-90)" opacity="0.9"/>
    <text x="0" y="10" text-anchor="middle" class="rank">{rank}</text>
    <text x="0" y="58" text-anchor="middle" class="rlbl">Rank</text>
  </g>
  <text x="10" y="188" class="note">Updated: {updated}</text>
</svg>'''


def generate_langs_svg(lang_totals):
    if not lang_totals:
        return ''
    sorted_langs = sorted(lang_totals.items(), key=lambda x: x[1]['size'], reverse=True)[:8]
    total = sum(v['size'] for _, v in sorted_langs)
    if total == 0:
        return ''

    lang_data = [(name, info['size'] / total * 100, info.get('color') or '#858585')
                 for name, info in sorted_langs]

    height = 60 + 22 + len(lang_data) * 22 + 20
    bar_y = 48

    # Stacked progress bar
    bar_segments = ''
    x = 20.0
    for i, (name, pct, color) in enumerate(lang_data):
        w = pct / 100 * 260
        rx = '4' if i == 0 else ('4' if i == len(lang_data) - 1 else '0')
        bar_segments += f'  <rect x="{x:.1f}" y="{bar_y}" width="{max(w,0.5):.1f}" height="8" fill="{color}"/>\n'
        x += w

    rows = ''
    for i, (name, pct, color) in enumerate(lang_data):
        y = 78 + i * 22
        rows += f'  <circle cx="30" cy="{y-3}" r="5" fill="{color}"/>\n'
        rows += f'  <text x="42" y="{y}" class="label">{name}</text>\n'
        rows += f'  <text x="285" y="{y}" text-anchor="end" class="pct">{pct:.1f}%</text>\n'

    updated = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    return f'''<svg width="300" height="{height}" viewBox="0 0 300 {height}" xmlns="http://www.w3.org/2000/svg">
  <style>
    .title {{ font: 600 17px "Segoe UI", Ubuntu, sans-serif; fill: {TITLE}; }}
    .label {{ font: 400 11px "Segoe UI", Ubuntu, sans-serif; fill: {TEXT}; }}
    .pct   {{ font: 600 11px "Segoe UI", Ubuntu, sans-serif; fill: {VALUE}; }}
    .note  {{ font: 400 10px "Segoe UI", Ubuntu, sans-serif; fill: {BORDER}; }}
  </style>
  <rect x="0.5" y="0.5" width="299" height="{height-1}" rx="4.5" fill="{BG}" stroke="{BORDER}"/>
  <text x="25" y="35" class="title">Most Used Languages</text>
  <rect x="20" y="{bar_y}" width="260" height="8" rx="4" fill="{BORDER}"/>
{bar_segments}{rows}
  <text x="10" y="{height-5}" class="note">Updated: {updated}</text>
</svg>'''


def main():
    print(f"Fetching GitHub stats for {USERNAME}...")
    user = get_user_info()
    if not user:
        print("ERROR: Could not fetch user info")
        return

    created_year = int(user.get('createdAt', '2020-01-01T00:00:00Z')[:4])
    repos = user.get('repositories', {}).get('nodes', [])

    total_stars = sum(r.get('stargazerCount', 0) for r in repos)
    total_prs = user.get('pullRequests', {}).get('totalCount', 0)
    total_issues = user.get('issues', {}).get('totalCount', 0)
    repo_count = len(repos)

    # Aggregate languages across all repos (excluding build outputs / markup)
    lang_totals = {}
    for repo in repos:
        for edge in repo.get('languages', {}).get('edges', []):
            name = edge['node']['name']
            if name in EXCLUDE_LANGS:
                continue
            color = edge['node'].get('color') or '#858585'
            size = edge.get('size', 0)
            if name not in lang_totals:
                lang_totals[name] = {'size': 0, 'color': color}
            lang_totals[name]['size'] += size

    print(f"Getting commits from {created_year} to present...")
    total_commits = get_total_commits(created_year)

    rank = calculate_rank(total_stars, total_commits, total_prs, total_issues, repo_count)
    print(f"Stars={total_stars} Commits={total_commits} PRs={total_prs} Issues={total_issues} Rank={rank}")

    with open('github-stats.svg', 'w', encoding='utf-8') as f:
        f.write(generate_stats_svg(total_stars, total_commits, total_prs, total_issues, repo_count, rank))
    print("Written github-stats.svg")

    langs_svg = generate_langs_svg(lang_totals)
    if langs_svg:
        with open('top-langs.svg', 'w', encoding='utf-8') as f:
            f.write(langs_svg)
        print("Written top-langs.svg")


if __name__ == '__main__':
    main()
