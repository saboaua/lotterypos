"""WebSocket API used by the panels.

Every command except ``login`` and ``check_promo`` needs the session ``token`` that
``login`` returned. The role of the token decides what a command may do:

  owner     back office (games, retailers, promotions, results, reports ...)
  retailer  sell screen - always acts as *its own* shop; a retailer id sent by the
            browser is ignored, so a shop can never sell or report as another shop
"""
import asyncio
from types import SimpleNamespace

import voluptuous as vol
from homeassistant.components import websocket_api

from . import auth as authlib
from .const import DOMAIN
from .store import LotteryError

# Flexible line: digit uses number; zodiac adds symbols; jackpot uses balls + mega
_LINE = vol.Schema({
    vol.Required("game"): str,
    vol.Required("bet_type"): str,
    vol.Optional("number", default=""): str,
    vol.Required("amount"): vol.Coerce(float),
    vol.Required("date"): str,
    vol.Optional("symbols", default=[]): [str],
    vol.Optional("balls", default=[]): [str],
    vol.Optional("mega", default=""): str,
    vol.Optional("draws", default=1): vol.Coerce(int),
    vol.Optional("multi_draw", default=1): vol.Coerce(int),
    vol.Optional("session", default=""): str,
}, extra=vol.ALLOW_EXTRA)

PUBLIC, OWNER, RETAILER, ANY = "public", "owner", "retailer", "any"


def _cmd(name, schema=None, role=ANY):
    """Register a command. The handler gets (store, msg, ctx); ctx.sess is the login session."""
    def deco(fn):
        @websocket_api.websocket_command({
            vol.Required("type"): f"{DOMAIN}/{name}",
            vol.Optional("token"): vol.Any(str, None),
            **(schema or {}),
        })
        @websocket_api.async_response
        async def handler(hass, connection, msg):
            try:
                store = hass.data[DOMAIN]["store"]
            except KeyError:
                connection.send_error(msg["id"], "not_ready", "Lottery POS is not loaded")
                return
            sess = None
            if role != PUBLIC:
                sess = store.auth.get(msg.get("token"))
                if not sess:
                    connection.send_error(msg["id"], "auth_required", "Please sign in")
                    return
                if role in (OWNER, RETAILER) and sess.role != role:
                    connection.send_error(msg["id"], "unauthorized", "Not allowed for this account")
                    return
                if sess.role == RETAILER:
                    r = next((x for x in store.data["retailers"] if x["id"] == sess.subject), None)
                    if not r or not r.get("active", True):
                        store.auth.revoke(sess.token)
                        connection.send_error(msg["id"], "auth_required", "This shop is disabled")
                        return
            ctx = SimpleNamespace(hass=hass, sess=sess)
            try:
                result = fn(store, msg, ctx)
                if asyncio.iscoroutine(result):
                    result = await result
                connection.send_result(msg["id"], result)
            except LotteryError as err:
                connection.send_error(msg["id"], "lottery_error", str(err))
        return handler
    return deco


async def _hash(ctx, pw):
    return await ctx.hass.async_add_executor_job(authlib.hash_password, pw)


async def _verify(ctx, pw, stored):
    return await ctx.hass.async_add_executor_job(authlib.verify_password, pw, stored)


# ---------------------------------------------------------------- sign in / out
@_cmd("login", {vol.Required("username"): str, vol.Required("password"): str,
                vol.Required("mode"): vol.In(["sell", "office"])}, role=PUBLIC)
async def _login(s, m, ctx):
    user, mode = m["username"].strip(), m["mode"]
    wait = s.auth.locked_for(user)
    if wait:
        raise LotteryError(f"Too many attempts. Try again in {max(1, wait // 60)} min")
    acct = s.find_account(user, mode)
    # verify even when the account does not exist so timing does not reveal valid usernames
    ok = await _verify(ctx, m["password"], acct["pw_hash"] if acct else None)
    if not acct or not ok:
        s.auth.record_failure(user)
        raise LotteryError("Wrong username or password")
    if acct["role"] == "retailer" and not acct.get("active", True):
        raise LotteryError("This shop is disabled - contact the lottery office")
    s.auth.clear_failures(user)
    sess = s.auth.create(acct["role"], acct["subject"], acct["username"], acct["name"], mode)
    return {"token": sess.token, "role": sess.role, "name": sess.name, "username": sess.username,
            "retailer_id": sess.subject if sess.role == "retailer" else "", "must_change": acct["must_change"]}


