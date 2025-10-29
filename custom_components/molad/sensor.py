"""Sensor platform for Molad."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.const import Platform

# Modern hdate v1.1.2 — NO htables!
from hdate import HDate
from hdate.zmanim import Location

from .const import (
    DOMAIN,
    DEFAULT_DIASPORA,
    SENSOR_MOLAD,
    SENSOR_IS_SHABBOS_MEVOCHIM,
    SENSOR_IS_UPCOMING_SHABBOS_MEVOCHIM,
)

_LOGGER = logging.getLogger(__name__)

# Hebrew day names (Sunday = 0)
HEBREW_DAYS = [
    "Sunday", "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Shabbos"
]

# Shabbos Mevorchim logic
def _is_shabbos_mevorchim(hdate: HDate, diaspora: bool) -> bool:
    """Check if today is Shabbos Mevorchim."""
    if hdate.weekday != 6:  # Not Shabbos
        return False
    rosh_chodesh = hdate.hebrew_date + timedelta(days=(8 - hdate.weekday))
    if diaspora:
        return rosh_chodesh.weekday in [0, 1]  # Sun/Mon
    return rosh_chodesh.weekday == 0  # Sunday only in Israel

def _is_upcoming_shabbos_mevorchim(hdate: HDate, diaspora: bool) -> bool:
    """Check if next Shabbos is Mevorchim."""
    next_shabbos = h randate + timedelta(days=(6 - hdate.weekday))
    next_hdate = HDate.from_py(next_shabbos)
    return _is_shabbos_mevorchim(next_hdate, diaspora)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_config_entry_first_refresh()

    entities = [
        MoladSensor(coordinator),
        ShabbosMevorchimSensor(coordinator, is_today=True),
        ShabbosMevorchimSensor(coordinator, is_today=False),
    ]
    async_add_entities(entities, True)


class MoladDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Molad data."""

    def __init__(self, hass: HomeAssistant, diaspora: bool) -> None:
        """Initialize the coordinator."""
        self.diaspora = diaspora
        self.location = Location(
            name="Jerusalem",
            latitude=31.778,
            longitude=35.235,
            timezone="Asia/Jerusalem",
            diaspora=diaspora,
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(days=1),
        )

    async def _async_update_data(self):
        """Fetch molad data."""
        from hdate import Molad

        now = datetime.now()
        year = now.year
        month = now.month

        # Get next molad
        molad = Molad(year=year, month=month, location=self.location)
        while molad.molad_date < now:
            month += 1
            if month > 12:
                month = 1
                year += 1
            molad = Molad(year=year, month=month, location=self.location)

        molad_py_date = molad.molad_date.date()
        hdate = HDate.from_py(molad_py_date)

        # Build attributes
        attrs = {
            "day": HEBREW_DAYS[molad.molad_date.weekday],
            "hours": molad.hours,
            "minutes": molad.minutes,
            "am_or_pm": "pm" if molad.hours >= 12 else "am",
            "chalakim": molad.chalakim,
            "friendly": molad.friendly,
            "month_name": hdate.hebrew_month_name,
            "hebrew_year": hdate.hebrew_year,
            "rosh_chodesh": molad.rosh_chodesh,
            "rosh_chodesh_days": molad.rosh_chodesh_days,
            "rosh_chodesh_dates": molad.rosh_chodesh_dates,
            "is_shabbos_mevorchim": _is_shabbos_mevorchim(hdate, self.diaspora),
            "is_upcoming_shabbos_mevorchim": _is_upcoming_shabbos_mevorchim(hdate, self.diaspora),
        }

        return {
            "molad": molad.friendly,
            "attributes": attrs,
        }


class MoladSensor(CoordinatorEntity, SensorEntity):
    """Representation of the Molad sensor."""

    _attr_name = "Molad"
    _attr_icon = "mdi:moon-waning-crescent"
    _attr_entity_category = None

    def __init__(self, coordinator: MoladDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_MOLAD}"

    @property
    def native_value(self):
        """Return the state."""
        return self.coordinator.data["molad"]

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self.coordinator.data["attributes"]


class ShabbosMevorchimSensor(CoordinatorEntity, SensorEntity):
    """Representation of Shabbos Mevorchim sensor."""

    def __init__(self, coordinator: MoladDataUpdateCoordinator, is_today: bool) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.is_today = is_today
        key = SENSOR_IS_SHABBOS_MEVOCHIM if is_today else SENSOR_IS_UPCOMING_SHABBOS_MEVOCHIM
        self._attr_unique_id = f"{DOMAIN}_{key}"
        self._attr_name = "Today is Shabbos Mevorchim" if is_today else "Upcoming Shabbos is Mevorchim"
        self._attr_icon = "mdi:calendar-star"

    @property
    def native_value(self):
        """Return the state."""
        key = "is_shabbos_mevorchim" if self.is_today else "is_upcoming_shabbos_mevorchim"
        return self.coordinator.data["attributes"].get(key, False)

    @property
    def is_on(self):
        """Return true if on."""
        return self.native_value
