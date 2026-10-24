"""Lottery POS - number-game sales, results and settlement for Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from homeassistant.helpers.event import async_track_time_interval

from . import api
from . import auth as authlib
from .const import DOMAIN, LEAFLET_URL, PANEL_URL, PANEL_URL_OFFICE, PLATFORMS, STATIC_URL, VERSION
from .store import LotteryError, LotteryStore

_LOGGER = logging.getLogger(__name__)
AUTO_FETCH_EVERY = timedelta(minutes=10)


async def _require_admin(hass, call) -> None:
    """Services change company data: only Home Assistant administrators may call them."""
    uid = call.context.user_id
    if uid is None:  # automations / scripts / internal calls
        return
    user = await hass.auth.async_get_user(uid)
    if not user or not user.is_admin:
        raise Unauthorized(context=call.context)


def _register_services(hass):
    def wrap(fn):
        async def handler(call):
            await _require_admin(hass, call)
            try:
                res = fn(hass.data[DOMAIN]["store"], call.data)
                if hasattr(res, "__await__"):
                    await res
            except LotteryError as err:
                raise HomeAssistantError(str(err)) from err
        return handler

    reg = hass.services.async_register
    reg(DOMAIN, "set_results", wrap(lambda s, d: s.set_results(d["game"], d["date"], d["numbers"], d.get("session"))),
        vol.Schema({vol.Required("game"): str, vol.Required("date"): str, vol.Required("numbers"): [str],
                    vol.Optional("session"): str}))
    reg(DOMAIN, "cancel_ticket", wrap(lambda s, d: s.cancel(d["ticket_id"])), vol.Schema({vol.Required("ticket_id"): str}))
    reg(DOMAIN, "redeem_ticket", wrap(lambda s, d: s.redeem(d["ticket_id"], d.get("retailer_id"))),
        vol.Schema({vol.Required("ticket_id"): str, vol.Optional("retailer_id"): str}))
    reg(DOMAIN, "add_retailer", wrap(lambda s, d: s.add_retailer(dict(d))),
        vol.Schema({
            vol.Required("name"): str,
            vol.Optional("number"): str,
            vol.Optional("first_name"): str,
            vol.Optional("last_name"): str,
            vol.Optional("address"): str,
            vol.Optional("phone"): str,
            vol.Optional("commission_sell", default=10): vol.Coerce(float),
            vol.Optional("commission_redeem", default=0): vol.Coerce(float),
            vol.Optional("commission"): vol.Coerce(float),
            vol.Optional("lat"): vol.Coerce(float),
            vol.Optional("lng"): vol.Coerce(float),
        }))
    reg(DOMAIN, "add_game", wrap(lambda s, d: s.add_game(dict(d))),
        vol.Schema({vol.Required("name"): str, vol.Optional("color"): str, vol.Optional("draw_time"): str,
                    vol.Optional("cutoff"): str, vol.Optional("logo"): str, vol.Optional("format"): str,
                    vol.Optional("digits"): vol.Coerce(int), vol.Optional("main_count"): vol.Coerce(int),
                    vol.Optional("main_max"): vol.Coerce(int), vol.Optional("mega_count"): vol.Coerce(int),
                    vol.Optional("mega_max"): vol.Coerce(int)}))
    reg(DOMAIN, "fetch_results", wrap(lambda s, d: s.async_scrape()), vol.Schema({}))

    async def reset_owner_password(call):
        """Recovery: set the back-office owner password (and optionally the username)."""
        await _require_admin(hass, call)
        store = hass.data[DOMAIN]["store"]
        bad = authlib.check_strength(call.data["password"])
        if bad:
            raise HomeAssistantError(bad)
        try:
            if call.data.get("username"):
                store.set_owner_username(call.data["username"])
            hashed = await hass.async_add_executor_job(authlib.hash_password, call.data["password"])
        except LotteryError as err:
            raise HomeAssistantError(str(err)) from err
        store.set_password_hash("owner", "owner", hashed, must_change=False)

    reg(DOMAIN, "reset_owner_password", reset_owner_password,
        vol.Schema({vol.Required("password"): str, vol.Optional("username"): str}))


async def _register_panels(hass) -> None:
    for url, title, icon, mode in (
        (PANEL_URL, "Lottery Sell", "mdi:ticket-confirmation", "sell"),
        (PANEL_URL_OFFICE, "Lottery Back Office", "mdi:store-cog", "office"),
    ):
        await panel_custom.async_register_panel(
            hass, webcomponent_name="lottery-pos-panel", frontend_url_path=url,
            module_url=f"{STATIC_URL}?v={VERSION}", sidebar_title=title, sidebar_icon=icon,
            require_admin=False, config={"mode": mode})


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
            StaticPathConfig(LEAFLET_URL, str(frontend_dir / "leaflet"), False),
        ])
        api.async_register(hass)
        _register_services(hass)
        dom["registered"] = True
    await _register_panels(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _auto_fetch(_now):
        if not store.data["settings"].get("auto_results", True) or not store.pending_draws():
            return
        try:
            res = await store.async_scrape(auto=True)
            if res["imported"]:
                _LOGGER.info("Imported %d draw result(s) automatically", len(res["imported"]))
            dom.pop("fetch_failed", None)
        except LotteryError as err:
            if not dom.get("fetch_failed"):  # log once per failure streak, not every 10 minutes
                _LOGGER.warning("Automatic results fetch failed: %s", err)
            dom["fetch_failed"] = True

    dom["unsub_fetch"] = async_track_time_interval(hass, _auto_fetch, AUTO_FETCH_EVERY)

    if store.initial_owner_password:
        from homeassistant.components import persistent_notification
        persistent_notification.async_create(
            hass,
            "The back office owner account was created.\n\n"
            f"**Username:** `owner`\n**Password:** `{store.initial_owner_password}`\n\n"
            "Open **Lottery Back Office** in the sidebar and sign in - you will be asked to choose your own "
            "password. Forgot it later? Call the service `lottery_pos.reset_owner_password` "
            "(Developer tools -> Actions).",
            title="Lottery POS - owner login", notification_id="lottery_pos_owner")
        store.initial_owner_password = None
    return True


async def async_unload_entry(hass, entry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        dom = hass.data.get(DOMAIN, {})
        if dom.get("unsub_fetch"):
            dom.pop("unsub_fetch")()
        for url in (PANEL_URL, PANEL_URL_OFFICE):
            frontend.async_remove_panel(hass, url)
        dom.pop("store", None)
    return ok
