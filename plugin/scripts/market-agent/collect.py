"""market-agent YouTube collector (US-06).

  python collect.py search            -> data/candidates_YYYYMMDD.json
  python collect.py commit ID [ID...] -> add reported video IDs to data/seen.json

search: per language, 2 rotating keywords, YouTube "this week" filter via yt-dlp,
drops already-reported IDs. Relevance judgment, top-3 pick, publish-date check
(agent-reach youtube read) and summaries are done by the Claude run that calls this.
Stops at the first failure (e.g. HTTP 429) and records it; never retries.
"""
import datetime, json, pathlib, subprocess, sys, time, urllib.parse

HERE = pathlib.Path(__file__).parent
DATA = HERE / "data"
SEEN = DATA / "seen.json"
WEEK_FILTER = "EgIIAw%3D%3D"  # YouTube search: upload date = this week
PER_DAY = 2                   # keywords per language per day
PAUSE = 15                    # seconds between YouTube requests


def ytdlp():
    tools = subprocess.run(["uv", "tool", "dir"], capture_output=True, text=True).stdout.strip()
    exe = pathlib.Path(tools) / "agent-reach" / "Scripts" / "yt-dlp.exe"
    if not exe.exists():
        sys.exit(f"yt-dlp not found at {exe}; install Agent Reach first")
    return str(exe)


def todays_keywords(kws, day):
    # ponytail: plain round-robin by date; every keyword comes up every ceil(n/2) days
    rounds = max(1, -(-len(kws) // PER_DAY))
    start = (day.toordinal() % rounds) * PER_DAY
    return kws[start:start + PER_DAY]


def search(exe, keyword):
    url = ("https://www.youtube.com/results?search_query="
           + urllib.parse.quote(keyword) + "&sp=" + WEEK_FILTER)
    p = subprocess.run([exe, "--flat-playlist", "-J", url, "--playlist-end", "30"],
                       capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0:
        return None, (p.stderr.strip().splitlines() or ["unknown error"])[-1]
    return json.loads(p.stdout).get("entries", []), None


def cmd_search():
    DATA.mkdir(exist_ok=True)
    kw = json.loads((HERE / "keywords.json").read_text(encoding="utf-8"))
    seen = set(json.loads(SEEN.read_text(encoding="utf-8"))) if SEEN.exists() else set()
    today = datetime.date.today()
    exe, out, requests, error = ytdlp(), {}, 0, None
    for lang in ("ko", "en", "ja"):
        out[lang] = {}
        for k in todays_keywords(kw.get(lang, []), today):
            if error:
                break
            entries, error = search(exe, k)
            requests += 1
            if entries is None:
                break
            out[lang][k] = [
                {"id": e["id"], "url": f"https://www.youtube.com/watch?v={e['id']}",
                 "title": e.get("title"), "channel": e.get("channel"),
                 "views": e.get("view_count"), "duration": e.get("duration"),
                 "description": (e.get("description") or "")[:500]}
                for e in entries if e.get("id") and e["id"] not in seen]
            time.sleep(PAUSE)
    result = {"date": today.isoformat(), "ok": error is None, "error": error,
              "requests": requests, "candidates": out}
    path = DATA / f"candidates_{today:%Y%m%d}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "error": error, "requests": requests,
                      "file": str(path)}, ensure_ascii=False))


def cmd_commit(ids):
    DATA.mkdir(exist_ok=True)
    seen = json.loads(SEEN.read_text(encoding="utf-8")) if SEEN.exists() else []
    seen += [i for i in ids if i not in seen]
    SEEN.write_text(json.dumps(seen, indent=0), encoding="utf-8")
    print(f"seen: {len(seen)}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["search"]:
        cmd_search()
    elif sys.argv[1:2] == ["commit"] and len(sys.argv) > 2:
        cmd_commit(sys.argv[2:])
    elif sys.argv[1:2] == ["selftest"]:
        ks = ["a", "b", "c", "d", "e"]
        days = [datetime.date(2026, 11, 5) + datetime.timedelta(d) for d in range(3)]
        got = [todays_keywords(ks, d) for d in days]
        assert sorted(sum(got, [])) == ks, got  # 3 days cover all 5 keywords once
        assert all(1 <= len(g) <= PER_DAY for g in got), got
        print("selftest ok", got)
    else:
        sys.exit(__doc__)
