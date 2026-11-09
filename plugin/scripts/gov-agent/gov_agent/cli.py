"""명령줄 진입점. 인증키는 환경변수 또는 .env 에서만 읽고 출력하지 않는다."""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .demo_brief import build_brief
from .eligibility import build_eligibility
from .quotes import load_source, mark
from .runner import run

# 기본 경로는 현재 폴더(대표 PC의 작업 폴더) 기준이다. 코드는 플러그인 안에 있어도 된다(H11, H12).
DEFAULT_SETTINGS, DEFAULT_STATE, DEFAULT_ENV = "settings", "state", ".env"


def urllib_transport(url, params):
    """실제 네트워크 계층. 시험에서는 쓰지 않는다."""
    full = url + "?" + urllib.parse.urlencode(params) if params else url
    req = urllib.request.Request(full, headers={"User-Agent": "gov-agent/1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def read_env_file(path):
    env = {}
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return env
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("'\"")
    return env


def main(argv=None, transport=None, environ=None, now=None):
    ap = argparse.ArgumentParser(prog="gov_agent")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="하루치 수집을 실행해 결과 파일을 쓴다")
    r.add_argument("--date", required=True, help="실행 기준일 YYYY-MM-DD")
    r.add_argument("--out", required=True, help="결과 폴더")
    r.add_argument("--settings", default=DEFAULT_SETTINGS)
    r.add_argument("--state", default=DEFAULT_STATE)
    r.add_argument("--env-file", default=DEFAULT_ENV)
    e = sub.add_parser("eligibility", help="요건 JSON과 회사 프로필을 대조해 eligibility 항목을 낸다")
    e.add_argument("--input", required=True, help="요건 JSON 파일(docs/eligibility-input.md)")
    e.add_argument("--settings", default=DEFAULT_SETTINGS)
    e.add_argument("--out", help="결과를 쓸 파일(없으면 표준출력)")
    e.add_argument("--merge-into", help="하루치 결과 파일. 같은 공고번호의 항목은 바꾸고 새 공고는 eligibility에 추가한다")
    b = sub.add_parser("brief", help="2차 검토: 시연 신호 JSON을 판정해 시연 브리프를 낸다")
    b.add_argument("--input", required=True, help="시연 신호 JSON 파일(docs/demo-brief-input.md)")
    b.add_argument("--eligibility", help="같은 공고의 제안 조건 검토 결과(eligibility 명령의 출력)")
    b.add_argument("--settings", default=DEFAULT_SETTINGS)
    b.add_argument("--out", help="브리프를 쓸 파일(없으면 표준출력). 보통 drafts/<공고번호>/brief.json")
    for p in (e, b):
        p.add_argument("--source-text", help="첨부를 텍스트로 바꾼 폴더(.md·.txt). 주면 원문에 없는 인용은 확인필요가 된다")
    a = ap.parse_args(argv)

    data = None
    if a.cmd in ("brief", "eligibility"):
        data = json.loads(Path(a.input).read_text(encoding="utf-8"))
        if a.source_text:
            mark(data, load_source(a.source_text))

    if a.cmd == "brief":
        elig = json.loads(Path(a.eligibility).read_text(encoding="utf-8")) if a.eligibility else None
        text = json.dumps(build_brief(data, elig, Path(a.settings) / "demo-criteria.md"), ensure_ascii=False, indent=2)
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(text, encoding="utf-8")
        else:
            print(text)
        return 0

    if a.cmd == "eligibility":
        entry = build_eligibility(data, Path(a.settings) / "company-profile.md")
        text = json.dumps(entry, ensure_ascii=False, indent=2)
        if a.merge_into:
            target = Path(a.merge_into)
            result = json.loads(target.read_text(encoding="utf-8"))
            kept = [x for x in result.get("eligibility") or [] if x.get("bid_id") != entry["bid_id"]]
            result["eligibility"] = kept + [entry]
            target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        elif a.out:
            Path(a.out).write_text(text, encoding="utf-8")
        else:
            print(text)
        return 0

    env = {**read_env_file(a.env_file), **dict(os.environ if environ is None else environ)}
    path = run(a.date, a.out, a.settings, a.state, transport or urllib_transport, env=env, now=now)
    result = json.loads(path.read_text(encoding="utf-8"))
    print(f"결과 파일: {path}")
    for s in result["sources"]:
        why = f" ({s['error']['kind']})" if s["error"] else ""
        print(f"  {s['id']}: {s['status']}{why}, 받음 {s['fetched']}, 포함 {s['included']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
