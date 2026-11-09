"""설정 md 읽기. 값 영역(`## 변경 이력` 절 앞의 표)만 해석하고, 변경 이력 절은 읽지 않는다."""
import re
import shutil
from pathlib import Path


class SettingsError(Exception):
    pass


_HISTORY = re.compile(r"^\s*#{1,6}\s*변경 이력")
_SEP = re.compile(r"^:?-{2,}:?$")

DEFAULT_BID = {"include": [], "exclude": [], "price_min": None, "price_max": None,
               "min_days": None, "exclude_types": []}
DEFAULT_GRANT = {"agencies": [], "fields": [], "keywords": [], "exclude": []}


def read_table(path):
    """값 영역의 첫 표를 (머리, 행 목록)으로 돌려준다."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        raise SettingsError("파일을 읽지 못함")
    header, rows = None, []
    for line in text.splitlines():
        if _HISTORY.match(line):
            break
        s = line.strip()
        if not s.startswith("|"):
            if header:
                break  # 첫 표가 끝남
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(_SEP.match(c) for c in cells if c) and any(cells):
            continue
        if header is None:
            header = cells
        else:
            rows.append(dict(zip(header, cells)))
    if header is None:
        raise SettingsError("값 표가 없음")
    return header, rows


def _csv(v):
    return [x.strip() for x in (v or "").split(",") if x.strip()]


def _int(v, name):
    v = (v or "").replace(",", "").replace("원", "").strip()
    if not v:
        return None
    if not v.isdigit():
        raise SettingsError(f"숫자가 아님({name}: {v})")
    return int(v)


def _kv(path, names):
    header, rows = read_table(path)
    if "항목" not in header or "값" not in header:
        raise SettingsError("표 머리에 항목/값 열이 없음")
    got = {r["항목"]: r["값"] for r in rows}
    missing = [n for n in names if n not in got]
    if missing:
        raise SettingsError("필수 행 없음(" + ", ".join(missing) + ")")
    return got


def load_bid_filter(path):
    g = _kv(path, ["포함 키워드", "제외 키워드", "추정가격 최소", "추정가격 최대",
                   "마감까지 최소 남은 일수", "제외할 기관 유형"])
    return {"include": _csv(g["포함 키워드"]), "exclude": _csv(g["제외 키워드"]),
            "price_min": _int(g["추정가격 최소"], "추정가격 최소"),
            "price_max": _int(g["추정가격 최대"], "추정가격 최대"),
            "min_days": _int(g["마감까지 최소 남은 일수"], "마감까지 최소 남은 일수"),
            "exclude_types": _csv(g["제외할 기관 유형"])}


def load_grant_criteria(path):
    g = _kv(path, ["관심 기관", "사업 분야", "지원사업 키워드", "제외 키워드"])
    return {"agencies": _csv(g["관심 기관"]), "fields": _csv(g["사업 분야"]),
            "keywords": _csv(g["지원사업 키워드"]), "exclude": _csv(g["제외 키워드"])}


def load_profile(path):
    """항목 -> {value, status, source}. 읽지 못하면 SettingsError."""
    header, rows = read_table(path)
    if "항목" not in header or "값" not in header or "확인 상태" not in header:
        raise SettingsError("표 머리에 항목/값/확인 상태 열이 없음")
    return {r["항목"]: {"value": r["값"], "status": r["확인 상태"], "source": r.get("출처", "")} for r in rows}


FILES = {"bid-filter.md": ("bid", load_bid_filter, DEFAULT_BID),
         "grant-criteria.md": ("grant", load_grant_criteria, DEFAULT_GRANT)}


def load_all(settings_dir, good_dir):
    """수집용 설정 2종을 읽는다. 오류가 있는 파일은 직전 정상 설정, 그것도 없으면 기본값을 쓴다."""
    cfg, problems = {}, []
    for name, (key, fn, default) in FILES.items():
        try:
            cfg[key] = fn(Path(settings_dir) / name)
        except SettingsError as e:
            try:
                cfg[key] = fn(Path(good_dir) / name)
                how = "직전 정상 설정으로 실행"
            except SettingsError:
                cfg[key] = default
                how = "직전 정상 설정이 없어 기본값(전부 통과)으로 실행"
            problems.append(f"{name}: {e} → {how}")
    return cfg, problems, list(FILES)


def save_good(settings_dir, good_dir):
    Path(good_dir).mkdir(parents=True, exist_ok=True)
    for name in FILES:
        shutil.copyfile(Path(settings_dir) / name, Path(good_dir) / name)
