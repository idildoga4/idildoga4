
import json
import os
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = "idildoga4"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "Token bulunamadı. GH_TOKEN veya GITHUB_TOKEN ortam değişkenini ayarla."
    )

# Son yaklaşık 6 ay
end_date = date.today()
start_date = end_date - timedelta(days=182)

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
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}",
        "User-Agent": "pink-github-activity-graph",
    },
)

with urllib.request.urlopen(request, timeout=30) as response:
    result = json.loads(response.read().decode("utf-8"))

if result.get("errors"):
    raise RuntimeError(
        "GitHub GraphQL hatası: "
        + json.dumps(result["errors"], ensure_ascii=False)
    )

user = result.get("data", {}).get("user")
if not user:
    raise RuntimeError(
        f"GitHub kullanıcısı bulunamadı: {USERNAME}. "
        "Token izinlerini ve kullanıcı adını kontrol et."
    )

calendar = user["contributionsCollection"]["contributionCalendar"]
days = [
    day
    for week in calendar["weeks"]
    for day in week["contributionDays"]
]

days = [
    day for day in days
    if start_date.isoformat() <= day["date"] <= end_date.isoformat()
]

total = sum(day["contributionCount"] for day in days)
active_days = sum(day["contributionCount"] > 0 for day in days)
max_count = max(
    (day["contributionCount"] for day in days),
    default=0,
)

print(f"GitHub takvimi toplamı: {calendar['totalContributions']}")
print(f"Grafikteki tarih aralığının katkıları: {total}")
print(f"Katkı bulunan gün sayısı: {active_days}")
print(f"En yoğun gün: {max_count}")

# Pembe renk paleti
COLORS = [
    "#fce7f3",
    "#f9a8d4",
    "#f472b6",
    "#db2777",
    "#9d174d",
]

def color_for_count(count):
    if count == 0 or max_count == 0:
        return COLORS[0]

    ratio = count / max_count

    if ratio <= 0.25:
        return COLORS[1]
    if ratio <= 0.50:
        return COLORS[2]
    if ratio <= 0.75:
        return COLORS[3]
    return COLORS[4]

# SVG boyutları
cell = 13
gap = 4
left = 42
top = 48
bottom = 32

# Haftanın günlerini Pazartesi'den başlayacak şekilde hizala.
first_date = date.fromisoformat(days[0]["date"]) if days else start_date
last_date = date.fromisoformat(days[-1]["date"]) if days else end_date

grid_start = first_date - timedelta(days=first_date.weekday())
grid_end = last_date + timedelta(days=(6 - last_date.weekday()))

columns = ((grid_end - grid_start).days + 1) // 7
width = left + columns * (cell + gap) + 12
height = top + 7 * (cell + gap) + bottom

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'width="100%" viewBox="0 0 {width} {height}">',
    f'<rect width="{width}" height="{height}" rx="12" fill="#fff5fa"/>',
    '<text x="14" y="24" font-family="Arial,sans-serif" '
    'font-size="15" font-weight="bold" fill="#9b527a">'
    'my last six months ♡</text>',
]

# Haftanın günleri
for label, weekday in [("Mon", 0), ("Wed", 2), ("Fri", 4)]:
    y = top + weekday * (cell + gap) + 10
    parts.append(
        f'<text x="7" y="{y}" font-family="Arial,sans-serif" '
        f'font-size="9" fill="#9b527a">{label}</text>'
    )

# Ay başlıkları
shown_months = set()

for day in days:
    current = date.fromisoformat(day["date"])
    col = (current - grid_start).days // 7

    if current.day <= 7:
        month_key = (current.year, current.month)
        if month_key not in shown_months:
            x = left + col * (cell + gap)
            month_label = current.strftime("%b")
            parts.append(
                f'<text x="{x}" y="{top - 10}" '
                'font-family="Arial,sans-serif" font-size="10" '
                f'fill="#9b527a">{month_label}</text>'
            )
            shown_months.add(month_key)

# Katkı kareleri
for day in days:
    current = date.fromisoformat(day["date"])
    col = (current - grid_start).days // 7
    row = current.weekday()

    x = left + col * (cell + gap)
    y = top + row * (cell + gap)

    count = day["contributionCount"]
    label = escape(f"{count} contributions on {day['date']}")

    parts.append(
        f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
        f'rx="3" fill="{color_for_count(count)}">'
        f'<title>{label}</title></rect>'
    )

parts.append(
    f'<text x="{left}" y="{height - 10}" '
    'font-family="Arial,sans-serif" font-size="10" fill="#9b527a">'
    f'{start_date:%d %b %Y} — {end_date:%d %b %Y}'
    '</text>'
)

parts.append("</svg>")

output = Path("assets/contributions-6-months.svg")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text("\n".join(parts), encoding="utf-8")

print(f"SVG oluşturuldu: {output}")
