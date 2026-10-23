"""Lottery POS - number-game sales, results and settlement for Home Assistant."""
from __future__ import annotations

from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.exceptions import HomeAssistantError

from . import api
from .const import DOMAIN, PANEL_URL, PLATFORMS, STATIC_URL, VERSION
from .store import LotteryError, LotteryStore


def _register_services(hass):
    def wrap(fn):
        async def handler(call):
            try:
                fn(hass.data[DOMAIN]["store"], call.data)
            except LotteryError as err:
                raise HomeAssistantError(str(err)) from err
        return handler

    reg = hass.services.async_register
    reg(DOMAIN, "set_results", wrap(lambda s, d: s.set_results(d["game"], d["date"], d["numbers"])),
        vol.Schema({vol.Required("game"): str, vol.Required("date"): str, vol.Required("numbers"): [str]}))
    reg(DOMAIN, "cancel_ticket", wrap(lambda s, d: s.cancel(d["ticket_id"])), vol.Schema({vol.Required("ticket_id"): str}))
    reg(DOMAIN, "redeem_ticket", wrap(lambda s, d: s.redeem(d["ticket_id"])), vol.Schema({vol.Required("ticket_id"): str}))
    reg(DOMAIN, "add_retailer", wrap(lambda s, d: s.add_retailer(d["name"], d["commission"])),
        vol.Schema({vol.Required("name"): str, vol.Required("commission"): vol.Coerce(float)}))
    reg(DOMAIN, "add_game", wrap(lambda s, d: s.add_game(d["name"], d.get("color", "#64748b"), d.get("draw_time", "12:00"),
                                                         d.get("cutoff", "11:45"), d.get("logo", ""))),
        vol.Schema({vol.Required("name"): str, vol.Optional("color"): str, vol.Optional("draw_time"): str,
                    vol.Optional("cutoff"): str, vol.Optional("logo"): str}))


async def async_setup_entry(hass, entry) -> bool:
    store = LotteryStore(hass)
    await store.async_load(entry.data.get("currency", "AWG"))
    dom = hass.data.setdefault(DOMAIN, {})
    dom["store"] = store
    if not dom.get("registered"):
        frontend_dir = Path(__file__).parent / "frontend"
        await hass.http.async_register_static_paths([
            StaticPathConfig(STATIC_URL, str(frontend_dir / "lottery-panel.js"), False),
            StaticPathConfig("/lottery_pos_static/check.html", str(frontend_dir / "check.html"), False),
        ])
        api.async_register(hass)
        _register_services(hass)
        dom["registered"] = True
    await panel_custom.async_register_panel(
        hass, webcomponent_name="lottery-pos-panel", frontend_url_path=PANEL_URL,
        module_url=f"{STATIC_URL}?v={VERSION}", sidebar_title="Lottery", sidebar_icon="mdi:ticket-confirmation",
        require_admin=False, config={})
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        frontend.async_remove_panel(hass, PANEL_URL)
        hass.data[DOMAIN].pop("store", None)
    return ok
