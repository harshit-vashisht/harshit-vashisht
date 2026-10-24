"""Collect public GitHub statistics and regenerate the themed profile cards."""
from __future__ import annotations
import argparse
from html import escape
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
LOGIN = 'harshit-vashisht'
STACK = ['React', 'TypeScript', 'Vite', 'GSAP', 'Python', 'HTML / CSS', 'GitHub Actions']
ACCOUNT = '''query($login:String!){user(login:$login){id login followers{totalCount}}}'''
REPOSITORIES = '''query($login:String!,$cursor:String){user(login:$login){repositories(first:100,after:$cursor,privacy:PUBLIC,ownerAffiliations:[OWNER]){nodes{id nameWithOwner isFork isPrivate stargazerCount defaultBranchRef{target{... on Commit{oid}}}}pageInfo{hasNextPage endCursor}}}}'''
HISTORY = '''query($owner:String!,$name:String!,$head:GitObjectID!,$author:ID!,$cursor:String){repository(owner:$owner,name:$name){object(oid:$head){... on Commit{history(first:100,after:$cursor,author:{id:$author}){nodes{oid additions deletions authoredDate}pageInfo{hasNextPage endCursor}}}}}}'''
LANGUAGES = '''query($owner:String!,$name:String!,$cursor:String){repository(owner:$owner,name:$name){languages(first:100,after:$cursor,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}pageInfo{hasNextPage endCursor}}}}'''

class StatsError(RuntimeError):
    pass

class GitHub:
    def __init__(self):
        self.calls = 0

    def query(self, query, variables):
        for attempt in range(3):
            self.calls += 1
            try:
                result = subprocess.run(['gh', 'api', 'graphql', '--input', '-'],
                    input=json.dumps({'query': query, 'variables': variables}),
                    capture_output=True, text=True, timeout=70, check=False)
            except subprocess.TimeoutExpired:
                if attempt == 2:
                    raise StatsError('GitHub request timed out after three attempts') from None
                time.sleep(2 ** attempt)
                continue
            try:
                payload = json.loads(result.stdout)
            except ValueError:
                payload = {}
            errors = payload.get('errors')
            if result.returncode == 0 and not errors and isinstance(payload.get('data'), dict):
                return payload['data']
            if attempt == 2:
                raise StatsError('GitHub query failed; verify gh authentication, API availability and rate limit. Existing cards were not replaced.')
            time.sleep(2 ** attempt)
        raise StatsError('GitHub query failed')


def pages(fetch):
    cursor, seen = None, set()
    while True:
        connection = fetch(cursor)
        if not isinstance(connection, dict):
            raise StatsError('GitHub resource disappeared while collecting statistics')
        yield connection
        info = connection['pageInfo']
        if not info['hasNextPage']:
            break
        cursor = info['endCursor']
        if not cursor or cursor in seen:
            raise StatsError('GitHub returned an invalid or repeated pagination cursor')
        seen.add(cursor)


def owned_public_repositories(client, login):
    result = []
    def fetch(cursor):
        user = client.query(REPOSITORIES, {'login': login, 'cursor': cursor})['user']
        if user is None:
            raise StatsError('GitHub account not found')
        return user['repositories']
    for page in pages(fetch):
        for repo in page['nodes']:
            if not repo['isPrivate'] and repo['nameWithOwner'].split('/')[0].casefold() == login.casefold():
                result.append(repo)
    return result


def history(client, repo, author):
    branch = repo['defaultBranchRef']
    if branch is None:
        return []
    owner, name = repo['nameWithOwner'].split('/')
    variables = {'owner': owner, 'name': name, 'head': branch['target']['oid'], 'author': author}
    def fetch(cursor):
        data = client.query(HISTORY, {**variables, 'cursor': cursor})['repository']
        if not data or not data['object']:
            raise StatsError('Repository head became unavailable; retry instead of publishing incomplete totals')
        return data['object']['history']
    return [commit for page in pages(fetch) for commit in page['nodes']]


def language_bytes(client, repo):
    owner, name = repo['nameWithOwner'].split('/')
    def fetch(cursor):
        data = client.query(LANGUAGES, {'owner': owner, 'name': name, 'cursor': cursor})['repository']
        if data is None:
            raise StatsError('Repository became unavailable while collecting languages')
        return data['languages']
    return [{'name': edge['node']['name'], 'color': edge['node']['color'] or '#8a957e', 'bytes': edge['size']}
            for page in pages(fetch) for edge in page['edges']]


