import os
import json
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = "idildoga4"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

end_date = date.today()
start_date = end_date - timedelta(days=182)

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
            color
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
        "from": f"{start_date.isoformat()}T00:00:00Z",
        "to": f"{end_date.isoformat()}T23:59:59Z",
    },
}

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps(payload).encode(),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}",
    },
)

with urllib.request.urlopen(request) as response:
    result = json.loads(response.read())

if "errors" in result:
    raise RuntimeError(result["errors"])

weeks = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
days = [day for week in weeks for day in week["contributionDays"]]
days = [day for day in days if start_date.isoformat() <= day["date"] <= end_date.isoformat()]

cell = 13
gap = 4
left = 42
top = 42
columns = (len(days) + 6) // 7
width = left + columns * (cell + gap)
height = top + 7 * (cell + gap) + 30

pink_levels = ["#fce7f3", "#f9a8d4", "#f472b6", "#db2777", "#9d174d"]
max_count = max((d["contributionCount"] for d in days), default=0)

def level(count):
    if count == 0 or max_count == 0:
        return pink_levels[0]
    fraction = count / max_count
    if fraction <= 0.25:
        return pink_levels[1]
    if fraction <= 0.5:
        return pink_levels[2]
    if fraction <= 0.75:
        return pink_levels[3]
    return pink_levels[4]

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 {width} {height}">',
    '<rect width="100%" height="100%" rx="12" fill="#fff5fa"/>',
    '<text x="12" y="23" font-family="Arial,sans-serif" font-size="15" font-weight="bold" fill="#9b527a">my last six months ♡</text>',
]

for i, label in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
    if i in (0, 2, 4):
        parts.append(
            f'<text x="8" y="{top + i * (cell + gap) + 10}" font-family="Arial,sans-serif" font-size="9" fill="#9b527a">{label}</text>'
        )

for day in days:
    d = date.fromisoformat(day["date"])
    col = (d - start_date).days // 7
    row = d.weekday()
    x = left + col * (cell + gap)
    y = top + row * (cell + gap)
    count = day["contributionCount"]
    title = escape(f"{count} contributions on {day['date']}")
    parts.append(
        f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{level(count)}"><title>{title}</title></rect>'
    )

parts.append(
    f'<text x="{left}" y="{height - 8}" font-family="Arial,sans-serif" font-size="10" fill="#9b527a">{start_date:%d %b %Y} — {end_date:%d %b %Y}</text>'
)
parts.append("</svg>")

output = Path("assets/contributions-6-months.svg")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text("\n".join(parts), encoding="utf-8")
print(f"Created {output}")
