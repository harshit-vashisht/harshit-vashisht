"""Render self-contained workbench profile cards without browser dependencies."""
from __future__ import annotations

from datetime import datetime
from html import escape
import re


def _number(value: object) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError, OverflowError):
        return 0


def _compact(value: object) -> str:
    number = _number(value)
    if number < 100_000:
        return f"{number:,}"
    for unit, divisor in (("T", 10**12), ("B", 10**9), ("M", 10**6), ("K", 10**3)):
        if number >= divisor:
            return f"{number / divisor:.1f}".rstrip("0").rstrip(".") + unit
    return str(number)


def _short(value: object, length: int = 28) -> str:
    text = str(value)
    return text if len(text) <= length else text[: length - 1] + "…"


def render_card(stats: dict, theme: str) -> str:
    """Return one SVG card. `theme` must be `light` or `dark`."""
    if theme not in ("light", "dark"):
        raise ValueError("theme must be light or dark")
    dark = theme == "dark"
    p = {
        "paper": "#171d19" if dark else "#f2f0e7",
        "ink": "#f2f0e7" if dark else "#282d26",
        "muted": "#b5bcae" if dark else "#626859",
        "line": "#3c473c" if dark else "#c7cbbc",
        "panel": "#202922" if dark else "#e8eadf",
        "accent": "#ff8059" if dark else "#b93f23",
        "orange": "#ff7449" if dark else "#ef502d",
        "sage": "#d5dfbd" if dark else "#536b3d",
        "wheel": "#d5dfbd" if dark else "#282d26",
        "wheel_inside": "#303b2b" if dark else "#d5dfbd",
    }
    e = lambda value: escape(str(value), quote=True)
    login = str(stats.get("login", "harshit-vashisht"))
    timestamp = str(stats.get("updated_at", ""))
    try:
        updated = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime("%d %b %Y").upper()
    except ValueError:
        updated = "NOT YET UPDATED"
    additions = _number(stats.get("additions"))
    deletions = _number(stats.get("deletions"))
    commits = _number(stats.get("commits"))
    active = _number(stats.get("active_days"))
    scanned = _number(stats.get("scanned_repositories"))
    lines_total = additions + deletions
    addition_width = 1004 * additions / lines_total if lines_total else 0
    full_description = (
        f"{login}. A mind, under construction. "
        f"{_number(stats.get('public_repos')):,} public repositories, "
        f"{commits:,} authored commits, {_number(stats.get('stars')):,} stars, "
        f"{_number(stats.get('followers')):,} followers. "
        f"{additions:,} lines added and {deletions:,} lines removed in authored commit diffs. "
        f"{active:,} active days in the last 365 days. "
        "Code and activity cover owned public non-fork repositories on default branches, excluding this profile repository. "
        "Diff line counts are not unique lines of code or push events. "
        f"Created by atulhacks for harshit-vashisht. Updated {updated}."
    )
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="1050" viewBox="0 0 1100 1050" role="img" aria-labelledby="card-title card-description" data-theme="{theme}" data-motion="workbench-v1">
<title id="card-title">{e(login)} — A mind, under construction.</title>
<desc id="card-description">{e(full_description)}</desc>
<defs>
  <pattern id="bench-dots" width="16" height="16" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".8" fill="{p['line']}"/></pattern>
  <clipPath id="activity-clip"><rect x="48" y="857" width="1004" height="100"/></clipPath>
