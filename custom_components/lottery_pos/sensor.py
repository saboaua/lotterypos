"""Summary sensors."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_UPDATE

SENSORS = [
    ("sales_today", "Lottery sales today", "mdi:cash-register"),
    ("tickets_today", "Lottery tickets today", "mdi:ticket"),
    ("unpaid_prizes", "Lottery unpaid prizes", "mdi:trophy"),
]


async def async_setup_entry(hass, entry, async_add_entities):
    store = hass.data[DOMAIN]["store"]
    async_add_entities(LotterySensor(store, *s) for s in SENSORS)


class LotterySensor(SensorEntity):
    _attr_should_poll = False

    def __init__(self, store, key, name, icon):
        self._store, self._key = store, key
        self._attr_name, self._attr_icon = name, icon
        self._attr_unique_id = f"{DOMAIN}_{key}"
        if key != "tickets_today":
            self._attr_native_unit_of_measurement = store.data.get("currency", "AWG")

    @property
    def native_value(self):
        return self._store.summary()[self._key]

    async def async_added_to_hass(self):
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self._refresh))

    @callback
    def _refresh(self):
        self.async_write_ha_state()