@_cmd("logout")
def _logout(s, m, ctx):
    s.auth.revoke(ctx.sess.token)
    return {}


@_cmd("whoami")
def _whoami(s, m, ctx):
    se = ctx.sess
    must = False
    try:
        must = s.data["accounts"]["owner"].get("must_change", False) if se.role == "owner" else \
            bool(next(r for r in s.data["retailers"] if r["id"] == se.subject).get("must_change"))
    except StopIteration:
        pass
    return {"role": se.role, "name": se.name, "username": se.username, "mode": se.mode,
            "retailer_id": se.subject if se.role == "retailer" else "", "must_change": must}


@_cmd("change_password", {vol.Required("old_password"): str, vol.Required("new_password"): str})
async def _chpw(s, m, ctx):
    se = ctx.sess
    if not await _verify(ctx, m["old_password"], s.current_hash(se.role, se.subject)):
        raise LotteryError("Current password is wrong")
    bad = authlib.check_strength(m["new_password"])
    if bad:
        raise LotteryError(bad)
    if m["new_password"] == m["old_password"]:
        raise LotteryError("Choose a different password")
    s.set_password_hash(se.role, se.subject, await _hash(ctx, m["new_password"]))
    new = s.auth.create(se.role, se.subject, se.username, se.name, se.mode)  # keep this browser signed in
    return {"token": new.token}


# ---------------------------------------------------------------- shared reads
@_cmd("state")
def _state(s, m, ctx):
    return s.state_for(ctx.sess.role, ctx.sess.subject if ctx.sess.role == "retailer" else None)


@_cmd("ticket", {vol.Required("ticket_id"): str})
def _ticket(s, m, ctx): return s.public(s.ticket(m["ticket_id"]))


@_cmd("draw_results", {vol.Required("date"): str})
def _draws(s, m, ctx): return s.draw_results(m["date"])


@_cmd("check_promo", {vol.Required("code"): str}, role=PUBLIC)
def _chk(s, m, ctx): return s.check_promo_code(m["code"])


# ---------------------------------------------------------------- retailer (sell screen)
@_cmd("sell", {vol.Required("lines"): [_LINE], vol.Optional("retailer_id"): str}, role=RETAILER)
def _sell(s, m, ctx): return s.sell(ctx.sess.subject, m["lines"])


@_cmd("last", {vol.Optional("retailer_id"): str}, role=RETAILER)
def _last(s, m, ctx):
    mine = [t for t in s.data["tickets"].values() if t["retailer_id"] == ctx.sess.subject]
    if not mine:
        raise LotteryError("No tickets yet")
    return s.public(max(mine, key=lambda t: t["created"]))


@_cmd("cancel", {vol.Required("ticket_id"): str})
def _cancel(s, m, ctx):
    t = s.ticket(m["ticket_id"])
    if ctx.sess.role == "retailer" and t["retailer_id"] != ctx.sess.subject:
        raise LotteryError("Only the shop that sold a ticket can cancel it")
    return s.cancel(m["ticket_id"])


@_cmd("redeem", {vol.Required("ticket_id"): str, vol.Optional("retailer_id"): str})
def _redeem(s, m, ctx):
    # a shop pays out as itself (any shop may pay any winning ticket); the owner pays without a shop
    return s.redeem(m["ticket_id"], ctx.sess.subject if ctx.sess.role == "retailer" else None)


@_cmd("report", {vol.Required("date_from"): str, vol.Required("date_to"): str, vol.Optional("retailer_id"): str})
def _report(s, m, ctx):
    # a shop only ever gets its own numbers
    rid = ctx.sess.subject if ctx.sess.role == "retailer" else (m.get("retailer_id") or None)
    return s.report(m["date_from"], m["date_to"], rid)