def parse_date(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def cache_valid(entry, head):
    if not isinstance(entry, dict) or entry.get('head') != head or not isinstance(entry.get('commits'), list):
        return False
    seen = set()
    for commit in entry['commits']:
        if not isinstance(commit, dict) or not re.fullmatch(r'[a-f0-9]{40,64}', str(commit.get('oid', ''))):
            return False
        if commit['oid'] in seen:
            return False
        seen.add(commit['oid'])
        if any(type(commit.get(field)) is not int or commit[field] < 0 for field in ('additions', 'deletions')):
            return False
        try:
            parse_date(commit['authoredDate'])
        except (KeyError, ValueError, TypeError, AttributeError):
            return False
    return True


def load_cache(path, author):
    try:
        data = json.loads(path.read_text())
        if data.get('schema') == 1 and data.get('author') == author and isinstance(data.get('repositories'), dict):
            return data['repositories']
    except (OSError, ValueError, AttributeError):
        pass
    return {}


def collect(client, cache_path, now=None, refresh=False):
    now = now or datetime.now(timezone.utc)
    account = client.query(ACCOUNT, {'login': LOGIN})['user']
    if not account:
        raise StatsError('GitHub account not found')
    repositories = owned_public_repositories(client, LOGIN)
    old = {} if refresh else load_cache(cache_path, account['id'])
    entries, commits, languages, colors = {}, {}, Counter(), {}
    scanned = 0
    for repo in repositories:
        if repo['isFork'] or repo['nameWithOwner'].casefold() == f'{LOGIN}/{LOGIN}'.casefold():
            continue
        scanned += 1
        head = repo['defaultBranchRef']['target']['oid'] if repo['defaultBranchRef'] else None
        entry = old.get(repo['id'])
        if not cache_valid(entry, head):
            entry = {'head': head, 'commits': history(client, repo, account['id'])}
        if not cache_valid(entry, head):
            raise StatsError('Invalid commit data; refusing to replace existing cards')
        entries[repo['id']] = entry
        for commit in entry['commits']:
            commits[commit['oid']] = commit
        for language in language_bytes(client, repo):
            languages[language['name']] += language['bytes']
            colors[language['name']] = language['color']
    month_number = now.year * 12 + now.month - 1
    months = [f'{n // 12:04d}-{n % 12 + 1:02d}' for n in range(month_number - 11, month_number + 1)]
    monthly, active = Counter(), set()
    for commit in commits.values():
        date = parse_date(commit['authoredDate'])
        if date <= now:
            monthly[date.strftime('%Y-%m')] += 1
            if date.date() >= (now.date() - timedelta(days=364)):
                active.add(date.date())
    stats = {'login': LOGIN, 'updated_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'public_repos': len(repositories), 'stars': sum(repo['stargazerCount'] for repo in repositories),
        'followers': account['followers']['totalCount'], 'scanned_repositories': scanned,
        'commits': len(commits), 'additions': sum(c['additions'] for c in commits.values()),
        'deletions': sum(c['deletions'] for c in commits.values()), 'active_days': len(active),
        'activity': [{'month': month, 'commits': monthly[month]} for month in months],
        'languages': [{'name': name, 'bytes': size, 'color': colors[name]} for name, size in sorted(languages.items(), key=lambda pair: (-pair[1], pair[0]))],
        'stack': STACK,
        'scope': 'Authored commit diffs in owned public non-fork repositories on default branches; profile repository excluded. Diff lines are cumulative changes, not unique current lines of code. Language sizes are repository bytes, not time spent.'}
    return stats, {'schema': 1, 'author': account['id'], 'repositories': entries}


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def readme(stats):
    version = stats['updated_at'].replace('-', '').replace(':', '')
    base = f'https://raw.githubusercontent.com/{LOGIN}/{LOGIN}/main/'
    alt = escape(f"{LOGIN} — A mind, under construction. {stats['public_repos']} public repositories, {stats['commits']} authored commits, {stats['additions']:,} lines added and {stats['deletions']:,} removed. React, TypeScript, Vite, GSAP, Python, HTML and CSS, GitHub Actions.", quote=True)
    return f"""<a href="https://harshit-vashisht.github.io/">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="{base}dark_mode.svg?v={version}">
    <source media="(prefers-color-scheme: light)" srcset="{base}light_mode.svg?v={version}">
    <img src="{base}light_mode.svg?v={version}" alt="{alt}" width="1100">
  </picture>
</a>

[Enter the workbench](https://harshit-vashisht.github.io/) · [Light SVG](./light_mode.svg) · [Dark SVG](./dark_mode.svg)

<details>
<summary>Behind the numbers</summary>

**{stats['public_repos']} public repositories · {stats['commits']} authored commits · +{stats['additions']:,} / −{stats['deletions']:,} lines**

Code totals and monthly activity cover authored commits in owned, public, non-fork repositories on their default branches. This profile repository is excluded so automatic updates never inflate the totals. Lines added/removed are cumulative commit diffs, not unique current lines of code or a count of push events. GitHub-linked authorship is used; private repositories and unlinked commit emails are not included. Languages are measured in repository bytes, not time spent.

The stack lists tools used in the portfolio. Generated from GitHub's API, refreshed daily by [GitHub Actions](https://github.com/{LOGIN}/{LOGIN}/actions/workflows/profile.yml). Last successful update: **{stats['updated_at']}**.

</details>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--collect-only', action='store_true')
    args = parser.parse_args()
    client = GitHub()
    stats, cache = collect(client, ROOT / 'cache/commits.json', refresh=args.refresh)
    outputs = {}
    if not args.collect_only:
        from render_card import render_card
        for theme in ('dark', 'light'):
            svg = render_card(stats, theme)
            root = ET.fromstring(svg)
            if root.tag != '{http://www.w3.org/2000/svg}svg':
                raise StatsError('Invalid SVG root')
            outputs[ROOT / f'{theme}_mode.svg'] = svg
    if not args.collect_only:
        outputs[ROOT / 'README.md'] = readme(stats)
    outputs[ROOT / 'data/stats.json'] = json.dumps(stats, indent=2) + '\n'
    outputs[ROOT / 'cache/commits.json'] = json.dumps(cache, indent=2, sort_keys=True) + '\n'
    for path, value in outputs.items():
        atomic_write(path, value)
    print(f'Updated {stats["public_repos"]} public repositories, {stats["commits"]} authored commits, +{stats["additions"]:,} / -{stats["deletions"]:,} lines. API calls: {client.calls}')

if __name__ == '__main__':
    try:
        main()
    except (StatsError, OSError, ValueError) as error:
        raise SystemExit(f'Profile update failed: {error}') from None
