"""Parsing and matching of externally published draw results (pure functions).

The importer in ``store.py`` fetches rows from the public results service and
uses these helpers to (1) turn each row into a normalised record and (2) find
the local game *and draw session* the record belongs to.

Why this is more careful than before:
  * every source request fails on its own - one bad request no longer loses
    the other results;
  * midday / evening rows are mapped to the game's sessions instead of being
    written to the same slot (the evening result used to overwrite midday);
  * names are compared after normalisation (case, punctuation, doubled
    letters), so "Phillipsburg" matches "PHILIPSBURG_AM";
  * numbers are padded / validated against the game's digit count.
"""
from __future__ import annotations

import json
import re
from datetime import date

SIGN_MAP = {
    "aries": "aries", "tauro": "taurus", "taurus": "taurus", "geminis": "gemini", "gemini": "gemini",
    "cancer": "cancer", "leo": "leo", "virgo": "virgo", "libra": "libra", "escorpio": "scorpio",
    "scorpio": "scorpio", "sagitario": "sagittarius", "sagittarius": "sagittarius",
    "capricornio": "capricorn", "capricorn": "capricorn", "acuario": "aquarius", "aquarius": "aquarius",
    "piscis": "pisces", "pisces": "pisces",
}

# Source game code (normalised, no period suffix) -> other names a local game may use.
ALIASES = {
    "diario": ["diario"],
    "corsow": ["korsow", "korsou", "wnk"],
    "korsow": ["corsow", "korsou", "wnk"],
    "flamingo": ["flamingo"],
    "super4": ["super4"],
    "philipsburg": ["philb", "phlp", "philipsburg"],
    "big4": ["big4"],
    "catochi": ["catochi"],
    "lucky3": ["lucky3"],
    "oneoff": ["1off", "oneoff"],
    "zodiac": ["zodiac"],
    "lottodia": ["lottodidia", "lottodia"],
    "lotto5": ["lotto5"],
    "minimega": ["minimega"],
    "megaplus": ["megaplus"],
}

_MIDDAY = {"midday", "merdia", "mediodia", "medio", "noon", "am", "morning", "mid", "day", "manana"}
_EVENING = {"evening", "anochi", "noche", "pm", "night", "eve", "tarde", "afternoon"}
_SUFFIX = re.compile(r"[_\-\s]+(am|pm|midday|merdia|mediodia|evening|anochi|noche|night|morning)$", re.I)


def norm(s) -> str:
    """lower-case, alphanumerics only, doubled letters collapsed."""
    s = re.sub(r"[^a-z0-9]", "", str(s or "").lower())
    return re.sub(r"([a-z])\1+", r"\1", s)


def period_of(word: str | None) -> str | None:
    w = re.sub(r"[^a-z]", "", str(word or "").lower())
    if w in _MIDDAY:
        return "midday"
    if w in _EVENING:
        return "evening"
    return None


def split_code(code: str) -> tuple[str, str | None]:
    """'PHILIPSBURG_AM' -> ('PHILIPSBURG', 'midday')."""
    c = str(code or "").strip()
    m = _SUFFIX.search(c)
    if not m:
        return c, None
    return c[: m.start()], period_of(m.group(1))


def _as_list(raw) -> list:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            raw = [x for x in re.split(r"[\s,;-]+", raw) if x]
    return raw if isinstance(raw, list) else []


def _as_dict(raw) -> dict:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            raw = {}
    return raw if isinstance(raw, dict) else {}


def row_date(row: dict) -> tuple[str | None, bool]:
    """(ISO date, assumed) - ``assumed`` is True when the row carries no usable date."""
    for k in ("draw_date", "date", "drawn_at", "draw_time", "created_at"):
        v = str(row.get(k) or "")[:10]
        try:
            date.fromisoformat(v)
            return v, False
        except ValueError:
            continue
    return None, True