</defs>
<style>
  text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: {p['ink']}; }}
  .mono {{ font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', monospace; }}
  .muted {{ fill: {p['muted']}; }}
  .accent {{ fill: {p['accent']}; }}
  .rule {{ stroke: {p['line']}; stroke-width: 1; }}
  .wheel-spin {{ transform-box: fill-box; transform-origin: center; animation: turn 48s linear infinite; }}
  .wheel-counter {{ transform-box: fill-box; transform-origin: center; animation: turn 72s linear infinite reverse; }}
  .signal {{ animation: signal 4s ease-in-out infinite; }}
  @keyframes turn {{ to {{ transform: rotate(360deg); }} }}
  @keyframes signal {{ 50% {{ opacity: .45; }} }}
  @media (prefers-reduced-motion: reduce) {{ .wheel-spin, .wheel-counter, .signal {{ animation: none; }} }}
</style>
<rect width="1100" height="1050" rx="14" fill="{p['paper']}"/>
<rect x=".5" y=".5" width="1099" height="1049" rx="14" fill="none" stroke="{p['line']}"/>
<path d="M48 25v24m19-24v24M48 37h19" fill="none" stroke="{p['ink']}" stroke-width="4"/>
<path d="m54 29 8 15" stroke="{p['orange']}" stroke-width="4"/>
<text x="83" y="44" font-size="21" font-weight="600">{e(_short(login, 34))}</text>
<text x="1052" y="43" class="mono muted" font-size="13" text-anchor="end" letter-spacing="1.3">A PERSONAL WORKBENCH / 001</text>
<path d="M48 69H1052" class="rule"/>
<text x="48" y="128" class="mono muted" font-size="13" letter-spacing="2">PART DEVELOPER. PART UNFINISHED THOUGHT.</text>
<text x="44" y="209" font-size="72" font-weight="500" letter-spacing="-4.4">A mind, under</text>
<text x="44" y="282" font-size="72" font-weight="500" letter-spacing="-4.4" fill="{p['orange']}" style="fill:{p['orange']}">construction.</text>
<text x="48" y="325" font-size="18" class="muted">Interfaces. Experiments. The decisions underneath.</text>
<g aria-hidden="true">
<rect x="744" y="88" width="308" height="246" fill="url(#bench-dots)" opacity=".6"/>
<path d="M718 211h344M881 84v248" class="rule" stroke-dasharray="3 7"/>
<circle cx="881" cy="211" r="119" fill="none" stroke="{p['line']}" stroke-dasharray="2 7"/>
<path d="M745 343h281m-281-5v10m281-10v10" class="rule"/>
<g transform="translate(881 211)">
<circle r="93" fill="{p['wheel']}"/>
<circle r="81" fill="none" stroke="{p['wheel_inside']}"/>
<g class="wheel-spin">''']
    for i in range(12):
        parts.append(f'<g transform="rotate({i * 30})"><path d="M-4-73h8v32h-8z" fill="{p["wheel_inside"]}"/><circle cy="-65" r="1.5" fill="{p["paper"]}"/></g>')
    parts.append(f'''</g><circle r="33" fill="{p['wheel_inside']}"/><circle r="21" fill="{p['orange']}"/><circle r="8" fill="{p['paper']}"/>
<g class="wheel-counter"><circle r="108" fill="none" stroke="{p['orange']}" stroke-width="9"/><path d="M-13-123h26v19h-26z" fill="{p['orange']}"/></g>
</g>
<path d="M881 211C1015 211 956 314 1040 300" fill="none" stroke="{p['orange']}" stroke-width="1.7"/>
<circle cx="1040" cy="300" r="5" fill="{p['orange']}" class="signal"/>
</g>
<path d="M48 365H1052" class="rule"/>
''')
    metrics = [("PUBLIC REPOSITORIES", stats.get("public_repos")), ("AUTHORED COMMITS", commits), ("STARS RECEIVED", stats.get("stars")), ("FOLLOWERS", stats.get("followers"))]
    for index, (label, value) in enumerate(metrics):
        x = 48 + index * 256
        if index:
            parts.append(f'<path d="M{x - 26} 390v68" class="rule"/>')
        parts.append(f'<g><title>{e(label.title())}: {_number(value):,}</title><text x="{x}" y="401" class="mono muted" font-size="13" letter-spacing=".7">{label}</text><text x="{x - 2}" y="455" font-size="46" letter-spacing="-1.5" font-weight="500">{_compact(value)}</text></g>')
    parts.append(f'''<path d="M48 481H1052" class="rule"/>
<text x="48" y="517" class="mono muted" font-size="13" letter-spacing="1.2">01 / THE CODE LEFT BEHIND</text>
<g><title>{additions:,} lines added across authored commit diffs</title><text x="46" y="576" font-size="48" letter-spacing="-1.8" style="fill:{p['sage']}">+{_compact(additions)}</text><text x="305" y="571" font-size="17" class="muted">lines added</text></g>
<g><title>{deletions:,} lines removed across authored commit diffs</title><text x="590" y="576" font-size="48" letter-spacing="-1.8" class="accent">−{_compact(deletions)}</text><text x="850" y="571" font-size="17" class="muted">lines removed</text></g>
<rect x="48" y="596" width="1004" height="4" fill="{p['line']}"/>
''')
    if lines_total:
        parts.append(f'<rect x="48" y="596" width="{addition_width:.3f}" height="4" fill="{p["sage"]}"/><rect x="{48 + addition_width:.3f}" y="596" width="{1004-addition_width:.3f}" height="4" fill="{p["orange"]}"/>')
    parts.append(f'''<text x="48" y="624" class="muted" font-size="14">Lifetime authored diff lines · not unique lines of code · {scanned:,} repositories scanned</text>
<text x="48" y="674" class="mono muted" font-size="13" letter-spacing="1.2">02 / TOOLS ON THE BENCH</text>
<text x="601" y="674" class="mono muted" font-size="13" letter-spacing="1.2">03 / LANGUAGE MIX · BYTES</text>
<path d="M564 655v135" class="rule"/>
''')
    stack = [str(s) for s in stats.get("stack", [])][:9]
    if not stack:
        stack = ["Still finding the next tool."]
    x, y = 48, 691
    for name in stack:
        label = _short(name, 22)
        width = min(455, 30 + len(label) * 9)
        if x + width > 535:
            x, y = 48, y + 37
        if y > 765:
            break
        parts.append(f'<g><title>{e(name)}</title><rect x="{x}" y="{y}" width="{width}" height="29" rx="3" fill="{p["panel"]}" stroke="{p["line"]}"/><text x="{x + 14}" y="{y + 20}" class="mono" font-size="14">{e(label)}</text></g>')
        x += width + 8
    raw_languages = stats.get("languages", [])
    languages = [item for item in raw_languages if _number(item.get("bytes")) > 0]
    languages.sort(key=lambda item: (-_number(item.get("bytes")), str(item.get("name", ""))))
    total_bytes = sum(_number(item.get("bytes")) for item in languages)
    displayed = list(languages[:2])
    if len(languages) > 2:
        displayed.append({"name": "Other", "bytes": sum(_number(item.get("bytes")) for item in languages[2:]), "color": p["muted"]})
    if len(languages) == 2:
        displayed = languages
    if not languages:
        parts.append(f'<text x="601" y="719" font-size="17" class="muted">No language data available yet.</text>')
    else:
        offset = 601.0
        for index, item in enumerate(displayed):
            name, byte_count = str(item.get("name", "Unknown")), _number(item.get("bytes"))
            color = str(item.get("color", ""))
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
                color = p["sage"]
            width = 451 * byte_count / total_bytes
            percentage = 100 * byte_count / total_bytes
            parts.append(f'<rect x="{offset:.3f}" y="695" width="{width:.3f}" height="6" fill="{color}"/>')
            offset += width
            row_y = 728 + index * 25
            parts.append(f'<g><title>{e(name)}: {byte_count:,} bytes ({percentage:.2f}%)</title><circle cx="606" cy="{row_y - 5}" r="4" fill="{color}"/><text x="622" y="{row_y}" font-size="16">{e(_short(name, 28))}</text><text x="1052" y="{row_y}" class="mono muted" font-size="14" text-anchor="end">{percentage:.1f}%</text></g>')
    activity = list(stats.get("activity", []))[-12:]
    largest = max((_number(item.get("commits")) for item in activity), default=0)
    parts.append(f'''<path d="M48 808H1052" class="rule"/>
<text x="48" y="842" class="mono muted" font-size="13" letter-spacing="1.2">04 / A YEAR OF SMALL DECISIONS</text>
<text x="1052" y="842" class="mono muted" font-size="13" text-anchor="end">{active:,} ACTIVE DAYS / LAST 365 DAYS</text>
<path d="M48 884H1052M48 920H1052M48 956H1052" class="rule" stroke-dasharray="2 6"/>
''')
    if activity:
        slot = 1004 / len(activity)
        for i, item in enumerate(activity):
            value = _number(item.get("commits"))
            height = value / largest * 72 if largest else 0
            x = 48 + i * slot + 8
            month = str(item.get("month", ""))
            try:
                label = datetime.strptime(month, "%Y-%m").strftime("%b").upper()
            except ValueError:
                label = _short(month, 4).upper()
            parts.append(f'<g><title>{e(month)}: {value:,} authored commits</title><rect x="{x:.3f}" y="{956-max(height, 2):.3f}" width="{max(1, slot - 16):.3f}" height="{max(height, 2):.3f}" rx="2" fill="{p["orange"] if i == len(activity)-1 else p["sage"]}" opacity="{1 if value else .2}"/><text x="{x+ (slot-16)/2:.3f}" y="{max(876, 946-height):.3f}" class="mono muted" font-size="12" text-anchor="middle">{_compact(value) if value else ''}</text><text x="{x+(slot-16)/2:.3f}" y="977" class="mono muted" font-size="12" text-anchor="middle">{e(label)}</text></g>')
    else:
        parts.append('<text x="48" y="921" font-size="17" class="muted">The next commit starts a new mark.</text>')
    parts.append(f'''<text x="48" y="1009" font-size="13" class="muted">Public, owned, non-fork repositories · default branches · profile excluded</text>
<text x="1052" y="1009" class="mono muted" font-size="12" text-anchor="end">UPDATED {e(updated)}</text>
<text x="48" y="1031" font-size="12" class="muted">Commit history, not push events. Activity uses UTC months; the current month is partial.</text>
<text x="1052" y="1031" font-size="12" class="muted" text-anchor="end">Created by atulhacks</text>
</svg>''')
    return "\n".join(parts) + "\n"