# ---------------------------------------------------------------- owner: results
@_cmd("fetch_results", {vol.Optional("url"): str}, role=OWNER)
async def _fetch(s, m, ctx): return await s.async_scrape(m.get("url"))


@_cmd("scrape_indios", {vol.Optional("url"): str}, role=OWNER)
async def _scrape_indios(s, m, ctx): return await s.async_scrape(m.get("url"))


@_cmd("scrape_joeblack", {vol.Optional("url"): str}, role=OWNER)
async def _scrape(s, m, ctx): return await s.async_scrape(m.get("url"))


@_cmd("set_results", {vol.Required("game"): str, vol.Required("date"): str, vol.Required("numbers"): [str],
                      vol.Optional("session", default=""): str}, role=OWNER)
def _results(s, m, ctx): return {"winners": s.set_results(m["game"], m["date"], m["numbers"], m.get("session") or None)}


@_cmd("results_summary", {vol.Required("date_from"): str, vol.Required("date_to"): str}, role=OWNER)
def _rsum(s, m, ctx): return s.results_summary(m["date_from"], m["date_to"])


# ---------------------------------------------------------------- owner: calendar
@_cmd("year_schedule", {vol.Required("year"): vol.Coerce(int)}, role=OWNER)
def _year(s, m, ctx): return s.year_schedule(m["year"])


@_cmd("add_holiday", {vol.Required("date"): str, vol.Required("name"): str,
                      vol.Optional("games", default=[]): [str]}, role=OWNER)
def _add_hol(s, m, ctx): return s.add_holiday(m["date"], m["name"], m.get("games") or [])


@_cmd("delete_holiday", {vol.Required("holiday_id"): str}, role=OWNER)
def _del_hol(s, m, ctx):
    s.delete_holiday(m["holiday_id"])
    return {}


@_cmd("seed_holidays", {vol.Required("year"): vol.Coerce(int)}, role=OWNER)
def _seed_hol(s, m, ctx): return s.seed_holidays(m["year"])


@_cmd("set_sales_settings", {vol.Required("advance_days"): vol.All(vol.Coerce(int), vol.Range(min=1, max=90)),
                             vol.Required("auto_results"): bool}, role=OWNER)
def _sales_settings(s, m, ctx):
    s.data["settings"]["advance_days"] = m["advance_days"]
    s.data["settings"]["auto_results"] = m["auto_results"]
    s._save()
    return {}


# ---------------------------------------------------------------- owner: retailers & logins
_RET_FIELDS = {
    vol.Optional("number"): str, vol.Optional("first_name"): str, vol.Optional("last_name"): str,
    vol.Optional("address"): str, vol.Optional("phone"): str,
    vol.Optional("commission_sell"): vol.Coerce(float), vol.Optional("commission_redeem"): vol.Coerce(float),
    vol.Optional("commission"): vol.Coerce(float), vol.Optional("active"): bool,
    vol.Optional("lat"): vol.Any(None, "", vol.Coerce(float)), vol.Optional("lng"): vol.Any(None, "", vol.Coerce(float)),
    vol.Optional("username"): str,
}


@_cmd("add_retailer", {vol.Required("name"): str, vol.Optional("password"): str, **_RET_FIELDS}, role=OWNER)
async def _add_r(s, m, ctx):
    fields = {k: v for k, v in m.items() if k not in ("type", "id", "token", "password")}
    pw = (m.get("password") or "").strip()
    generated = not pw
    if generated:
        pw = authlib.generate_password()
    bad = authlib.check_strength(pw)
    if bad:
        raise LotteryError(bad)
    r = s.add_retailer(fields, await _hash(ctx, pw))
    return {**r, "initial_password": pw if generated else ""}


@_cmd("update_retailer", {vol.Required("retailer_id"): str, vol.Required("name"): str, **_RET_FIELDS}, role=OWNER)
def _upd_r(s, m, ctx):
    return s.update_retailer(m["retailer_id"], {k: v for k, v in m.items() if k not in ("retailer_id", "type", "id", "token")})


