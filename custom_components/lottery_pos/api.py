"""WebSocket API used by the sidebar panel."""
import voluptuous as vol
from homeassistant.components import websocket_api

from .const import DOMAIN
from .store import LotteryError

_LINE = vol.Schema({vol.Required("game"): str, vol.Required("bet_type"): str, vol.Required("number"): str,
                    vol.Required("amount"): vol.Coerce(float), vol.Required("date"): str})


def _cmd(name, schema=None, admin=False):
    def deco(fn):
        @websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/{name}", **(schema or {})})
        @websocket_api.async_response
        async def handler(hass, connection, msg):
            if admin and not connection.user.is_admin:
                connection.send_error(msg["id"], "unauthorized", "Admin access required")
                return
            try:
                connection.send_result(msg["id"], fn(hass.data[DOMAIN]["store"], msg))
            except LotteryError as err:
                connection.send_error(msg["id"], "lottery_error", str(err))
        return handler
    return deco


@_cmd("state")
def _state(s, m):
    d = s.data
    return {"games": [g for g in d["games"] if g.get("enabled", True)], "all_games": d["games"],
            "bet_types": [b for b in d["bet_types"] if b.get("enabled", True)], "all_bet_types": d["bet_types"],
            "currency": d["currency"], "settings": d["settings"],
            "retailers": [r for r in d["retailers"] if r.get("active", True)], "all_retailers": d["retailers"],
            "promotions": d.get("promotions", []), "summary": s.summary()}

@_cmd("sell", {vol.Required("retailer_id"): str, vol.Required("lines"): [_LINE]})
def _sell(s, m): return s.sell(m["retailer_id"], m["lines"])

@_cmd("ticket", {vol.Required("ticket_id"): str})
def _ticket(s, m): return s.public(s.ticket(m["ticket_id"]))

@_cmd("last", {vol.Required("retailer_id"): str})
def _last(s, m):
    mine = [t for t in s.data["tickets"].values() if t["retailer_id"] == m["retailer_id"]]
    if not mine:
        raise LotteryError("No tickets yet")
    return s.public(max(mine, key=lambda t: t["created"]))

@_cmd("cancel", {vol.Required("ticket_id"): str})
def _cancel(s, m): return s.cancel(m["ticket_id"])

@_cmd("redeem", {vol.Required("ticket_id"): str})
def _redeem(s, m): return s.redeem(m["ticket_id"])

@_cmd("draw_results", {vol.Required("date"): str})
def _draws(s, m): return s.draw_results(m["date"])

@_cmd("report", {vol.Required("date_from"): str, vol.Required("date_to"): str})
def _report(s, m): return s.report(m["date_from"], m["date_to"])

@_cmd("set_results", {vol.Required("game"): str, vol.Required("date"): str, vol.Required("numbers"): [str]}, admin=True)
def _results(s, m): return {"winners": s.set_results(m["game"], m["date"], m["numbers"])}

@_cmd("add_retailer", {vol.Required("name"): str, vol.Required("commission"): vol.Coerce(float)}, admin=True)
def _add_r(s, m): return s.add_retailer(m["name"], m["commission"])

@_cmd("add_game", {vol.Required("name"): str, vol.Optional("color", default="#64748b"): str,
                   vol.Optional("draw_time", default="12:00"): str, vol.Optional("cutoff", default="11:45"): str,
                   vol.Optional("logo", default=""): str}, admin=True)
def _add_g(s, m): return s.add_game(m["name"], m["color"], m["draw_time"], m["cutoff"], m["logo"])

@_cmd("set_branding", {vol.Required("name"): str, vol.Optional("logo", default=""): str}, admin=True)
def _brand(s, m): return s.set_branding(m["name"], m["logo"])

@_cmd("set_ticker", {vol.Required("text"): str, vol.Required("enabled"): bool, vol.Required("speed"): vol.Coerce(int),
                     vol.Required("color"): str}, admin=True)
