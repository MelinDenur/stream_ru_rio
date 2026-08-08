"""
Запускается в GitHub Actions (не в браузере), поэтому CORS тут вообще
ни при чём — это обычный серверный HTTP-запрос.

Читает streamers.json (список стримеров), запрашивает Raider.IO API
по каждому персонажу и пишет результат в data.json.
Никакого season не передаём — Raider.IO по умолчанию отдаёт текущий
сезон, так что при выходе Midnight Season 2 и далее ничего менять не надо.
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import datetime
import sys

API_BASE = "https://raider.io/api/v2/characters/profile"


def fetch_character(region, realm, char):
    params = urllib.parse.urlencode({
        "region": region,
        "realm": realm,
        "name": char,
        "fields": "mythic_plus_scores_by_season:current,mythic_plus_best_runs",
    })
    url = f"{API_BASE}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "wow-streamers-personal-page/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    try:
        with open("streamers.json", "r", encoding="utf-8") as f:
            streamers = json.load(f)
    except FileNotFoundError:
        print("streamers.json не найден", file=sys.stderr)
        streamers = []

    results = []
    for s in streamers:
        entry = {
            "twitch": s["twitch"],
            "region": s["region"],
            "realm": s["realm"],
            "char": s["char"],
        }
        try:
            data = fetch_character(s["region"], s["realm"], s["char"])
            entry["status"] = "ok"
            entry["data"] = data
            print(f"OK: {s['char']}-{s['realm']}")
        except urllib.error.HTTPError as e:
            entry["status"] = "error"
            try:
                body = json.loads(e.read().decode("utf-8"))
                detail = body.get("error") or body.get("message") or ""
            except Exception:
                detail = ""
            entry["error"] = f"HTTP {e.code}" + (f": {detail}" if detail else "")
            print(f"HTTP ERROR {e.code}: {s['char']}-{s['realm']} — {detail}", file=sys.stderr)
        except Exception as e:
            entry["status"] = "error"
            entry["error"] = str(e)
            print(f"ERROR: {s['char']}-{s['realm']}: {e}", file=sys.stderr)
        results.append(entry)

    output = {
        "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "streamers": results,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Готово: {len(results)} персонажей записано в data.json")


if __name__ == "__main__":
    main()