@_cmd("reset_retailer_password", {vol.Required("retailer_id"): str, vol.Optional("password"): str}, role=OWNER)
async def _reset_r(s, m, ctx):
    r = next((x for x in s.data["retailers"] if x["id"] == m["retailer_id"]), None)
    if not r:
        raise LotteryError("Retailer not found")
    if not r.get("username"):
        raise LotteryError("Set a username first")
    pw = (m.get("password") or "").strip()
    generated = not pw
    if generated:
        pw = authlib.generate_password()
    bad = authlib.check_strength(pw)
    if bad:
        raise LotteryError(bad)
    s.set_password_hash("retailer", r["id"], await _hash(ctx, pw), must_change=True)
    return {"username": r["username"], "password": pw}


@_cmd("remove_demo_logins", role=OWNER)
def _rm_demo(s, m, ctx): return {"removed": s.remove_demo_logins()}


@_cmd("set_owner_username", {vol.Required("username"): str}, role=OWNER)
def _owner_user(s, m, ctx):
    s.set_owner_username(m["username"])
    ctx.sess.username = m["username"].strip().lower()
    return {"username": ctx.sess.username}


@_cmd("add_game", {
    vol.Required("name"): str,
    vol.Optional("color", default="#64748b"): str,
    vol.Optional("draw_time", default="12:00"): str,
    vol.Optional("cutoff", default="11:45"): str,
    vol.Optional("logo", default=""): str,
    vol.Optional("format", default="digit"): str,
    vol.Optional("digits", default=4): vol.Coerce(int),
    vol.Optional("main_count", default=5): vol.Coerce(int),
    vol.Optional("main_max", default=30): vol.Coerce(int),
    vol.Optional("mega_count", default=0): vol.Coerce(int),
    vol.Optional("mega_max", default=15): vol.Coerce(int),
    vol.Optional("symbols", default=[]): [str],
}, role=OWNER)
def _add_g(s, m, ctx): return s.add_game(m)

@_cmd("set_branding", {vol.Required("name"): str, vol.Optional("logo", default=""): str,
                     vol.Optional("operator", default=""): str, vol.Optional("tagline", default=""): str,
                     vol.Optional("license_text", default=""): str}, role=OWNER)
def _brand(s, m, ctx): return s.set_branding(m["name"], m["logo"], m.get("operator",""), m.get("tagline",""), m.get("license_text",""))

@_cmd("set_ticker", {vol.Required("text"): str, vol.Required("enabled"): bool, vol.Required("speed"): vol.Coerce(int),
                     vol.Required("color"): str, vol.Optional("messages", default=[]): list}, role=OWNER)
def _ticker(s, m, ctx): return s.set_ticker(m["text"], m["enabled"], m["speed"], m["color"], m.get("messages") or [])

# NOTE: never use schema key "id" — it collides with the WebSocket message id (int).
@_cmd("update_game", {
    vol.Required("game_id"): str, vol.Optional("name"): str, vol.Optional("color"): str,
    vol.Optional("draw_time"): str, vol.Optional("open_time"): str, vol.Optional("cutoff"): str,
    vol.Optional("enabled"): bool, vol.Optional("bet_types"): [str], vol.Optional("logo"): str,
    vol.Optional("draw_days"): [vol.All(int, vol.Range(min=0, max=6))],
    vol.Optional("format"): str, vol.Optional("digits"): vol.Coerce(int),
    vol.Optional("main_count"): vol.Coerce(int), vol.Optional("main_max"): vol.Coerce(int),
    vol.Optional("mega_count"): vol.Coerce(int), vol.Optional("mega_max"): vol.Coerce(int),
    vol.Optional("symbols"): [str],
    vol.Optional("sessions"): list,
    vol.Optional("min_stake"): vol.Coerce(float), vol.Optional("max_stake"): vol.Coerce(float),
    vol.Optional("jackpot_min"): vol.Coerce(float), vol.Optional("jackpot_current"): vol.Coerce(float),
    vol.Optional("jackpot_contrib"): vol.Coerce(float),
    vol.Optional("jackpot_prizes"): list, vol.Optional("fixed_prices"): list,
    vol.Optional("one_per_day"): bool, vol.Optional("week_schedule"): dict,
    vol.Optional("ext_codes"): [str],
}, role=OWNER)
def _upd_g(s, m, ctx): return s.update_game(m["game_id"], {k: v for k, v in m.items() if k not in ("game_id", "type")})

