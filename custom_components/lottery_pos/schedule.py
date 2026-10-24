"""Draw calendar rules (pure functions, no Home Assistant dependency).

A game draws on a date when:
  * the date is not a holiday that applies to the game, and
  * the weekly pattern says so.

Two weekly patterns exist:

``one_per_day`` games      ``week_schedule`` maps weekday -> ONE session
                           ("0": "midday", "1": "evening" ...). A weekday can
                           never have more than one draw. Missing weekday = no draw.
classic games              ``draw_days`` lists weekdays (empty = every day) and
                           every session of the game draws on those days.
"""
from __future__ import annotations

from datetime import date, timedelta


def easter(year: int) -> date:
    """Gregorian Easter Sunday (anonymous / Meeus algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def aruba_holidays(year: int) -> list[dict]:
    """Aruba public holidays. Always verify against the official government list."""
    e = easter(year)
    kings = date(year, 4, 27)
    if kings.weekday() == 6:  # Sunday -> Saturday before
        kings = date(year, 4, 26)
    labour = date(year, 5, 1)
    if labour.weekday() == 6:  # Sunday -> Monday after
        labour = date(year, 5, 2)
    items = [
        (date(year, 1, 1), "New Year's Day"),
        (date(year, 1, 25), "Betico Croes Day"),
        (e - timedelta(days=48), "Carnival Monday"),
        (date(year, 3, 18), "National Anthem and Flag Day"),
        (e - timedelta(days=2), "Good Friday"),
        (e + timedelta(days=1), "Easter Monday"),
        (kings, "King's Day"),
        (labour, "Labour Day"),
        (e + timedelta(days=39), "Ascension Day"),
        (date(year, 12, 25), "Christmas Day"),
        (date(year, 12, 26), "Boxing Day"),
    ]
    return [{"date": d.isoformat(), "name": n} for d, n in sorted(items)]


def holiday_for(holidays: list[dict], d: str, game_id: str | None = None) -> dict | None:
    """Holiday that blocks ``game_id`` on date ``d`` (empty ``games`` = all games)."""
    for h in holidays:
        if h.get("date") != d:
            continue
        scope = h.get("games") or []
        if not scope or game_id is None or game_id in scope:
            return h
    return None


def draws_on(game: dict, d: str, holidays: list[dict]) -> list[dict]:
    """Draws of ``game`` on ISO date ``d``: list of {id,label,draw_time,cutoff}.

    ``id`` is None for games without sessions.
    """
    if holiday_for(holidays, d, game.get("id")):
        return []
    wd = date.fromisoformat(d).weekday()
    sessions = game.get("sessions") or []
    if game.get("one_per_day"):
        sid = (game.get("week_schedule") or {}).get(str(wd))
        for s in sessions:
            if sid and s["id"] == sid:
                return [s]
        return []
    days = game.get("draw_days") or []
    if days and wd not in days:
        return []
    if sessions:
        return list(sessions)
    return [{"id": None, "label": "", "draw_time": game.get("draw_time") or "12:00",
             "cutoff": game.get("cutoff") or "23:59"}]


def next_draws(game: dict, holidays: list[dict], start: str, days: int) -> list[tuple[str, dict]]:
    """Every (date, session) draw of the game from ``start`` for ``days`` days."""
    out = []
    cur = date.fromisoformat(start)
    for _ in range(days + 1):
        iso = cur.isoformat()
        for s in draws_on(game, iso, holidays):
            out.append((iso, s))
        cur += timedelta(days=1)
    return out


def validate_week_schedule(raw: dict, sessions: list[dict]) -> dict:
    """Clean a {weekday: session_id} pattern. One draw per weekday by construction."""
    ids = {s["id"] for s in sessions}
    out = {}
    for k, v in (raw or {}).items():
        try:
            wd = int(k)
        except (TypeError, ValueError) as err:
            raise ValueError(f"Bad weekday '{k}'") from err
        if not 0 <= wd <= 6:
            raise ValueError("Weekday must be 0 (Mon) to 6 (Sun)")
        if v in (None, "", "none"):
            continue
        if isinstance(v, (list, tuple)):
            if len(v) > 1:
                raise ValueError("A weekday can only have one draw (midday OR evening)")
            v = v[0] if v else None
            if not v:
                continue
        if v not in ids:
            raise ValueError(f"Unknown draw '{v}'")
        out[str(wd)] = v
    return out
