
import json
import os
import calendar
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = "idildoga4"
TOKEN = os.environ["GITHUB_TOKEN"]
OUTPUT = Path("assets/contributions-6-months.svg")

today = datetime.now(timezone.utc).date()

# Takvim olarak tam 6 ay geriye git.
month = today.month - 6
year = today.year
while month <= 0:
    month += 12
    year -= 1

start = date(
    year,
    month,
    min(today.day, calendar.monthrange(year, month)[1]),
)

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""

payload = {
    "query": query,
    "variables": {
        "login": USERNAME,
        "from": f"{start.isoformat()}T00:00:00Z",
        "to": f"{today.isoformat()}T23:59:59Z",
    },
}

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps(payload).encode(),
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": USERNAME,
    },
)

with urllib.request.urlopen(request, timeout=30) as response:
    result = json.load(response)

if result.get("errors"):
    raise RuntimeError(json.dumps(result["errors"], indent=2))

user = result["data"]["user"]
if user is None:
    raise RuntimeError(f"GitHub user not found: {USERNAME}")

calendar_data = user["contributionsCollection"]["contributionCalendar"]
days = {}

for week in calendar_data["weeks"]:
    for day in week["contributionDays"]:
        days[date.fromisoformat(day["date"])] = day

# Haftaları pazartesi başlangıçlı göster.
grid_start = start - timedelta(days=start.weekday())
grid_end = today + timedelta(days=6 - today.weekday())

weeks = (grid_end - grid_start).days // 7 + 1
cell = 12
gap = 4
step = cell + gap
left = 48
top = 67
width = left + weeks * step + 20
height = top + 7 * step + 45

palette = {
    "NONE": "#FCEAF2",
    "FIRST_QUARTILE": "#F6C7DC",
    "SECOND_QUARTILE": "#ED9FC4",
    "THIRD_QUARTILE": "#D96BA5",
    "FOURTH_QUARTILE": "#A9407E",
}

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
    f'<rect width="100%" height="100%" rx="18" fill="#FFF7FB"/>',
    '<text x="22" y="29" font-size="17" font-weight="700" '
    'fill="#8E456F" font-family="Arial, sans-serif">'
    'my coding era ♡</text>',
    f'<text x="22" y="47" font-size="10" fill="#A16C8A" '
    f'font-family="Arial, sans-serif">'
    f'{start:%d %b %Y} — {today:%d %b %Y}</text>',
    f'<text x="{width - 22}" y="30" text-anchor="end" '
    f'font-size="12" font-weight="700" fill="#B94E8C" '
    f'font-family="Arial, sans-serif">'
    f'{calendar_data["totalContributions"]} contributions</text>',
]

# Haftalık sütunların üstünde ay adları.
seen_months = set()
cursor = grid_start
while cursor <= grid_end:
    if cursor.day == 1 or cursor == grid_start:
        key = (cursor.year, cursor.month)
        if key not in seen_months and cursor >= start.replace(day=1):
            x = left + ((cursor - grid_start).days // 7) * step
            parts.append(
                f'<text x="{x}" y="62" font-size="9" fill="#A16C8A" '
                f'font-family="Arial, sans-serif">'
                f'{escape(cursor.strftime("%b"))}</text>'
            )
            seen_months.add(key)
    cursor += timedelta(days=1)

for row, label in enumerate(["Mon", "", "Wed", "", "Fri", "", ""]):
    if label:
        parts.append(
            f'<text x="22" y="{top + row * step + 10}" '
            f'font-size="9" fill="#A16C8A" '
            f'font-family="Arial, sans-serif">{label}</text>'
        )

cursor = start
while cursor <= today:
    day = days.get(cursor, {})
    count = day.get("contributionCount", 0)
    level = day.get("contributionLevel", "NONE")

    column = (cursor - grid_start).days // 7
    row = cursor.weekday()
    x = left + column * step
    y = top + row * step
    color = palette.get(level, "#FCEAF2")

    parts.append(
        f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
        f'rx="3" fill="{color}">'
        f'<title>{cursor.isoformat()}: {count} contributions</title>'
        f'</rect>'
    )
    cursor += timedelta(days=1)

parts.extend([
    f'<text x="22" y="{height - 15}" font-size="9" '
    f'fill="#A16C8A" font-family="Arial, sans-serif">'
    'less</text>'
])

for index, color in enumerate(palette.values()):
    x = width - 104 + index * 16
    parts.append(
        f'<rect x="{x}" y="{height - 24}" width="11" height="11" '
        f'rx="3" fill="{color}"/>'
    )

parts.append("</svg>")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(parts), encoding="utf-8")

print(f"Generated {OUTPUT} for {start} through {today}")