def parse_row(row: dict, kind: str, period: str | None = None) -> dict | None:
    """Normalise one source row. ``kind`` is 'our' (daily 4-digit games) or 'lotto'."""
    if not isinstance(row, dict):
        return None
    code = str(row.get("game_code") or row.get("code") or "").strip()
    if not code:
        return None
    d, assumed = row_date(row)
    rec = {"code": code, "period": period or period_of(row.get("period")), "date": d,
           "date_assumed": assumed, "numbers": [], "kind": kind}
    if kind == "our":
        for k in ("first_prize", "second_prize", "third_prize", "skina4_prize"):
            v = row.get(k)
            s = str(v).strip() if v is not None else ""
            if s.isdigit():
                rec["numbers"].append(s)
        return rec
    raw = _as_list(row.get("numbers"))
    extra = _as_dict(row.get("extra"))
    base = norm(split_code(code)[0])
    nums: list[str] = []
    if base in {norm(x) for x in ("lottodia", "lotto5", "minimega", "megaplus")}:
        for x in raw:
            s = str(x).strip()
            if s.isdigit():
                nums.append(s.zfill(2))
        joker = extra.get("joker", extra.get("mega", extra.get("mega_ball")))
        if joker is not None and str(joker).strip().isdigit():
            nums.append(str(joker).strip().zfill(2))
        rec["jackpot"] = extra.get("jackpot")
    elif base == "zodiac":
        digits = "".join(str(x).strip() for x in raw if str(x).strip().isdigit())
        if digits:
            nums.append(digits)
        sign = str(extra.get("sign") or "").lower().strip()
        if sign:
            nums.append(SIGN_MAP.get(sign, sign))
    else:
        parts = [str(x).strip() for x in raw if str(x).strip()]
        if parts and all(p.isdigit() and len(p) == 1 for p in parts):
            nums.append("".join(parts))  # single digits -> one number
        else:
            nums.extend(p for p in parts if p.isdigit())
    rec["numbers"] = nums
    return rec


def _game_names(game: dict) -> set[str]:
    names = {norm(game.get("id")), norm(game.get("name"))}
    for ec in game.get("ext_codes") or []:
        names.add(norm(split_code(str(ec).split(":")[0])[0]))
    names.discard("")
    return names


def _pick_session(game: dict, period: str | None, record_code: str) -> tuple[str | None, str | None]:
    """(session_id, error)."""
    sessions = game.get("sessions") or []
    if not sessions:
        if not period:
            return None, None
        # single-draw local game fed by midday+evening rows: keep only the matching period
        t = str(game.get("draw_time") or "12:00")
        mine = "midday" if t < "16:00" else "evening"
        if period != mine:
            return None, f"{game.get('name')} has one draw ({mine}); {period} row ignored"
        return None, None
    if len(sessions) == 1:
        return sessions[0]["id"], None
    if period:
        for s in sessions:
            if period_of(s.get("id")) == period or period_of(s.get("label")) == period:
                return s["id"], None
        # fall back on time of day
        ordered = sorted(sessions, key=lambda s: s.get("draw_time") or "")
        return (ordered[0] if period == "midday" else ordered[-1])["id"], None
    return None, (f"{record_code}: {game.get('name')} has several draws - add the source code with a "
                  f"session (e.g. {record_code}:{sessions[0]['id']}) in the game's 'Result codes'")


def match_game(games: list[dict], code: str, period: str | None) -> tuple[dict | None, str | None, str | None]:
    """Return (game, session_id, error). ``error`` set when the row must be skipped."""
    full_n = norm(code)
    base_code, suffix_period = split_code(code)
    period = suffix_period or period  # the code's own AM/PM beats the request it came from
    base_n = norm(base_code)

    # 1) explicit mapping set by the owner: "CODE" or "CODE:session"
    for g in games:
        for ec in g.get("ext_codes") or []:
            raw, _, sid = str(ec).partition(":")
            if norm(raw) in (full_n, base_n):
                sid = sid.strip().lower()
                if sid:
                    if any(s["id"] == sid for s in g.get("sessions") or []):
                        return g, sid, None
                    return None, None, f"Result code {ec}: unknown session '{sid}'"
                sess, err = _pick_session(g, period, code)
                return (g, sess, None) if not err else (None, None, err)

    # 2) name match (enabled games first)
    keys = {base_n, full_n} | set(ALIASES.get(base_n, []))
    keys = {norm(k) for k in keys if k}
    ordered = sorted(games, key=lambda g: 0 if g.get("enabled", True) else 1)
    hit = next((g for g in ordered if _game_names(g) & keys), None)
    if not hit:
        # 3) loose containment, only when unambiguous
        loose = [g for g in ordered if any(len(k) >= 5 and len(n) >= 5 and (k in n or n in k)
                                           for k in keys for n in _game_names(g))]
        enabled = [g for g in loose if g.get("enabled", True)]
        pool = enabled or loose
        if len(pool) == 1:
            hit = pool[0]
    if not hit:
        return None, None, "no matching local game"
    sess, err = _pick_session(hit, period, code)
    if err:
        return None, None, err
    return hit, sess, None


def fit_numbers(game: dict, numbers: list[str]) -> list[str]:
    """Pad digit results to the game's digit count (source sometimes drops leading zeros)."""
    fmt = game.get("format", "digit")
    if fmt == "digit":
        dig = int(game.get("digits") or 4)
        return [n.zfill(dig) if n.isdigit() and len(n) < dig else n for n in numbers]
    if fmt == "zodiac":
        dig = int(game.get("digits") or 2)
        if numbers and numbers[0].isdigit() and len(numbers[0]) < dig:
            return [numbers[0].zfill(dig)] + numbers[1:]
    return numbers