@_cmd("delete_game", {vol.Required("game_id"): str}, role=OWNER)
def _del_g(s, m, ctx):
    s.delete_game(m["game_id"])
    return {}

@_cmd("update_bet_type", {
    vol.Required("key"): str,
    vol.Required("label"): str,
    vol.Required("multiplier"): vol.Coerce(float),
    vol.Required("enabled"): bool,
    vol.Optional("min_stake"): vol.Coerce(float),
    vol.Optional("max_stake"): vol.Coerce(float),
}, role=OWNER)
def _upd_b(s, m, ctx):
    return s.update_bet_type(m["key"], {k: v for k, v in m.items() if k not in ("key", "type")})

@_cmd("set_ticket_design", {vol.Required("design"): dict}, role=OWNER)
def _design(s, m, ctx): return s.set_ticket_design(m["design"])



_PRIZE = vol.Schema({
    vol.Required("label"): str,
    vol.Required("amount"): vol.Coerce(float),
    vol.Required("quantity"): vol.Coerce(int),
})

@_cmd("add_promotion", {
    vol.Required("name"): str,
    vol.Optional("trigger", default="min_plays"): str,
    vol.Optional("trigger_value", default=3): vol.Coerce(float),
    vol.Optional("code_digits", default=6): vol.Coerce(int),
    vol.Optional("games", default=[]): [str],
    vol.Optional("label", default="Qualified for promotion"): str,
    vol.Optional("instruction", default="Visit www.shocolottery.com and check if you have won"): str,
    vol.Optional("url", default="https://www.shocolottery.com"): str,
    vol.Optional("enabled", default=True): bool,
    vol.Optional("start_at", default=""): str,
    vol.Optional("end_at", default=""): str,
    vol.Optional("prize", default=0): vol.Coerce(float),
    vol.Optional("prizes", default=[]): [_PRIZE],
}, role=OWNER)
def _add_p(s, m, ctx):
    return s.add_promotion(m)

@_cmd("update_promotion", {
    vol.Required("promotion_id"): str,
    vol.Optional("name"): str, vol.Optional("trigger"): str,
    vol.Optional("trigger_value"): vol.Coerce(float), vol.Optional("code_digits"): vol.Coerce(int),
    vol.Optional("games"): [str],
    vol.Optional("label"): str, vol.Optional("instruction"): str, vol.Optional("url"): str,
    vol.Optional("enabled"): bool,
    vol.Optional("start_at"): str,
    vol.Optional("end_at"): str,
    vol.Optional("prize"): vol.Coerce(float),
    vol.Optional("prizes"): [_PRIZE],
}, role=OWNER)
def _upd_p(s, m, ctx):
    return s.update_promotion(m["promotion_id"], {k: v for k, v in m.items() if k not in ("promotion_id", "type")})

@_cmd("delete_promotion", {vol.Required("promotion_id"): str}, role=OWNER)
def _del_p(s, m, ctx):
    s.delete_promotion(m["promotion_id"])
    return {}

@_cmd("draw_promo_winners", {vol.Required("promotion_id"): str}, role=OWNER)
def _draw_p(s, m, ctx):
    return s.draw_promo_winners(m["promotion_id"])

@_cmd("promo_codes_summary", {vol.Optional("promotion_id"): str}, role=OWNER)
def _psum(s, m, ctx):
    return s.promo_codes_summary(m.get("promotion_id"))


COMMANDS = [
    _login, _logout, _whoami, _chpw, _state, _ticket, _draws, _chk,
    _sell, _last, _cancel, _redeem, _report,
    _fetch, _scrape_indios, _scrape, _results, _rsum,
    _year, _add_hol, _del_hol, _seed_hol, _sales_settings,
    _add_r, _upd_r, _reset_r, _rm_demo, _owner_user,
    _brand, _ticker, _upd_g, _del_g, _upd_b, _design,
    _add_g, _add_p, _upd_p, _del_p, _draw_p, _psum,
]


def async_register(hass):
    for c in COMMANDS:
        websocket_api.async_register_command(hass, c)
