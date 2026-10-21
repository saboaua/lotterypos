"""Persistent data + business logic (sales, results, settlement)."""
from __future__ import annotations

import copy
import re
import secrets

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (DEFAULT_BET_TYPES, DEFAULT_GAMES, DOMAIN, SIGNAL_UPDATE,
                    STORAGE_KEY, STORAGE_VERSION)


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
            }
        data["currency"] = currency
        data.setdefault("settings", {"name": "Lottery POS", "logo": ""})
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
            bt = self._find("bet_types", "key", ln["bet_type"], "bet type")
            num, amt = str(ln["number"]), round(float(ln["amount"]), 2)
            if not (num.isdigit() and len(num) == bt["digits"]):
                raise LotteryError(f"{bt['label']} needs {bt['digits']} digits")
            if amt <= 0:
                raise LotteryError("Amount must be above 0")
            line = {"game": game["id"], "bet_type": bt["key"], "number": num, "amount": amt,
                    "date": ln["date"], "prize": 0.0, "settled": False}
            if self._closed(line):
                raise LotteryError(f"{game['name']} is closed for {line['date']}")
            if f"{game['id']}|{line['date']}" in self.data["results"]:
                raise LotteryError(f"{game['name']} {line['date']} already drawn")
            clean.append(line)
        now = dt_util.now()
        self.data["seq"] += 1
        tid = f"{now:%y%m%d}{self.data['seq'] % 10000:04d}{secrets.randbelow(10**8):08d}"
        ticket = {"id": tid, "retailer_id": retailer["id"], "created": now.isoformat(), "lines": clean,
                  "total": round(sum(l["amount"] for l in clean), 2), "status": "active", "prize": 0.0}
        self.data["tickets"][tid] = ticket
        self._save()
        self.hass.bus.async_fire(f"{DOMAIN}_ticket_sold", {"ticket_id": tid, "retailer_id": retailer["id"], "total": ticket["total"]})
        return self.public(ticket)

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

    # ---------- results & settlement ----------
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
        else:  # chances: last 2 digits of any of the drawn numbers
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

    # ---------- reports ----------
    def report(self, date_from: str, date_to: str) -> dict:
        rows: dict[str, dict] = {}
        for r in self.data["retailers"]:
            rows[r["id"]] = {"retailer": r["name"], "commission_pct": r["commission"], "tickets": 0,
                             "sales": 0.0, "commission": 0.0, "prizes": 0.0, "net": 0.0}
        for t in self.data["tickets"].values():
            if t["status"] == "cancelled" or t["retailer_id"] not in rows:
                continue
            row, hit = rows[t["retailer_id"]], False
            for l in t["lines"]:
                if date_from <= l["date"] <= date_to:
                    row["sales"] += l["amount"]
                    row["prizes"] += l["prize"]
                    hit = True
            row["tickets"] += hit
        totals = {"tickets": 0, "sales": 0.0, "commission": 0.0, "prizes": 0.0, "net": 0.0}
        for row in rows.values():
            row["commission"] = row["sales"] * row["commission_pct"] / 100
            row["net"] = row["sales"] - row["commission"] - row["prizes"]
            for k in totals:
                totals[k] += row[k]
            for k in ("sales", "commission", "prizes", "net"):
                row[k] = round(row[k], 2)
        return {"from": date_from, "to": date_to, "rows": list(rows.values()),
                "totals": {k: round(v, 2) for k, v in totals.items()}}

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
    def set_branding(self, name: str, logo: str) -> dict:
        name = name.strip()[:40]
        if not name:
            raise LotteryError("Enter a lottery name")
        if logo and not (logo.startswith("data:image/") or logo.startswith("/local/")):
            raise LotteryError("Logo must be an uploaded image or a /local/ path")
        if len(logo) > 300_000:
            raise LotteryError("Logo image is too large")
        self.data["settings"] = {"name": name, "logo": logo}
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

    def add_game(self, name: str, color: str = "#64748b", draw_time: str = "12:00",
                 cutoff: str = "11:45", logo: str = "") -> dict:
        gid = re.sub(r"\W+", "_", name.lower()).strip("_")
        if not gid or any(g["id"] == gid for g in self.data["games"]):
            raise LotteryError("Game already exists")
        g = {"id": gid, "name": name, "color": color, "draw_time": draw_time, "cutoff": cutoff, "logo": logo}
        self.data["games"].append(g)
        self._save()
        return g