def _ticker(s, m): return s.set_ticker(m["text"], m["enabled"], m["speed"], m["color"])

@_cmd("update_game", {vol.Required("id"): str, vol.Optional("name"): str, vol.Optional("color"): str,
                      vol.Optional("draw_time"): str, vol.Optional("open_time"): str, vol.Optional("cutoff"): str,
                      vol.Optional("enabled"): bool, vol.Optional("bet_types"): [str], vol.Optional("logo"): str,
                      vol.Optional("draw_days"): [vol.All(int, vol.Range(min=0, max=6))]}, admin=True)
def _upd_g(s, m): return s.update_game(m["id"], {k: v for k, v in m.items() if k not in ("id", "type")})

@_cmd("delete_game", {vol.Required("id"): str}, admin=True)
def _del_g(s, m):
    s.delete_game(m["id"])
    return {}

@_cmd("update_bet_type", {vol.Required("key"): str, vol.Required("label"): str,
                          vol.Required("multiplier"): vol.Coerce(float), vol.Required("enabled"): bool}, admin=True)
def _upd_b(s, m): return s.update_bet_type(m["key"], m["label"], m["multiplier"], m["enabled"])

@_cmd("set_ticket_design", {vol.Required("design"): dict}, admin=True)
def _design(s, m): return s.set_ticket_design(m["design"])

@_cmd("update_retailer", {vol.Required("id"): str, vol.Required("name"): str, vol.Required("commission"): vol.Coerce(float),
                          vol.Required("active"): bool}, admin=True)
def _upd_r(s, m): return s.update_retailer(m["id"], m["name"], m["commission"], m["active"])

@_cmd("results_summary", {vol.Required("date_from"): str, vol.Required("date_to"): str}, admin=True)
def _rsum(s, m): return s.results_summary(m["date_from"], m["date_to"])

@_cmd("add_promotion", {
    vol.Required("name"): str,
    vol.Optional("trigger", default="min_lines"): str,
    vol.Optional("trigger_value", default=3): vol.Coerce(int),
    vol.Optional("code_digits", default=6): vol.Coerce(int),
    vol.Optional("label", default="Qualified for promotion"): str,
    vol.Optional("instruction", default="Visit www.shocolottery.com and check if you have won"): str,
    vol.Optional("url", default="https://www.shocolottery.com"): str,
    vol.Optional("enabled", default=True): bool,
}, admin=True)
def _add_p(s, m):
    return s.add_promotion(
        m["name"], m.get("trigger", "min_lines"), m.get("trigger_value", 3),
        m.get("code_digits", 6), m.get("label", "Qualified for promotion"),
        m.get("instruction", "Visit www.shocolottery.com and check if you have won"),
        m.get("url", "https://www.shocolottery.com"), m.get("enabled", True))

@_cmd("update_promotion", {
    vol.Required("id"): str,
    vol.Optional("name"): str, vol.Optional("trigger"): str,
    vol.Optional("trigger_value"): vol.Coerce(int), vol.Optional("code_digits"): vol.Coerce(int),
    vol.Optional("label"): str, vol.Optional("instruction"): str, vol.Optional("url"): str,
    vol.Optional("enabled"): bool,
}, admin=True)
def _upd_p(s, m):
    return s.update_promotion(m["id"], {k: v for k, v in m.items() if k not in ("id", "type")})

@_cmd("delete_promotion", {vol.Required("id"): str}, admin=True)
def _del_p(s, m):
    s.delete_promotion(m["id"])
    return {}

COMMANDS = [_design, _upd_r, _rsum, _ticker, _upd_g, _del_g, _upd_b, _brand, _state, _sell, _ticket,
            _last, _cancel, _redeem, _draws, _report, _results, _add_r, _add_g, _add_p, _upd_p, _del_p]


def async_register(hass):
    for c in COMMANDS:
        websocket_api.async_register_command(hass, c)
