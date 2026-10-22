"""Persistent data + business logic (sales, results, settlement)."""
from __future__ import annotations

import calendar
import copy
import re
import secrets
from datetime import date as _date

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (DEFAULT_BET_TYPES, DEFAULT_GAMES, DEFAULT_PROMOTIONS, DOMAIN,
                    SIGNAL_UPDATE, STORAGE_KEY, STORAGE_VERSION, TICKET_DEFAULTS)


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
                "retailers": [{"id": "main", "name": "Main Shop", "commission": 10.0, "active": True}],
                "tickets": {}, "results": {}, "seq": 0,
                "promotions": copy.deepcopy(DEFAULT_PROMOTIONS),
            }
        data["currency"] = currency
        data.setdefault("settings", {"name": "Lottery POS", "logo": ""})
        data["settings"].setdefault("ticker", {"enabled": True, "text": "Welcome! Play responsibly - good luck to all our players!", "speed": 5, "color": "#39ff14"})
        data["settings"]["ticket"] = {**TICKET_DEFAULTS, **data["settings"].get("ticket", {})}
        data.setdefault("promotions", copy.deepcopy(DEFAULT_PROMOTIONS))
        for g in data["games"]:
            g.setdefault("open_time", "00:00")
            g.setdefault("enabled", True)
            g.setdefault("bet_types", [])
            g.setdefault("draw_days", [])
        for b in data["bet_types"]:
            b.setdefault("enabled", True)
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
        self.data = data
        self._save()

    def _save(self) -> None:
        self._store.async_delay_save(lambda: self.data, 1)
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)

    def _find(self, coll: str, key: str, val: str, label: str) -> dict:
        for item in self.data[coll]:
            if item[key] == val:
                return item
        raise LotteryError(f"Unknown {label}: {val}")

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
        return line["date"] < today or (line["date"] == today and now.strftime("%H:%M") >= game["cutoff"])

    def sell(self, retailer_id: str, lines: list[dict]) -> dict:
        if not lines:
            raise LotteryError("Ticket is empty")
        retailer = self._find("retailers", "id", retailer_id, "retailer")
        if not retailer.get("active", True):
            raise LotteryError("Retailer is disabled")
        clean = []
        for ln in lines:
            game = self._find("games", "id", ln["game"], "game")
            bt = self._find("bet_types", "key", ln["bet_type"], "bet type")
            if not game.get("enabled", True):
                raise LotteryError(f"{game['name']} is not on sale")
            allowed = game.get("bet_types") or []
            if not bt.get("enabled", True) or (allowed and bt["key"] not in allowed):
                raise LotteryError(f"{bt['label']} is not available for {game['name']}")
            num, amt = str(ln["number"]), round(float(ln["amount"]), 2)
            if not (num.isdigit() and len(num) == bt["digits"]):
                raise LotteryError(f"{bt['label']} needs {bt['digits']} digits")
            if amt <= 0:
                raise LotteryError("Amount must be above 0")
            line = {"game": game["id"], "bet_type": bt["key"], "number": num, "amount": amt,
                    "date": ln["date"], "prize": 0.0, "settled": False}
            try:
                wd = _date.fromisoformat(line["date"]).weekday()
            except ValueError as err:
                raise LotteryError("Invalid draw date") from err
            if game.get("draw_days") and wd not in game["draw_days"]:
                raise LotteryError(f"{game['name']} has no draw on {calendar.day_name[wd]}")
            if self._closed(line):
                raise LotteryError(f"{game['name']} is closed for {line['date']}")
            if line["date"] == dt_util.now().date().isoformat() and dt_util.now().strftime("%H:%M") < game["open_time"]:
                raise LotteryError(f"{game['name']} opens at {game['open_time']}")
            if f"{game['id']}|{line['date']}" in self.data["results"]:
                raise LotteryError(f"{game['name']} {line['date']} already drawn")
            clean.append(line)
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

    def _apply_promotions(self, lines: list[dict]) -> list[dict]:
        awarded = []
        for p in self.data.get("promotions", []):
            if not p.get("enabled", True):
                continue
            try:
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
                code = f"{secrets.randbelow(10 ** digits):0{digits}d}"
                awarded.append({
                    "id": p["id"], "name": p.get("name", "Promotion"), "code": code,
                    "label": p.get("label", "Qualified for promotion"),
                    "instruction": p.get("instruction", "Visit www.shocolottery.com and check if you have won"),
                    "url": p.get("url", "https://www.shocolottery.com"),
                })
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

    def redeem(self, tid: str) -> dict:
        t = self.ticket(tid)
        if t["status"] == "redeemed":
            raise LotteryError("Already paid")
        if t["status"] != "won":
            raise LotteryError("Not a winning ticket" if t["status"] == "lost" else f"Ticket is {t['status']} (draw pending)")
        t["status"], t["redeemed_at"] = "redeemed", dt_util.now().isoformat()
        self._save()
        return self.public(t)

    def _prize(self, ln: dict, nums: list[str]) -> float:
        bt = self._find("bet_types", "key", ln["bet_type"], "bet type")
        n, first, mode, d = ln["number"], nums[0], bt["mode"], bt["digits"]
        if mode == "exact":
            hits = n == first[-d:]
        elif mode == "perm":
            hits = sorted(n) == sorted(first[-d:])
        elif mode == "bf":
            hits = n in (first[:2], first[-2:])
        elif mode == "back":
            hits = n == first[-2:]
        else:
            hits = sum(1 for x in nums if x[-2:] == n)
        return round(ln["amount"] * bt["multiplier"] * int(hits), 2)

    def set_results(self, game: str, d: str, numbers: list[str]) -> list[dict]:
        self._find("games", "id", game, "game")
        nums = [str(n).strip() for n in numbers if str(n).strip()]
        if not nums or any(not (n.isdigit() and len(n) == 4) for n in nums):
            raise LotteryError("Results must be 4-digit numbers (1st, 2nd, 3rd prize)")
        self.data["results"][f"{game}|{d}"] = nums
        winners = []
        for t in self.data["tickets"].values():
            if t["status"] != "active":
                continue
            touched = False
            for ln in t["lines"]:
                if ln["game"] == game and ln["date"] == d and not ln["settled"]:
                    ln["prize"], ln["settled"], touched = self._prize(ln, nums), True, True
            if touched and all(l["settled"] for l in t["lines"]):
                t["prize"] = round(sum(l["prize"] for l in t["lines"]), 2)
                t["status"] = "won" if t["prize"] > 0 else "lost"
                if t["prize"] > 0:
                    winners.append(t)
        self._save()
        self.hass.bus.async_fire(f"{DOMAIN}_results", {"game": game, "date": d, "numbers": nums})
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

    def report(self, date_from: str, date_to: str) -> dict:
        money = ("sales", "commission", "prizes", "paid", "unpaid", "net")
        rows = {r["id"]: {"retailer": r["name"], "commission_pct": r["commission"], "tickets": 0, "lines": 0,
                          "sales": 0.0, "commission": 0.0, "prizes": 0.0, "paid": 0.0, "unpaid": 0.0, "net": 0.0}
                for r in self.data["retailers"]}
        games = {g["id"]: {"game": g["name"], "tickets": 0, "sales": 0.0, "prizes": 0.0, "net": 0.0} for g in self.data["games"]}
        bts = {b["key"]: b for b in self.data["bet_types"]}
        cancelled, exposure = 0, 0.0
        for t in self.data["tickets"].values():
            lines = [l for l in t["lines"] if date_from <= l["date"] <= date_to]
            if not lines or t["retailer_id"] not in rows:
                continue
            if t["status"] == "cancelled":
                cancelled += 1
                continue
            row, seen = rows[t["retailer_id"]], set()
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
        totals = {"tickets": 0, "cancelled": cancelled, "lines": 0, "sales": 0.0, "commission": 0.0, "prizes": 0.0,
                  "paid": 0.0, "unpaid": 0.0, "net": 0.0, "exposure": round(exposure, 2)}
        for row in rows.values():
            row["commission"] = row["sales"] * row["commission_pct"] / 100
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

    def set_ticket_design(self, d: dict) -> dict:
        out = {}
        for k, default in TICKET_DEFAULTS.items():
            v = d.get(k, default)
            try:
                out[k] = bool(v) if isinstance(default, bool) else int(v) if isinstance(default, int) else str(v)
            except (TypeError, ValueError) as err:
                raise LotteryError(f"Invalid value for {k}") from err
        if out["font"] not in ("mono", "sans", "serif", "condensed") or out["align"] not in ("left", "center"):
            raise LotteryError("Invalid font or alignment")
        if not 8 <= out["size"] <= 20 or not 40 <= out["width"] <= 100 or not 12 <= out["qr_size"] <= 60:
            raise LotteryError("Size out of range")
        if not 20 <= out.get("logo_height", 40) <= 80:
            raise LotteryError("Logo height must be 20-80 px")
        out["header"], out["footer"], out["qr_prefix"] = out["header"][:120], out["footer"][:200], out["qr_prefix"][:40]
        self.data["settings"]["ticket"] = out
        self._save()
        return out

    def _find_promo(self, pid: str) -> dict:
        for p in self.data.get("promotions", []):
            if p["id"] == pid:
                return p
        raise LotteryError(f"Unknown promotion: {pid}")

    def _normalize_promo_fields(self, f: dict, existing: dict | None = None) -> dict:
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
            seen, uniq = set(), []
            for g in games:
                if g not in seen:
                    seen.add(g)
                    uniq.append(g)
            out["games"] = uniq
        if "label" in f or existing is None:
            out["label"] = str(f.get("label", out.get("label", "Qualified for promotion")))[:80]
        if "instruction" in f or existing is None:
            out["instruction"] = str(f.get("instruction", out.get("instruction", "Visit www.shocolottery.com and check if you have won")))[:200]
        if "url" in f or existing is None:
            out["url"] = str(f.get("url", out.get("url", "https://www.shocolottery.com")))[:120]
        if "enabled" in f or existing is None:
            out["enabled"] = bool(f.get("enabled", out.get("enabled", True)))
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

    def update_retailer(self, rid: str, name: str, commission: float, active: bool) -> dict:
        r = self._find("retailers", "id", rid, "retailer")
        if not name.strip() or not 0 <= commission <= 100:
            raise LotteryError("Name required and commission must be 0-100")
        r.update({"name": name.strip(), "commission": float(commission), "active": bool(active)})
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

    def add_retailer(self, name: str, commission: float) -> dict:
        rid = re.sub(r"\W+", "_", name.lower()).strip("_") or secrets.token_hex(3)
        if any(r["id"] == rid for r in self.data["retailers"]):
            raise LotteryError("Retailer already exists")
        r = {"id": rid, "name": name, "commission": float(commission), "active": True}
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

    def update_game(self, gid: str, f: dict) -> dict:
        g = self._find("games", "id", gid, "game")
        new = dict(g)
        for k in ("name", "color", "draw_time", "open_time", "cutoff", "logo"):
            if k in f:
                new[k] = f[k]
        if "enabled" in f:
            new["enabled"] = bool(f["enabled"])
        if "bet_types" in f:
            keys = {b["key"] for b in self.data["bet_types"]}
            if any(k not in keys for k in f["bet_types"]):
                raise LotteryError("Unknown bet type")
            new["bet_types"] = list(f["bet_types"])
        if "draw_days" in f:
            days = f["draw_days"]
            if any(not isinstance(d, int) or not 0 <= d <= 6 for d in days):
                raise LotteryError("Draw days must be 0 (Mon) to 6 (Sun)")
            new["draw_days"] = sorted(set(days))
        if not str(new["name"]).strip():
            raise LotteryError("Game name is required")
        for k in ("draw_time", "open_time", "cutoff"):
            if not re.fullmatch(r"\d\d:\d\d", new[k]):
                raise LotteryError("Times must be HH:MM")
        if new["open_time"] >= new["cutoff"]:
            raise LotteryError("Open time must be before the cut-off")
        if new["logo"] and not (new["logo"].startswith(("data:image/", "/local/")) and len(new["logo"]) < 300_000):
            raise LotteryError("Invalid logo")
        g.update(new)
        self._save()
        return g

    def delete_game(self, gid: str) -> None:
        g = self._find("games", "id", gid, "game")
        if any(l["game"] == gid for t in self.data["tickets"].values() for l in t["lines"]):
            raise LotteryError("This game has sales history - hide it instead")
        self.data["games"].remove(g)
        self._save()

    def update_bet_type(self, key: str, label: str, multiplier: float, enabled: bool) -> dict:
        b = self._find("bet_types", "key", key, "bet type")
        if not label.strip() or multiplier <= 0:
            raise LotteryError("Label and a payout above 0 are required")
        b.update({"label": label.strip(), "multiplier": multiplier, "enabled": bool(enabled)})
        self._save()
        return b

    def add_game(self, name: str, color: str = "#64748b", draw_time: str = "12:00",
                 cutoff: str = "11:45", logo: str = "") -> dict:
        gid = re.sub(r"\W+", "_", name.lower()).strip("_")
        if not gid or any(g["id"] == gid for g in self.data["games"]):
            raise LotteryError("Game already exists")
        g = {"id": gid, "name": name, "color": color, "draw_time": draw_time, "open_time": "00:00", "cutoff": cutoff,
             "logo": logo, "enabled": True, "bet_types": [], "draw_days": []}
        self.data["games"].append(g)
        self._save()
        return g
