"""Persistent data + business logic (sales, results, settlement)."""
from __future__ import annotations

import calendar
import json
import urllib.request
import copy
import re
import secrets
from datetime import date as _date, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (DEFAULT_BET_TYPES, DEFAULT_GAMES, DEFAULT_PROMOTIONS, DOMAIN,
                    PLAY_WHE_MARKS, SIGNAL_UPDATE, STORAGE_KEY, STORAGE_VERSION, TICKET_DEFAULTS, ZODIAC_SYMBOLS)


class LotteryError(ValueError):
    """Validation error that is shown to the retailer."""


class LotteryStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.data: dict = {}

    async def async_load(self, currency: str = "AWG") -> None:
        data = await self._store.async_load()
        if not data:
            data = {
                "games": copy.deepcopy(DEFAULT_GAMES),
                "bet_types": copy.deepcopy(DEFAULT_BET_TYPES),
                "retailers": [{"id": "main", "number": "001", "name": "Main Shop", "first_name": "", "last_name": "", "address": "", "phone": "", "commission": 10.0, "commission_sell": 10.0, "commission_redeem": 2.0, "active": True}],
                "tickets": {}, "results": {}, "seq": 0,
                "promotions": copy.deepcopy(DEFAULT_PROMOTIONS),
            }
        data["currency"] = currency
        data.setdefault("settings", {"name": "Lottery POS", "logo": ""})
        data["settings"].setdefault("ticker", {"enabled": True, "text": "Welcome! Play responsibly - good luck to all our players!", "speed": 5, "color": "#39ff14"})
        data["settings"]["ticket"] = {**TICKET_DEFAULTS, **data["settings"].get("ticket", {})}
        data.setdefault("promotions", copy.deepcopy(DEFAULT_PROMOTIONS))
        data.setdefault("promo_codes", {})
        for g in data["games"]:
            g.setdefault("open_time", "00:00")
            g.setdefault("enabled", True)
            g.setdefault("bet_types", [])
            g.setdefault("draw_days", [])
            g.setdefault("format", "digit")  # digit | zodiac | jackpot | whe
            g.setdefault("digits", 4)  # digit / zodiac / whe number length
            g.setdefault("main_count", 5)  # jackpot main balls to pick
            g.setdefault("main_max", 30)  # jackpot main pool 01..main_max
            g.setdefault("mega_count", 0)  # 0 or 1
            g.setdefault("mega_max", 15)
            g.setdefault("sessions", [])  # [{id,label,draw_time,cutoff}] multi-draw same day
            west_ids = [z["id"] for z in ZODIAC_SYMBOLS]
            legacy = {"rat","ox","tiger","rabbit","dragon","snake","horse","goat","monkey","rooster","dog","pig"}
            if "symbols" not in g or not g["symbols"] or set(g["symbols"]) <= legacy:
                g["symbols"] = list(west_ids)
            else:
                # keep only known western ids
                g["symbols"] = [s for s in g["symbols"] if s in west_ids] or list(west_ids)
            if not isinstance(g.get("id"), str):
                g["id"] = str(g["id"])
        # Migrate legacy Philb-AM / Philb-PM into one Phillipsburg with sessions
        ids = {g["id"] for g in data["games"]}
        if "philb_am" in ids or "philb_pm" in ids:
            if "philb" not in ids:
                am = next((g for g in data["games"] if g["id"] == "philb_am"), None)
                pm = next((g for g in data["games"] if g["id"] == "philb_pm"), None)
                base = dict(am or pm or {})
                base.update({
                    "id": "philb",
                    "name": "Phillipsburg",
                    "color": (am or pm or {}).get("color", "#84cc16"),
                    "draw_time": (am or {}).get("draw_time", "11:00"),
                    "cutoff": (am or {}).get("cutoff", "10:45"),
                    "format": (am or pm or {}).get("format", "digit"),
                    "digits": (am or pm or {}).get("digits", 4),
                    "sessions": [
                        {"id": "am", "label": "AM",
                         "draw_time": (am or {}).get("draw_time", "11:00"),
                         "cutoff": (am or {}).get("cutoff", "10:45")},
                        {"id": "pm", "label": "PM",
                         "draw_time": (pm or {}).get("draw_time", "19:00"),
                         "cutoff": (pm or {}).get("cutoff", "18:45")},
                    ],
                    "enabled": True,
                })
                data["games"].append(base)
            # hide old split games (keep history)
            for g in data["games"]:
                if g["id"] in ("philb_am", "philb_pm"):
                    g["enabled"] = False
        # Ensure Play Whe default game exists
        if "playwhe" not in {g["id"] for g in data["games"]}:
            for dg in DEFAULT_GAMES:
                if dg["id"] == "playwhe":
                    data["games"].append(copy.deepcopy(dg))
                    break
        for b in data["bet_types"]:
            b.setdefault("enabled", True)
        known_bt = {b["key"] for b in data["bet_types"]}
        for b in DEFAULT_BET_TYPES:
            if b["key"] not in known_bt:
                data["bet_types"].append(copy.deepcopy(b))
        for i, r in enumerate(data.get("retailers", [])):
            r.setdefault("number", f"{i+1:03d}")
            r.setdefault("first_name", "")
            r.setdefault("last_name", "")
            r.setdefault("address", "")
            r.setdefault("phone", "")
            r.setdefault("commission", 10.0)
            r.setdefault("commission_sell", float(r.get("commission", 10.0)))
            r.setdefault("commission_redeem", 0.0)
            r.setdefault("active", True)
            if not isinstance(r.get("id"), str):
                r["id"] = str(r["id"])
        for p in data["promotions"]:
            p.setdefault("enabled", True)
            if p.get("trigger") == "min_lines":
                p["trigger"] = "min_plays"
            p.setdefault("trigger", "min_plays")
            p.setdefault("trigger_value", 3)
            p.setdefault("code_digits", 6)
            p.setdefault("games", [])
            p.setdefault("label", "Qualified for promotion")
            p.setdefault("instruction", "Visit www.shocolottery.com and check if you have won")
            p.setdefault("url", "https://www.shocolottery.com")
            p.setdefault("start_at", "")
            p.setdefault("end_at", "")
            p.setdefault("prize", 0.0)
            p.setdefault("prizes", [])
            # migrate single prize into prizes list if empty
            if not p.get("prizes") and float(p.get("prize") or 0) > 0:
                p["prizes"] = [{"label": "Winner prize", "amount": float(p["prize"]), "quantity": 1}]
            # ensure id is always a string (legacy numeric ids)
            if not isinstance(p.get("id"), str):
                p["id"] = str(p["id"])
        self.data = data
        self._save()

    def _save(self) -> None:
        self._store.async_delay_save(lambda: self.data, 1)
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)

    # ---------- lookups ----------
    def _find(self, coll: str, key: str, val: str, label: str) -> dict:
        for item in self.data[coll]:
            if item[key] == val:
                return item
        raise LotteryError(f"Unknown {label}: {val}")


    def _session(self, game: dict, session_id: str | None) -> dict | None:
        """Return session dict for game, or None if game has no sessions."""
        sessions = game.get("sessions") or []
        if not sessions:
            return None
        if not session_id:
            return sessions[0]
        for s in sessions:
            if s.get("id") == session_id:
                return s
        raise LotteryError(f"Unknown session '{session_id}' for {game.get('name')}")

    def _result_key(self, game_id: str, d: str, session_id: str | None = None) -> str:
        if session_id:
            return f"{game_id}|{d}|{session_id}"
        return f"{game_id}|{d}"

    def _cutoff_for(self, game: dict, session_id: str | None = None) -> str:
        sess = self._session(game, session_id) if (game.get("sessions") or []) else None
        if sess and sess.get("cutoff"):
            return sess["cutoff"]
        return game.get("cutoff") or "23:59"

    def ticket(self, tid: str) -> dict:
        t = self.data["tickets"].get(str(tid).strip())
        if not t:
            raise LotteryError("Ticket not found")
        return t

    def public(self, t: dict) -> dict:
        out = copy.deepcopy(t)
        try:
            out["retailer_name"] = self._find("retailers", "id", t["retailer_id"], "retailer")["name"]
        except LotteryError:
            out["retailer_name"] = t["retailer_id"]
        return out

    def _closed(self, line: dict) -> bool:
        now = dt_util.now()
        today = now.date().isoformat()
        game = self._find("games", "id", line["game"], "game")
        cutoff = self._cutoff_for(game, line.get("session"))
        return line["date"] < today or (line["date"] == today and now.strftime("%H:%M") >= cutoff)

    # ---------- selling ----------
    def sell(self, retailer_id: str, lines: list[dict]) -> dict:
        if not lines:
            raise LotteryError("Ticket is empty")
        retailer = self._find("retailers", "id", retailer_id, "retailer")
        if not retailer.get("active", True):
            raise LotteryError("Retailer is disabled")
        clean = []
        for ln in lines:
            game = self._find("games", "id", ln["game"], "game")
            fmt = game.get("format", "digit")
            bt_key = ln.get("bet_type") or ("jackpot" if fmt == "jackpot" else "zodiac" if fmt == "zodiac" else "play_whe" if fmt == "whe" else None)
            if not bt_key:
                raise LotteryError("Bet type required")
            bt = self._find("bet_types", "key", bt_key, "bet type")
            if not game.get("enabled", True):
                raise LotteryError(f"{game['name']} is not on sale")
            allowed = game.get("bet_types") or []
            if fmt == "digit":
                if not bt.get("enabled", True) or (allowed and bt["key"] not in allowed):
                    raise LotteryError(f"{bt['label']} is not available for {game['name']}")
            amt = round(float(ln["amount"]), 2)
            if amt <= 0:
                raise LotteryError("Amount must be above 0")
            line = {"game": game["id"], "bet_type": bt["key"], "amount": amt,
                    "date": ln["date"], "prize": 0.0, "settled": False, "format": fmt}
            if fmt == "digit":
                digits = int(game.get("digits") or bt.get("digits") or 4)
                num = str(ln.get("number", "")).strip()
                if not (num.isdigit() and len(num) == digits):
                    raise LotteryError(f"{game['name']} needs a {digits}-digit number (0–{'9'*digits})")
                line["number"] = num
            elif fmt == "zodiac":
                digits = int(game.get("digits") or 2)
                num = str(ln.get("number", "")).strip()
                if not (num.isdigit() and len(num) == digits):
                    raise LotteryError(f"{game['name']} needs a {digits}-digit number with zodiac symbol(s)")
                allowed_sym = set(game.get("symbols") or [z["id"] for z in ZODIAC_SYMBOLS])
                syms = ln.get("symbols") or []
                if not isinstance(syms, list) or not syms:
                    raise LotteryError("Select at least one zodiac symbol (or All)")
                syms = [str(s) for s in syms]
                bad = [s for s in syms if s not in allowed_sym]
                if bad:
                    raise LotteryError(f"Unknown symbol(s): {', '.join(bad)}")
                # unique preserve order
                seen = set()
                uniq = []
                for s in syms:
                    if s not in seen:
                        seen.add(s)
                        uniq.append(s)
                line["number"] = num
                line["symbols"] = uniq
            elif fmt == "whe":
                # Play Whe: single mark 1–36
                num = str(ln.get("number", "")).strip()
                try:
                    n = int(num)
                except (TypeError, ValueError):
                    n = -1
                if not (1 <= n <= 36):
                    raise LotteryError(f"{game['name']} needs a mark from 1 to 36")
                line["number"] = f"{n:02d}"
                mark = next((m for m in PLAY_WHE_MARKS if m["num"] == n), None)
                line["mark"] = mark["label"] if mark else str(n)
                if mark and mark.get("emoji"):
                    line["mark_emoji"] = mark["emoji"]
            elif fmt == "jackpot":
                main_count = int(game.get("main_count") or 5)
                main_max = int(game.get("main_max") or 30)
                mega_count = int(game.get("mega_count") or 0)
                mega_max = int(game.get("mega_max") or 15)
                balls = ln.get("balls") or []
                if not isinstance(balls, list):
                    raise LotteryError("Jackpot balls must be a list")
                norm = []
                for b in balls:
                    s = str(b).strip()
                    if not s.isdigit():
                        raise LotteryError(f"Invalid ball: {b}")
                    n = int(s)
                    if not 1 <= n <= main_max:
                        raise LotteryError(f"Ball must be 01–{main_max:02d}")
                    norm.append(f"{n:02d}")
                if len(set(norm)) != len(norm):
                    raise LotteryError("Jackpot balls must be unique")
                if len(norm) != main_count:
                    raise LotteryError(f"Pick exactly {main_count} balls from 01–{main_max:02d}")
                line["balls"] = sorted(norm)
                line["number"] = "-".join(line["balls"])
                if mega_count:
                    mega = str(ln.get("mega", "")).strip()
                    if not mega.isdigit() or not 1 <= int(mega) <= mega_max:
                        raise LotteryError(f"Mega ball must be 01–{mega_max:02d}")
                    line["mega"] = f"{int(mega):02d}"
                    line["number"] = f"{line['number']}+{line['mega']}"
                else:
                    line["mega"] = ""
            else:
                raise LotteryError(f"Unknown game format: {fmt}")
            # stake limits: game override, else bet type
            min_s = float(game.get("min_stake") or bt.get("min_stake") or 0.01)
            max_s = float(game.get("max_stake") or bt.get("max_stake") or 1_000_000)
            if amt < min_s or amt > max_s:
                raise LotteryError(f"Amount for {game['name']} must be {min_s:g}–{max_s:g}")
            # Optional same-day session (AM / Midday / Evening …)
            sessions = game.get("sessions") or []
            sess_id = str(ln.get("session") or "").strip() or None
            if sessions:
                if not sess_id:
                    # default to first still-open session for the date, else first
                    now = dt_util.now()
                    today = now.date().isoformat()
                    chosen = None
                    if ln.get("date") == today:
                        hm = now.strftime("%H:%M")
                        for s in sessions:
                            if hm < (s.get("cutoff") or "23:59"):
                                chosen = s
                                break
                    sess_id = (chosen or sessions[0])["id"]
                self._session(game, sess_id)  # validates
                line["session"] = sess_id
                sess = self._session(game, sess_id)
                line["session_label"] = sess.get("label") or sess_id
            elif sess_id:
                raise LotteryError(f"{game['name']} has no draw sessions")
            try:
                multi = max(1, min(28, int(ln.get("draws") or ln.get("multi_draw") or 1)))
            except (TypeError, ValueError):
                multi = 1
            base_date = line["date"]
            dates = self._multi_draw_dates(game, base_date, multi)
            for d in dates:
                one = dict(line)
                one["date"] = d
                try:
                    wd = _date.fromisoformat(d).weekday()
                except ValueError as err:
                    raise LotteryError("Invalid draw date") from err
                if game.get("draw_days") and wd not in game["draw_days"]:
                    raise LotteryError(f"{game['name']} has no draw on {calendar.day_name[wd]}")
                if self._closed(one):
                    raise LotteryError(f"{game['name']} is closed for {d}")
                if d == dt_util.now().date().isoformat() and dt_util.now().strftime("%H:%M") < game.get("open_time", "00:00"):
                    raise LotteryError(f"{game['name']} opens at {game['open_time']}")
                rkey = self._result_key(game["id"], d, line.get("session"))
                if rkey in self.data["results"]:
                    label = line.get("session_label") or line.get("session") or ""
                    raise LotteryError(f"{game['name']} {d}{(' ' + label) if label else ''} already drawn")
                one["draws"] = multi
                clean.append(one)
            # progressive jackpot: contribute per play (once per multi-draw purchase unit)
            if fmt == "jackpot":
                contrib = float(game.get("jackpot_contrib") or 0)
                if contrib > 0:
                    add = round(amt * multi * contrib, 2)
                    game["jackpot_current"] = round(float(game.get("jackpot_current") or game.get("jackpot_min") or 0) + add, 2)
        now = dt_util.now()
        self.data["seq"] += 1
        tid = f"{now:%y%m%d}{self.data['seq'] % 10000:04d}{secrets.randbelow(10**8):08d}"
        promos = self._apply_promotions(clean)
        ticket = {"id": tid, "retailer_id": retailer["id"], "created": now.isoformat(), "lines": clean,
                  "total": round(sum(l["amount"] for l in clean), 2), "status": "active", "prize": 0.0,
                  "promotions": promos}
        self.data["tickets"][tid] = ticket
        self._save()
        self.hass.bus.async_fire(f"{DOMAIN}_ticket_sold", {"ticket_id": tid, "retailer_id": retailer["id"], "total": ticket["total"]})
        return self.public(ticket)

    def _multi_draw_dates(self, game: dict, start: str, count: int) -> list[str]:
        """Next `count` valid draw dates starting at start (inclusive)."""
        try:
            d0 = _date.fromisoformat(start)
        except ValueError as err:
            raise LotteryError("Invalid draw date") from err
        days = game.get("draw_days") or []
        out = []
        cur = d0
        guard = 0
        while len(out) < count and guard < 400:
            guard += 1
            if not days or cur.weekday() in days:
                out.append(cur.isoformat())
            cur = cur + timedelta(days=1)
        if len(out) < count:
            raise LotteryError("Could not schedule multi-draw dates")
        return out

    def _apply_promotions(self, lines: list[dict]) -> list[dict]:
        """Award promotion codes for every enabled promo whose trigger is met.

        Scope: games empty = all games; otherwise only listed game ids count.
        Triggers:
          min_plays  – matching line count >= value
          min_games  – distinct matching games >= value
          min_amount – sum of matching amounts >= value (currency)
        Legacy min_lines is treated as min_plays.
        """
        awarded = []
        now = dt_util.now()
        now_iso = now.isoformat(timespec="minutes")
        today = now.date().isoformat()
        for p in self.data.get("promotions", []):
            if not p.get("enabled", True):
                continue
            try:
                # Schedule window: empty = always; date-only or datetime
                sa = (p.get("start_at") or "").strip()
                ea = (p.get("end_at") or "").strip()
                if sa:
                    if "T" in sa:
                        if now_iso < sa:
                            continue
                    else:
                        if today < sa:
                            continue
                if ea:
                    if "T" in ea:
                        if now_iso > ea:
                            continue
                    else:
                        if today > ea:
                            continue
                scope = set(p.get("games") or [])
                matched = [l for l in lines if not scope or l["game"] in scope]
                if not matched:
                    continue
                trig = p.get("trigger", "min_plays")
                if trig == "min_lines":
                    trig = "min_plays"
                val = float(p.get("trigger_value", 3))
                if trig == "min_plays":
                    ok = len(matched) >= val
                elif trig == "min_games":
                    ok = len({l["game"] for l in matched}) >= val
                elif trig == "min_amount":
                    ok = sum(float(l["amount"]) for l in matched) >= val
                else:
                    continue
                if not ok:
                    continue
                digits = max(4, min(10, int(p.get("code_digits", 6))))
                # unique code not already used
                codes = self.data.setdefault("promo_codes", {})
                for _ in range(20):
                    code = f"{secrets.randbelow(10 ** digits):0{digits}d}"
                    if code not in codes:
                        break
                prize = float(p.get("prize") or 0)
                prizes = p.get("prizes") or []
                if not prize and prizes:
                    prize = max((float(x.get("amount") or 0) for x in prizes), default=0)
                entry = {
                    "id": str(p["id"]),
                    "name": p.get("name", "Promotion"),
                    "code": code,
                    "label": p.get("label", "Qualified for promotion"),
                    "instruction": p.get("instruction", "Visit www.shocolottery.com and check if you have won"),
                    "url": p.get("url", "https://www.shocolottery.com"),
                    "prize": prize,
                }
                awarded.append(entry)
                codes[code] = {
                    "code": code,
                    "promotion_id": str(p["id"]),
                    "promotion_name": p.get("name", "Promotion"),
                    "created": now.isoformat(),
                    "status": "pending",  # pending | won | lost
                    "prize_label": "",
                    "prize_amount": 0.0,
                    "claimed": False,
                }
            except (TypeError, ValueError, KeyError):
                continue
        return awarded

    def cancel(self, tid: str) -> dict:
        t = self.ticket(tid)
        if t["status"] != "active":
            raise LotteryError(f"Ticket is {t['status']}")
        if any(l["settled"] or self._closed(l) for l in t["lines"]):
            raise LotteryError("A draw on this ticket is already closed")
        t["status"] = "cancelled"
        self._save()
        self.hass.bus.async_fire(f"{DOMAIN}_ticket_cancelled", {"ticket_id": t["id"]})
        return self.public(t)

    def redeem(self, tid: str, retailer_id: str | None = None) -> dict:
        t = self.ticket(tid)
        if t["status"] == "redeemed":
            raise LotteryError("Already paid")
        if t["status"] != "won":
            raise LotteryError("Not a winning ticket" if t["status"] == "lost" else f"Ticket is {t['status']} (draw pending)")
        rid = (retailer_id or t.get("retailer_id") or "").strip()
        if rid:
            self._find("retailers", "id", rid, "retailer")
        t["status"] = "redeemed"
        t["redeemed_at"] = dt_util.now().isoformat()
        t["redeemed_by"] = rid or t.get("retailer_id")
        self._save()
        return self.public(t)

    # ---------- results & settlement ----------
    def _prize(self, ln: dict, nums: list[str]) -> float:
        """Settle a play against drawn numbers.

        nums layout depends on format:
          digit: ["4821", "0377", "9150"]  (1st/2nd/3rd)
          zodiac: ["12", "rat"] or ["12", "rat", "ox"]  (number + winning symbol ids)
          jackpot: main balls then optional mega e.g. ["01","05","12","20","28","07"]
        """
        bt = self._find("bet_types", "key", ln["bet_type"], "bet type")
        fmt = ln.get("format") or "digit"
        if fmt == "zodiac":
            if not nums:
                return 0.0
            drawn_num = str(nums[0]).zfill(len(ln.get("number", "00")))
            drawn_syms = set(str(x) for x in nums[1:])
            play_syms = set(ln.get("symbols") or [])
            if ln.get("number") == drawn_num and play_syms & drawn_syms:
                return round(ln["amount"] * float(bt.get("multiplier", 1)), 2)
            return 0.0
        if fmt == "whe":
            if not nums:
                return 0.0
            try:
                drawn = int(str(nums[0]).strip())
                play = int(str(ln.get("number") or "0").strip())
            except (TypeError, ValueError):
                return 0.0
            if drawn == play and 1 <= drawn <= 36:
                return round(ln["amount"] * float(bt.get("multiplier", 24)), 2)
            return 0.0
        if fmt == "jackpot":
            game = self._find("games", "id", ln["game"], "game")
            main_count = int(game.get("main_count") or 5)
            mega_count = int(game.get("mega_count") or 0)
            if len(nums) < main_count:
                return 0.0
            drawn_main = set(f"{int(x):02d}" for x in nums[:main_count])
            play_main = set(ln.get("balls") or [])
            matched = len(drawn_main & play_main)
            mega_hit = False
            if mega_count:
                if len(nums) < main_count + 1:
                    return 0.0
                drawn_mega = f"{int(nums[main_count]):02d}"
                mega_hit = (ln.get("mega") or "") == drawn_mega
            prizes = game.get("jackpot_prizes") or []
            # best matching tier: highest match, then mega preference
            best = None
            for pr in prizes:
                need = int(pr.get("match") or 0)
                need_mega = bool(pr.get("mega"))
                if matched < need:
                    continue
                if need_mega and not mega_hit:
                    continue
                if best is None or need > int(best.get("match") or 0) or (
                    need == int(best.get("match") or 0) and need_mega and not best.get("mega")
                ):
                    best = pr
            if not best:
                return 0.0
            ptype = best.get("prize_type") or "fixed"
            if ptype == "jackpot":
                pool = float(game.get("jackpot_current") or game.get("jackpot_min") or 0)
                # reset pool to minimum after win (caller settles one winner; simple model)
                game["jackpot_current"] = float(game.get("jackpot_min") or 0)
                return round(pool, 2)
            if ptype == "multiplier":
                return round(ln["amount"] * float(best.get("amount") or bt.get("multiplier") or 1), 2)
            return round(float(best.get("amount") or 0), 2)
        # digit / classic
        n, first, mode, d = ln["number"], nums[0], bt["mode"], bt["digits"]
        if mode == "exact":
            hits = n == first[-d:]
        elif mode == "perm":
            hits = sorted(n) == sorted(first[-d:])
        elif mode == "bf":
            hits = n in (first[:2], first[-2:])
        elif mode == "back":
            hits = n == first[-2:]
        else:  # chances
            hits = sum(1 for x in nums if x[-2:] == n)
        return round(ln["amount"] * bt["multiplier"] * int(hits), 2)

    def set_results(self, game: str, d: str, numbers: list[str], session: str | None = None) -> list[dict]:
        g = self._find("games", "id", game, "game")
        nums = [str(n).strip() for n in numbers if str(n).strip()]
        if not nums:
            raise LotteryError("Enter at least one result value")
        sessions = g.get("sessions") or []
        if sessions:
            if not session:
                session = sessions[0]["id"]
            self._session(g, session)
        elif session:
            raise LotteryError(f"{g['name']} has no draw sessions")
        fmt = g.get("format", "digit")
        if fmt == "digit":
            dig = int(g.get("digits") or 4)
            if any(not n.isdigit() for n in nums):
                raise LotteryError("Digit game results must be numbers")
        elif fmt == "zodiac":
            if len(nums) < 2:
                raise LotteryError("Zodiac results: number then winning symbol id(s)")
        elif fmt == "whe":
            try:
                n = int(nums[0])
            except (TypeError, ValueError) as err:
                raise LotteryError("Play Whe result must be a number 1–36") from err
            if not 1 <= n <= 36:
                raise LotteryError("Play Whe result must be 1–36")
            nums = [str(n)]
        elif fmt == "jackpot":
            need = int(g.get("main_count") or 5) + (1 if int(g.get("mega_count") or 0) else 0)
            if len(nums) < need:
                raise LotteryError(f"Jackpot results need {need} values (main balls + mega if any)")
        rkey = self._result_key(game, d, session)
        self.data["results"][rkey] = nums
        winners = []
        for t in self.data["tickets"].values():
            if t["status"] != "active":
                continue
            touched = False
            for ln in t["lines"]:
                same_sess = (ln.get("session") or None) == (session or None)
                if ln["game"] == game and ln["date"] == d and same_sess and not ln["settled"]:
                    ln["prize"], ln["settled"], touched = self._prize(ln, nums), True, True
            if touched and all(l["settled"] for l in t["lines"]):
                t["prize"] = round(sum(l["prize"] for l in t["lines"]), 2)
                t["status"] = "won" if t["prize"] > 0 else "lost"
                if t["prize"] > 0:
                    winners.append(t)
        self._save()
        self.hass.bus.async_fire(f"{DOMAIN}_results", {"game": game, "date": d, "numbers": nums, "session": session})
        for t in winners:
            self.hass.bus.async_fire(f"{DOMAIN}_winner", {"ticket_id": t["id"], "retailer_id": t["retailer_id"], "prize": t["prize"]})
        return [self.public(t) for t in winners]

    def draw_results(self, d: str) -> list[dict]:
        out = []
        for g in self.data["games"]:
            nums = self.data["results"].get(f"{g['id']}|{d}")
            if nums:
                out.append({"game": g["name"], "date": d, "numbers": nums})
        return out

    # ---------- reports ----------
    def report(self, date_from: str, date_to: str) -> dict:
        money = ("sales", "commission_sell", "commission_redeem", "commission", "prizes", "paid", "unpaid", "net")
        retailers = {r["id"]: r for r in self.data["retailers"]}
        rows = {r["id"]: {
            "retailer": r["name"], "number": r.get("number", ""),
            "commission_sell_pct": float(r.get("commission_sell", r.get("commission", 0))),
            "commission_redeem_pct": float(r.get("commission_redeem", 0)),
            "tickets": 0, "lines": 0,
            "sales": 0.0, "commission_sell": 0.0, "commission_redeem": 0.0, "commission": 0.0,
            "prizes": 0.0, "paid": 0.0, "unpaid": 0.0, "net": 0.0,
        } for r in self.data["retailers"]}
        games = {g["id"]: {"game": g["name"], "tickets": 0, "sales": 0.0, "prizes": 0.0, "net": 0.0} for g in self.data["games"]}
        bts = {b["key"]: b for b in self.data["bet_types"]}
        cancelled, exposure = 0, 0.0
        for t in self.data["tickets"].values():
            lines = [l for l in t["lines"] if date_from <= l["date"] <= date_to]
            if not lines:
                continue
            if t["status"] == "cancelled":
                cancelled += 1
                continue
            rid = t.get("retailer_id")
            if rid not in rows:
                continue
            row, seen = rows[rid], set()
            row["tickets"] += 1
            for l in lines:
                row["lines"] += 1
                row["sales"] += l["amount"]
                row["prizes"] += l["prize"]
                if l["prize"] > 0:
                    row["paid" if t["status"] == "redeemed" else "unpaid"] += l["prize"]
                g = games.get(l["game"])
                if g:
                    g["sales"] += l["amount"]
                    g["prizes"] += l["prize"]
                    if l["game"] not in seen:
                        g["tickets"] += 1
                        seen.add(l["game"])
                if not l["settled"] and l["bet_type"] in bts:
                    bt = bts[l["bet_type"]]
                    exposure += l["amount"] * bt["multiplier"] * (3 if bt["mode"] == "chances" else 1)
            # redeem commission credited to the shop that paid out
            if t["status"] == "redeemed" and t.get("prize"):
                pay_rid = t.get("redeemed_by") or rid
                if pay_rid in rows:
                    pct = rows[pay_rid]["commission_redeem_pct"]
                    rows[pay_rid]["commission_redeem"] += float(t["prize"]) * pct / 100
        totals = {"tickets": 0, "cancelled": cancelled, "lines": 0, "sales": 0.0,
                  "commission_sell": 0.0, "commission_redeem": 0.0, "commission": 0.0,
                  "prizes": 0.0, "paid": 0.0, "unpaid": 0.0, "net": 0.0, "exposure": round(exposure, 2)}
        for row in rows.values():
            row["commission_sell"] = row["sales"] * row["commission_sell_pct"] / 100
            row["commission"] = row["commission_sell"] + row["commission_redeem"]
            # operator view: sales out, commissions owed to retailer, prizes paid reduce net
            row["net"] = row["sales"] - row["commission"] - row["prizes"]
            for k in ("tickets", "lines") + money:
                totals[k] += row[k]
            for k in money:
                row[k] = round(row[k], 2)
        game_rows = []
        for g in games.values():
            if g["tickets"]:
                g["net"] = round(g["sales"] - g["prizes"], 2)
                g["sales"], g["prizes"] = round(g["sales"], 2), round(g["prizes"], 2)
                game_rows.append(g)
        return {"from": date_from, "to": date_to, "rows": list(rows.values()), "games": game_rows,
                "totals": {k: round(v, 2) if isinstance(v, float) else v for k, v in totals.items()}}

    def results_summary(self, date_from: str, date_to: str) -> dict:
        names = {g["id"]: g["name"] for g in self.data["games"]}
        retailers = {r["id"]: r["name"] for r in self.data["retailers"]}
        live = [t for t in self.data["tickets"].values() if t["status"] != "cancelled"]
        draws = []
        for key, nums in self.data["results"].items():
            gid, d = key.split("|")
            if not date_from <= d <= date_to:
                continue
            played, won, sales, prizes = set(), set(), 0.0, 0.0
            for t in live:
                for l in t["lines"]:
                    if l["game"] == gid and l["date"] == d:
                        played.add(t["id"])
                        sales += l["amount"]
                        if l["prize"] > 0:
                            won.add(t["id"])
                            prizes += l["prize"]
            draws.append({"game": gid, "game_name": names.get(gid, gid), "date": d, "numbers": nums, "tickets": len(played),
                          "sales": round(sales, 2), "winners": len(won), "prizes": round(prizes, 2)})
        draws.sort(key=lambda x: (x["date"], x["game_name"]), reverse=True)
        winners, paid, unpaid = [], 0.0, 0.0
        for t in live:
            wl = [l for l in t["lines"] if l["settled"] and l["prize"] > 0 and date_from <= l["date"] <= date_to]
            if not wl:
                continue
            prize = round(sum(l["prize"] for l in wl), 2)
            if t["status"] == "redeemed":
                paid += prize
            else:
                unpaid += prize
            winners.append({"id": t["id"], "retailer": retailers.get(t["retailer_id"], t["retailer_id"]), "prize": prize,
                            "status": t["status"], "lines": [{"game": names.get(l["game"], l["game"]), "date": l["date"],
                                                              "number": l["number"], "bet_type": l["bet_type"], "prize": l["prize"]} for l in wl]})
        winners.sort(key=lambda w: w["prize"], reverse=True)
        return {"draws": draws, "winners": winners, "totals": {"winners": len(winners), "prizes": round(paid + unpaid, 2),
                                                                "paid": round(paid, 2), "unpaid": round(unpaid, 2)}}

    def summary(self) -> dict:
        today = dt_util.now().date().isoformat()
        sales, count, liability = 0.0, 0, 0.0
        for t in self.data["tickets"].values():
            if t["status"] == "cancelled":
                continue
            if t["created"][:10] == today:
                sales, count = sales + t["total"], count + 1
            if t["status"] == "won":
                liability += t["prize"]
        return {"sales_today": round(sales, 2), "tickets_today": count, "unpaid_prizes": round(liability, 2)}

    # ---------- setup ----------
    def set_ticket_design(self, d: dict) -> dict:
        out = {}
        for k, default in TICKET_DEFAULTS.items():
            if k == "messages":
                continue
            v = d.get(k, default)
            try:
                if isinstance(default, bool):
                    out[k] = bool(v)
                elif isinstance(default, int):
                    out[k] = int(v)
                else:
                    out[k] = str(v if v is not None else default)
            except (TypeError, ValueError) as err:
                raise LotteryError(f"Invalid value for {k}") from err
        if out["font"] not in ("mono", "sans", "serif", "condensed") or out["align"] not in ("left", "center"):
            raise LotteryError("Invalid font or alignment")
        if not 8 <= out["size"] <= 20 or not 40 <= out["width"] <= 100 or not 12 <= out["qr_size"] <= 60:
            raise LotteryError("Size out of range")
        if not 20 <= out.get("logo_height", 40) <= 80:
            raise LotteryError("Logo height must be 20-80 px")
        out["header"] = out["header"][:120]
        out["footer"] = out["footer"][:200]
        out["qr_prefix"] = out["qr_prefix"][:40]
        out["jackpot_text"] = out.get("jackpot_text", "")[:160]
        out["jackpot_mode"] = out.get("jackpot_mode") if out.get("jackpot_mode") in ("auto", "manual") else "auto"
        out["jackpot_game"] = out.get("jackpot_game", "")[:40]
        # Ticket messages of the day (standard / dynamic / scheduled)
        msgs = d.get("messages", TICKET_DEFAULTS.get("messages", []))
        if not isinstance(msgs, list):
            raise LotteryError("messages must be a list")
        known_games = {g["id"] for g in self.data["games"]}
        cleaned = []
        for i, m in enumerate(msgs[:30]):
            if not isinstance(m, dict):
                continue
            text = str(m.get("text") or "").strip()[:400]
            if not text:
                continue
            mtype = str(m.get("type") or "standard")
            if mtype not in ("standard", "dynamic", "scheduled"):
                mtype = "standard"
            games = m.get("games") or []
            if not isinstance(games, list):
                games = []
            games = [str(g) for g in games if str(g) in known_games]
            cleaned.append({
                "id": str(m.get("id") or secrets.token_hex(4)),
                "type": mtype,
                "text": text,
                "enabled": bool(m.get("enabled", True)),
                "games": games,  # empty = all games on the ticket
                "start_at": str(m.get("start_at") or "")[:32] if mtype == "scheduled" else "",
                "end_at": str(m.get("end_at") or "")[:32] if mtype == "scheduled" else "",
            })
        out["messages"] = cleaned
        self.data["settings"]["ticket"] = out
        self._save()
        return out

    # ---------- promotions ----------
    def _find_promo(self, pid: str) -> dict:
        for p in self.data.get("promotions", []):
            if p["id"] == pid:
                return p
        raise LotteryError(f"Unknown promotion: {pid}")

    def _normalize_promo_fields(self, f: dict, existing: dict | None = None) -> dict:
        """Validate and normalise promotion fields for add/update."""
        out = dict(existing or {})
        if "name" in f or existing is None:
            name = str(f.get("name", out.get("name", ""))).strip()[:60]
            if not name:
                raise LotteryError("Promotion name is required")
            out["name"] = name
        if "trigger" in f or existing is None:
            trig = f.get("trigger", out.get("trigger", "min_plays"))
            if trig == "min_lines":
                trig = "min_plays"
            if trig not in ("min_plays", "min_games", "min_amount"):
                raise LotteryError("Trigger must be min_plays, min_games or min_amount")
            out["trigger"] = trig
        if "trigger_value" in f or existing is None:
            try:
                val = float(f.get("trigger_value", out.get("trigger_value", 3)))
            except (TypeError, ValueError) as err:
                raise LotteryError("Invalid trigger value") from err
            if out.get("trigger") == "min_amount":
                if not 0.01 <= val <= 1_000_000:
                    raise LotteryError("Amount must be between 0.01 and 1000000")
                out["trigger_value"] = round(val, 2)
            else:
                if not 1 <= val <= 50:
                    raise LotteryError("Trigger value must be 1-50")
                out["trigger_value"] = int(val)
        if "code_digits" in f or existing is None:
            try:
                digits = int(f.get("code_digits", out.get("code_digits", 6)))
            except (TypeError, ValueError) as err:
                raise LotteryError("Invalid code digits") from err
            if not 4 <= digits <= 10:
                raise LotteryError("Code digits must be 4-10")
            out["code_digits"] = digits
        if "games" in f or existing is None:
            games = f.get("games", out.get("games", [])) or []
            if not isinstance(games, list):
                raise LotteryError("Games must be a list of game ids")
            known = {g["id"] for g in self.data.get("games", [])}
            bad = [g for g in games if g not in known]
            if bad:
                raise LotteryError(f"Unknown game(s): {', '.join(bad)}")
            # unique preserve order
            seen = set()
            uniq = []
            for g in games:
                if g not in seen:
                    seen.add(g)
                    uniq.append(g)
            out["games"] = uniq
        if "label" in f or existing is None:
            out["label"] = str(f.get("label", out.get("label", "Qualified for promotion")))[:80]
        if "instruction" in f or existing is None:
            out["instruction"] = str(
                f.get("instruction", out.get("instruction", "Visit www.shocolottery.com and check if you have won"))
            )[:200]
        if "url" in f or existing is None:
            out["url"] = str(f.get("url", out.get("url", "https://www.shocolottery.com")))[:120]
        if "enabled" in f or existing is None:
            out["enabled"] = bool(f.get("enabled", out.get("enabled", True)))
        if "start_at" in f or existing is None:
            sa = str(f.get("start_at", out.get("start_at", "")) or "").strip()
            if sa:
                # Accept "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM"
                try:
                    if "T" in sa:
                        dt_util.parse_datetime(sa)
                    else:
                        _date.fromisoformat(sa)
                except (TypeError, ValueError) as err:
                    raise LotteryError("Invalid start date/time") from err
            out["start_at"] = sa
        if "end_at" in f or existing is None:
            ea = str(f.get("end_at", out.get("end_at", "")) or "").strip()
            if ea:
                try:
                    if "T" in ea:
                        dt_util.parse_datetime(ea)
                    else:
                        _date.fromisoformat(ea)
                except (TypeError, ValueError) as err:
                    raise LotteryError("Invalid end date/time") from err
            out["end_at"] = ea
        sa, ea = out.get("start_at") or "", out.get("end_at") or ""
        if sa and ea and sa > ea:
            raise LotteryError("Start must be before end")
        if "prizes" in f or existing is None:
            raw = f.get("prizes", out.get("prizes", [])) or []
            if not isinstance(raw, list):
                raise LotteryError("Prizes must be a list")
            cleaned = []
            for i, item in enumerate(raw):
                if not isinstance(item, dict):
                    raise LotteryError(f"Prize #{i+1} is invalid")
                label = str(item.get("label") or f"Prize {i+1}").strip()[:60]
                try:
                    amount = float(item.get("amount", 0))
                    qty = int(item.get("quantity", 1))
                except (TypeError, ValueError) as err:
                    raise LotteryError(f"Prize #{i+1} has invalid amount or quantity") from err
                if amount < 0 or amount > 1_000_000:
                    raise LotteryError(f"Prize #{i+1} amount must be 0–1000000")
                if not 1 <= qty <= 10_000:
                    raise LotteryError(f"Prize #{i+1} quantity must be 1–10000")
                cleaned.append({"label": label, "amount": round(amount, 2), "quantity": qty})
            out["prizes"] = cleaned
            # keep legacy single prize as max amount for display
            out["prize"] = max((x["amount"] for x in cleaned), default=0.0)
        elif "prize" in f or existing is None:
            try:
                prize = float(f.get("prize", out.get("prize", 0)))
            except (TypeError, ValueError) as err:
                raise LotteryError("Invalid prize amount") from err
            if prize < 0 or prize > 1_000_000:
                raise LotteryError("Prize must be between 0 and 1000000")
            out["prize"] = round(prize, 2)
            if not out.get("prizes") and prize > 0:
                out["prizes"] = [{"label": "Winner prize", "amount": out["prize"], "quantity": 1}]
        return out

    def add_promotion(self, fields: dict) -> dict:
        fields = self._normalize_promo_fields(fields, None)
        base = "".join(c if c.isalnum() else "_" for c in fields["name"].lower()).strip("_") or secrets.token_hex(3)
        pid = base
        if any(p["id"] == pid for p in self.data.get("promotions", [])):
            pid = f"{pid}_{secrets.token_hex(2)}"
        p = {"id": pid, **fields}
        self.data.setdefault("promotions", []).append(p)
        self._save()
        return p

    def update_promotion(self, pid: str, f: dict) -> dict:
        p = self._find_promo(pid)
        updated = self._normalize_promo_fields(f, p)
        p.clear()
        p.update({"id": pid, **updated})
        self._save()
        return p

    def delete_promotion(self, pid: str) -> None:
        self._find_promo(pid)
        self.data["promotions"] = [x for x in self.data["promotions"] if x["id"] != pid]
        self._save()

    def check_promo_code(self, code: str) -> dict:
        """Public lookup: has this promotion code won a prize?"""
        code = str(code or "").strip()
        if not code or not code.isdigit():
            raise LotteryError("Enter a valid promotion code")
        codes = self.data.get("promo_codes") or {}
        entry = codes.get(code)
        if not entry:
            # also accept codes still only on tickets (legacy)
            for t in self.data.get("tickets", {}).values():
                for pr in t.get("promotions") or []:
                    if str(pr.get("code")) == code:
                        entry = {
                            "code": code,
                            "promotion_id": str(pr.get("id", "")),
                            "promotion_name": pr.get("name", "Promotion"),
                            "status": "pending",
                            "prize_label": "",
                            "prize_amount": float(pr.get("prize") or 0),
                            "claimed": False,
                        }
                        break
                if entry:
                    break
        if not entry:
            raise LotteryError("Code not found — check the number on your ticket")
        status = entry.get("status") or "pending"
        amount = float(entry.get("prize_amount") or 0)
        label = entry.get("prize_label") or ""
        cur = self.data.get("currency", "")
        if status == "won" and amount > 0:
            return {
                "found": True,
                "status": "won",
                "code": code,
                "promotion": entry.get("promotion_name", "Promotion"),
                "message": "Congratulations! You won!",
                "prize_label": label or "Prize",
                "prize_amount": amount,
                "currency": cur,
                "claimed": bool(entry.get("claimed")),
            }
        if status == "lost":
            return {
                "found": True,
                "status": "lost",
                "code": code,
                "promotion": entry.get("promotion_name", "Promotion"),
                "message": "This code did not win a prize. Thank you for playing!",
                "prize_label": "",
                "prize_amount": 0,
                "currency": cur,
                "claimed": False,
            }
        # pending — draw not run yet, or qualified only
        return {
            "found": True,
            "status": "pending",
            "code": code,
            "promotion": entry.get("promotion_name", "Promotion"),
            "message": "You qualified! Winners are not drawn yet — check back later.",
            "prize_label": "",
            "prize_amount": 0,
            "currency": cur,
            "claimed": False,
        }

    def draw_promo_winners(self, pid: str) -> dict:
        """Randomly assign prize slots to pending codes for a promotion."""
        promo = self._find_promo(pid)
        prizes = promo.get("prizes") or []
        if not prizes and float(promo.get("prize") or 0) > 0:
            prizes = [{"label": "Winner prize", "amount": float(promo["prize"]), "quantity": 1}]
        if not prizes:
            raise LotteryError("Add at least one prize before drawing winners")
        codes = self.data.setdefault("promo_codes", {})
        pending = [c for c in codes.values()
                   if c.get("promotion_id") == str(pid) and c.get("status") == "pending"]
        if not pending:
            raise LotteryError("No pending codes for this promotion")
        # Build slot list
        slots = []
        for pr in prizes:
            for _ in range(int(pr.get("quantity") or 1)):
                slots.append({"label": pr.get("label") or "Prize", "amount": float(pr.get("amount") or 0)})
        # Shuffle and assign
        import random
        random.shuffle(pending)
        random.shuffle(slots)
        won, assigned = 0, 0
        for i, entry in enumerate(pending):
            if i < len(slots):
                slot = slots[i]
                entry["status"] = "won"
                entry["prize_label"] = slot["label"]
                entry["prize_amount"] = slot["amount"]
                won += 1
            else:
                entry["status"] = "lost"
                entry["prize_label"] = ""
                entry["prize_amount"] = 0.0
            assigned += 1
        self._save()
        return {"assigned": assigned, "winners": won, "prizes": len(slots), "pending_before": len(pending)}

    def promo_codes_summary(self, pid: str | None = None) -> dict:
        codes = list((self.data.get("promo_codes") or {}).values())
        if pid:
            codes = [c for c in codes if c.get("promotion_id") == str(pid)]
        return {
            "total": len(codes),
            "pending": sum(1 for c in codes if c.get("status") == "pending"),
            "won": sum(1 for c in codes if c.get("status") == "won"),
            "lost": sum(1 for c in codes if c.get("status") == "lost"),
        }



    def _normalize_retailer_fields(self, f: dict, existing: dict | None = None) -> dict:
        out = dict(existing or {})
        name = str(f.get("name", out.get("name", ""))).strip()[:80]
        if not name:
            raise LotteryError("Shop / retailer name is required")
        out["name"] = name
        number = str(f.get("number", out.get("number", ""))).strip()[:20]
        out["number"] = number
        out["first_name"] = str(f.get("first_name", out.get("first_name", ""))).strip()[:60]
        out["last_name"] = str(f.get("last_name", out.get("last_name", ""))).strip()[:60]
        out["address"] = str(f.get("address", out.get("address", ""))).strip()[:200]
        out["phone"] = str(f.get("phone", out.get("phone", ""))).strip()[:40]
        try:
            cs = float(f.get("commission_sell", f.get("commission", out.get("commission_sell", out.get("commission", 10)))))
            cr = float(f.get("commission_redeem", out.get("commission_redeem", 0)))
        except (TypeError, ValueError) as err:
            raise LotteryError("Invalid commission") from err
        if not 0 <= cs <= 100 or not 0 <= cr <= 100:
            raise LotteryError("Commission must be 0–100%")
        out["commission_sell"] = round(cs, 2)
        out["commission_redeem"] = round(cr, 2)
        out["commission"] = out["commission_sell"]  # legacy field
        out["active"] = bool(f.get("active", out.get("active", True)))
        return out

    def update_retailer(self, rid: str, fields: dict) -> dict:
        r = self._find("retailers", "id", rid, "retailer")
        updated = self._normalize_retailer_fields(fields, r)
        # unique retailer number if set
        num = updated.get("number") or ""
        if num and any(x.get("number") == num and x["id"] != rid for x in self.data["retailers"]):
            raise LotteryError(f"Retailer number {num} already in use")
        r.clear()
        r.update({"id": rid, **updated})
        self._save()
        return r

    def set_branding(self, name: str, logo: str) -> dict:
        name = name.strip()[:40]
        if not name:
            raise LotteryError("Enter a lottery name")
        if logo and not (logo.startswith("data:image/") or logo.startswith("/local/")):
            raise LotteryError("Logo must be an uploaded image or a /local/ path")
        if len(logo) > 300_000:
            raise LotteryError("Logo image is too large")
        self.data["settings"].update({"name": name, "logo": logo})
        self._save()
        return self.data["settings"]

    def add_retailer(self, fields: dict) -> dict:
        fields = self._normalize_retailer_fields(fields, None)
        base = re.sub(r"\W+", "_", fields["name"].lower()).strip("_") or secrets.token_hex(3)
        rid = base
        if any(r["id"] == rid for r in self.data["retailers"]):
            rid = f"{base}_{secrets.token_hex(2)}"
        num = fields.get("number") or ""
        if not num:
            # auto number: next sequential
            existing = [r.get("number", "") for r in self.data["retailers"]]
            n = 1
            while f"{n:03d}" in existing:
                n += 1
            fields["number"] = f"{n:03d}"
        elif any(r.get("number") == num for r in self.data["retailers"]):
            raise LotteryError(f"Retailer number {num} already in use")
        r = {"id": rid, **fields}
        self.data["retailers"].append(r)
        self._save()
        return r

    def set_ticker(self, text: str, enabled: bool, speed: int, color: str) -> dict:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise LotteryError("Invalid color")
        self.data["settings"]["ticker"] = {"text": text.strip()[:200], "enabled": bool(enabled),
                                           "speed": max(1, min(10, int(speed))), "color": color}
        self._save()
        return self.data["settings"]["ticker"]


    # ---------- external results scrape (indioslottery.com) ----------
    INDIOS_SUPABASE = "https://sswbmocnjkuwoyqqpgsk.supabase.co"
    INDIOS_ANON_KEY = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNzd2Jtb2Nuamt1d295cXFwZ3NrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU2NTQ5NjMsImV4cCI6MjA3MTIzMDk2M30."
        "PSZMQgLihW_ZnEaW9ynCINWvvFl9skaOwWW92TWHzL8"
    )
    # site game_code → possible local game name/id fragments
    INDIOS_ALIASES = {
        "DIARIO": ["diario"],
        "CORSOW": ["corsow", "korsow", "korsou", "wnk"],
        "KORSOW": ["corsow", "korsow", "korsou", "wnk"],
        "FLAMINGO": ["flamingo"],
        "SUPER4": ["super4", "super 4", "super-4"],
        "PHILIPSBURG_AM": ["philipsburg am", "philb_am", "philb am", "phlp am"],
        "PHILIPSBURG_PM": ["philipsburg pm", "philb_pm", "philb pm", "phlp pm", "philipsburg evening"],
        "BIG4": ["big 4", "big4"],
        "CATOCHI": ["catochi"],
        "LUCKY3": ["lucky 3", "lucky3"],
        "ONEOFF": ["1 off", "1-off", "oneoff", "one off"],
        "ZODIAC": ["zodiac"],
        "LOTTO_DIA": ["lotto di dia", "lottodidia", "lotto dia"],
        "LOTTO5": ["lotto 5", "lotto5"],
        "MINI_MEGA": ["mini mega", "minimega"],
        "MINIMEGA": ["mini mega", "minimega"],
        "MEGAPLUS": ["mega plus", "megaplus"],
        "MEGA_PLUS": ["mega plus", "megaplus"],
    }

    def _indios_fetch(self, path: str) -> list:
        url = f"{self.INDIOS_SUPABASE}/rest/v1/{path}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "LotteryPOS/1.0",
                "apikey": self.INDIOS_ANON_KEY,
                "Authorization": f"Bearer {self.INDIOS_ANON_KEY}",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        return data if isinstance(data, list) else []

    def _match_local_game(self, code: str, period: str | None = None):
        """Match Indios game_code (+ optional midday/evening) to a local game."""
        code_u = (code or "").upper().strip()
        aliases = list(self.INDIOS_ALIASES.get(code_u, []))
        aliases.append(code_u.lower().replace("_", " "))
        aliases.append(code_u.lower().replace("_", ""))
        if period:
            p = period.lower()
            extra = []
            for a in aliases:
                if p in ("midday", "merdia"):
                    extra += [f"{a} merdia", f"{a} midday", f"{a} am"]
                elif p in ("evening", "anochi"):
                    extra += [f"{a} anochi", f"{a} evening", f"{a} pm"]
            aliases = extra + aliases
        # exact id / name
        for g in self.data["games"]:
            gname = g["name"].lower().strip()
            gid = g["id"].lower().strip()
            for a in aliases:
                a = a.lower()
                if gid == a or gname == a or a in gname or gname in a:
                    return g
        return None

    def _nums_from_indios_row(self, row: dict, period_style: bool) -> tuple[str, list[str]]:
        """Return (draw_date, numbers list) from a Supabase row."""
        draw_date = str(row.get("draw_date") or dt_util.now().date().isoformat())[:10]
        if not period_style:
            # v_our_latest: first/second/third/skina
            nums = []
            for k in ("first_prize", "second_prize", "third_prize", "skina4_prize"):
                v = row.get(k)
                if v is None or v == "":
                    continue
                s = str(v).strip()
                if s.isdigit():
                    nums.append(s.zfill(4) if len(s) <= 4 else s)
            return draw_date, nums
        # v_lotto_latest
        raw = row.get("numbers")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                raw = []
        if not isinstance(raw, list):
            raw = []
        extra = row.get("extra") or {}
        if isinstance(extra, str):
            try:
                extra = json.loads(extra)
            except Exception:
                extra = {}
        code = str(row.get("game_code") or "").upper()
        nums: list[str] = []
        if code in ("LOTTO_DIA", "LOTTO5", "MINI_MEGA", "MINIMEGA"):
            for x in raw:
                s = str(x).strip()
                if s.isdigit():
                    nums.append(s.zfill(2))
            joker = extra.get("joker") or extra.get("mega") or extra.get("mega_ball")
            if joker is not None and str(joker).strip() != "":
                nums.append(str(joker).strip().zfill(2))
        elif code == "ZODIAC":
            # digits + sign
            digits = "".join(str(x) for x in raw)
            nums.append(digits)
            sign = str(extra.get("sign") or "").lower().strip()
            # map spanish/english signs to our zodiac ids when possible
            sign_map = {
                "aries": "aries", "tauro": "taurus", "taurus": "taurus",
                "geminis": "gemini", "gemini": "gemini", "cancer": "cancer",
                "leo": "leo", "virgo": "virgo", "libra": "libra",
                "escorpio": "scorpio", "scorpio": "scorpio",
                "sagitario": "sagittarius", "sagittarius": "sagittarius",
                "capricornio": "capricorn", "capricorn": "capricorn",
                "acuario": "aquarius", "aquarius": "aquarius",
                "piscis": "pisces", "pisces": "pisces",
                "rat": "rat", "ox": "ox", "tiger": "tiger", "rabbit": "rabbit",
                "dragon": "dragon", "snake": "snake", "horse": "horse",
                "goat": "goat", "monkey": "monkey", "rooster": "rooster",
                "dog": "dog", "pig": "pig",
            }
            if sign:
                nums.append(sign_map.get(sign, sign))
        else:
            # digit games: join into one number string(s)
            if all(str(x).isdigit() and len(str(x)) == 1 for x in raw):
                nums.append("".join(str(x) for x in raw))
            else:
                for x in raw:
                    s = str(x).strip()
                    if s:
                        nums.append(s)
        return draw_date, nums

    def scrape_indios(self, url: str = "https://indioslottery.com/") -> dict:
        """Pull latest results from indioslottery.com (Supabase public API) and settle matching games."""
        imported, skipped, winners_all = [], [], []
        try:
            our = self._indios_fetch("v_our_latest?select=*")
            midday = self._indios_fetch("v_lotto_latest?select=*&period=eq.midday")
            evening = self._indios_fetch("v_lotto_latest?select=*&period=eq.evening")
        except Exception as err:
            raise LotteryError(f"Could not fetch Indios results: {err}") from err

        rows = []
        for r in our:
            rows.append((r, False, None))
        for r in midday:
            rows.append((r, True, "midday"))
        for r in evening:
            rows.append((r, True, "evening"))

        dates = set()
        for row, period_style, period in rows:
            code = str(row.get("game_code") or "").strip()
            if not code:
                skipped.append({"name": "?", "reason": "missing game_code"})
                continue
            label = code + (f" ({period})" if period else "")
            draw_date, nums = self._nums_from_indios_row(row, period_style)
            if not nums:
                skipped.append({"name": label, "reason": "no numbers"})
                continue
            game = self._match_local_game(code, period)
            if not game:
                skipped.append({"name": label, "reason": "no matching local game"})
                continue
            try:
                winners = self.set_results(game["id"], draw_date, nums)
            except LotteryError as err:
                skipped.append({"name": label, "reason": str(err)})
                continue
            dates.add(draw_date)
            imported.append({
                "game": game["name"], "game_id": game["id"], "date": draw_date,
                "numbers": nums, "winners": len(winners), "source_code": code,
            })
            winners_all.extend(winners)

        # also try to update jackpot pools from extra.jackpot when present
        for row, period_style, period in rows:
            if not period_style:
                continue
            extra = row.get("extra") or {}
            if isinstance(extra, str):
                try:
                    extra = json.loads(extra)
                except Exception:
                    extra = {}
            jp = extra.get("jackpot")
            if not jp:
                continue
            game = self._match_local_game(str(row.get("game_code") or ""), period)
            if not game or game.get("format") != "jackpot":
                continue
            try:
                # European-style thousand separator: 450.000 → 450000
                val = float(str(jp).replace(".", "").replace(",", ""))
                game["jackpot_current"] = val
            except (TypeError, ValueError):
                pass
        if any(r[1] for r in rows):
            self._save()

        return {
            "source": url or "https://indioslottery.com/",
            "date": sorted(dates)[-1] if dates else dt_util.now().date().isoformat(),
            "imported": imported,
            "skipped": skipped,
            "winners": [self.public(w) if isinstance(w, dict) and "id" in w else w for w in winners_all],
        }

    # backward-compatible alias
    def scrape_joeblack(self, url: str = "https://indioslottery.com/") -> dict:
        return self.scrape_indios(url)


    def update_game(self, gid: str, f: dict) -> dict:
        g = self._find("games", "id", gid, "game")
        new = dict(g)
        for k in ("name", "color", "draw_time", "open_time", "cutoff", "logo"):
            if k in f and f[k] is not None:
                new[k] = f[k]
        if "enabled" in f:
            new["enabled"] = bool(f["enabled"])
        if "bet_types" in f:
            keys = {b["key"] for b in self.data["bet_types"]}
            if any(k not in keys for k in f["bet_types"]):
                raise LotteryError("Unknown bet type")
            new["bet_types"] = list(f["bet_types"])
        if "draw_days" in f:
            days = [int(x) for x in f["draw_days"]]
            if any(d < 0 or d > 6 for d in days):
                raise LotteryError("Draw days must be 0–6")
            new["draw_days"] = days
        if "format" in f:
            fmt = str(f["format"])
            if fmt not in ("digit", "zodiac", "jackpot", "whe"):
                raise LotteryError("Format must be digit, zodiac, jackpot or whe")
            new["format"] = fmt
        if "digits" in f:
            dig = int(f["digits"])
            if not 1 <= dig <= 6:
                raise LotteryError("Digits must be 1–6")
            new["digits"] = dig
        for k, lo, hi in (("main_count", 1, 10), ("main_max", 5, 99), ("mega_max", 1, 99)):
            if k in f:
                v = int(f[k])
                if not lo <= v <= hi:
                    raise LotteryError(f"{k} must be {lo}–{hi}")
                new[k] = v
        if "mega_count" in f:
            mc = int(f["mega_count"])
            if mc not in (0, 1):
                raise LotteryError("mega_count must be 0 or 1")
            new["mega_count"] = mc
        if "symbols" in f:
            known = {z["id"] for z in ZODIAC_SYMBOLS}
            syms = list(f["symbols"] or [])
            bad = [s for s in syms if s not in known]
            if bad:
                raise LotteryError(f"Unknown symbols: {', '.join(bad)}")
            new["symbols"] = syms or [z["id"] for z in ZODIAC_SYMBOLS]
        if "sessions" in f:
            raw = f.get("sessions") or []
            if not isinstance(raw, list):
                raise LotteryError("sessions must be a list")
            cleaned = []
            seen_ids = set()
            for i, s in enumerate(raw):
                if not isinstance(s, dict):
                    raise LotteryError(f"Session #{i+1} invalid")
                sid = str(s.get("id") or "").strip().lower().replace(" ", "_")
                if not sid or sid in seen_ids:
                    raise LotteryError(f"Session #{i+1} needs a unique id")
                seen_ids.add(sid)
                label = str(s.get("label") or sid).strip()
                dt = str(s.get("draw_time") or "12:00").strip()
                cut = str(s.get("cutoff") or dt).strip()
                cleaned.append({"id": sid, "label": label, "draw_time": dt, "cutoff": cut})
            new["sessions"] = cleaned
            if cleaned:
                # keep top-level draw_time/cutoff as first session for compatibility
                new["draw_time"] = cleaned[0]["draw_time"]
                new["cutoff"] = cleaned[0]["cutoff"]
        for k in ("min_stake", "max_stake", "jackpot_min", "jackpot_current", "jackpot_contrib"):
            if k in f:
                try:
                    v = float(f[k])
                except (TypeError, ValueError) as err:
                    raise LotteryError(f"Invalid {k}") from err
                if v < 0:
                    raise LotteryError(f"{k} must be ≥ 0")
                new[k] = round(v, 2)
        if "min_stake" in new and "max_stake" in new and new["max_stake"] < new["min_stake"]:
            raise LotteryError("max_stake must be ≥ min_stake")
        if "fixed_prices" in f:
            prices = []
            for x in f.get("fixed_prices") or []:
                try:
                    v = float(x)
                except (TypeError, ValueError):
                    continue
                if v > 0:
                    prices.append(round(v, 2))
            new["fixed_prices"] = sorted(set(prices)) or [2.0, 3.0, 4.0, 5.0]
        if "jackpot_prizes" in f:
            raw = f.get("jackpot_prizes") or []
            if not isinstance(raw, list):
                raise LotteryError("jackpot_prizes must be a list")
            cleaned = []
            mc = int(new.get("main_count") or 5)
            for i, pr in enumerate(raw):
                if not isinstance(pr, dict):
                    raise LotteryError(f"Prize tier #{i+1} invalid")
                match = int(pr.get("match") or 0)
                if not 1 <= match <= mc:
                    raise LotteryError(f"Prize match must be 1–{mc} (main balls)")
                ptype = str(pr.get("prize_type") or "fixed")
                if ptype not in ("jackpot", "fixed", "multiplier"):
                    raise LotteryError("prize_type must be jackpot, fixed or multiplier")
                try:
                    amount = float(pr.get("amount") or 0)
                except (TypeError, ValueError) as err:
                    raise LotteryError("Invalid prize amount") from err
                cleaned.append({
                    "match": match,
                    "mega": bool(pr.get("mega")),
                    "prize_type": ptype,
                    "amount": round(amount, 2),
                })
            new["jackpot_prizes"] = cleaned
        g.clear()
        g.update(new)
        self._save()
        return g


    def delete_game(self, gid: str) -> None:
        g = self._find("games", "id", gid, "game")
        if any(l["game"] == gid for t in self.data["tickets"].values() for l in t["lines"]):
            raise LotteryError("This game has sales history - hide it instead")
        self.data["games"].remove(g)
        self._save()

    def update_bet_type(self, key: str, fields: dict) -> dict:
        b = self._find("bet_types", "key", key, "bet type")
        label = str(fields.get("label", b.get("label", ""))).strip()
        try:
            multiplier = float(fields.get("multiplier", b.get("multiplier", 1)))
            min_stake = float(fields.get("min_stake", b.get("min_stake", 0.5)))
            max_stake = float(fields.get("max_stake", b.get("max_stake", 100)))
        except (TypeError, ValueError) as err:
            raise LotteryError("Invalid payout or stake") from err
        if not label or multiplier <= 0:
            raise LotteryError("Label required and payout must be > 0")
        if min_stake < 0 or max_stake < min_stake:
            raise LotteryError("Stake range invalid (min ≤ max)")
        b.update({
            "label": label[:40],
            "multiplier": multiplier,
            "min_stake": round(min_stake, 2),
            "max_stake": round(max_stake, 2),
            "enabled": bool(fields.get("enabled", b.get("enabled", True))),
        })
        self._save()
        return b

    def add_game(self, fields: dict) -> dict:
        name = str(fields.get("name", "")).strip()
        if not name:
            raise LotteryError("Game name is required")
        gid = re.sub(r"\W+", "_", name.lower()).strip("_") or secrets.token_hex(3)
        if any(g["id"] == gid for g in self.data["games"]):
            raise LotteryError("Game already exists")
        g = {
            "id": gid,
            "name": name[:40],
            "color": str(fields.get("color") or "#64748b"),
            "draw_time": str(fields.get("draw_time") or "12:00"),
            "cutoff": str(fields.get("cutoff") or "11:45"),
            "open_time": str(fields.get("open_time") or "00:00"),
            "logo": str(fields.get("logo") or ""),
            "enabled": True,
            "bet_types": list(fields.get("bet_types") or []),
            "draw_days": list(fields.get("draw_days") or []),
            "format": str(fields.get("format") or "digit"),
            "digits": int(fields.get("digits") or 4),
            "main_count": int(fields.get("main_count") or 5),
            "main_max": int(fields.get("main_max") or 30),
            "mega_count": int(fields.get("mega_count") or 0),
            "mega_max": int(fields.get("mega_max") or 15),
            "symbols": list(fields.get("symbols") or [z["id"] for z in ZODIAC_SYMBOLS]),
            "min_stake": float(fields.get("min_stake") or 0.5),
            "max_stake": float(fields.get("max_stake") or 100),
            "jackpot_min": float(fields.get("jackpot_min") or 10000),
            "jackpot_current": float(fields.get("jackpot_current") or fields.get("jackpot_min") or 10000),
            "jackpot_contrib": float(fields.get("jackpot_contrib") or 0.2),
            "jackpot_prizes": list(fields.get("jackpot_prizes") or []),
            "fixed_prices": list(fields.get("fixed_prices") or [2, 3, 4, 5]),
        }
        if g["format"] not in ("digit", "zodiac", "jackpot"):
            raise LotteryError("Format must be digit, zodiac or jackpot")
        if not 1 <= g["digits"] <= 6:
            raise LotteryError("Digits must be 1–6")
        if not 1 <= g["main_count"] <= 10 or not 5 <= g["main_max"] <= 99:
            raise LotteryError("Invalid jackpot main ball settings")
        if g["mega_count"] not in (0, 1) or not 1 <= g["mega_max"] <= 99:
            raise LotteryError("Invalid mega ball settings")
        self.data["games"].append(g)
        self._save()
        return g
