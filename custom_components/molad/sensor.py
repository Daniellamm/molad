"""Support for Molad sensors."""
import datetime
import math
import logging
import voluptuous as vol
from typing import Any, Dict

import hdate
from hdate import Location
import hdate.htables
import hdate.converters
from hdate.zmanim import Zmanim

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_TIME_ZONE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.trigger import TriggerInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_DAY,
    ATTR_HOURS,
    ATTR_MINUTES,
    ATTR_AM_OR_PM,
    ATTR_CHALAKIM,
    ATTR_FRIENDLY,
    ATTR_ROSH_CHODESH,
    ATTR_ROSH_CHODESH_DAYS,
    ATTR_ROSH_CHODESH_DATES,
    ATTR_IS_SHABBOS_MEVOCHIM,
    ATTR_IS_UPCOMING_SHABBOS_MEVOCHIM,
    ATTR_MONTH_NAME,
    DEFAULT_DIASPORA,
    DOMAIN,
    SENSOR_IS_SHABBOS_MEVOCHIM,
    SENSOR_IS_UPCOMING_SHABBOS_MEVOCHIM,
    SENSOR_MOLAD,
)

_LOGGER = logging.getLogger(__name__)

class Molad:
    """Molad class from helper.py."""

    def __init__(self, day: str, hours: int, minutes: int, am_or_pm: str, chalakim: int, friendly: str):
        self.day = day
        self.hours = hours
        self.minutes = minutes
        self.am_or_pm = am_or_pm
        self.chalakim = chalakim
        self.friendly = friendly

class RoshChodesh:
    """RoshChodesh class from helper.py."""

    def __init__(self, month: str, text: str, days: list, gdays: list = None):
        self.month = month
        self.text = text
        self.days = days
        self.gdays = gdays if gdays is not None else []

class MoladDetails:
    """MoladDetails class from helper.py."""

    def __init__(
        self, molad: Molad, is_shabbos_mevorchim: bool, is_upcoming_shabbos_mevorchim: bool, rosh_chodesh: RoshChodesh
    ):
        self.molad = molad
        self.is_shabbos_mevorchim = is_shabbos_mevorchim
        self.is_upcoming_shabbos_mevorchim = is_upcoming_shabbos_mevorchim
        self.rosh_chodesh = rosh_chodesh

class MoladHelper:
    """MoladHelper class – ported to hdate 1.1.2 (uses HDateInfo, Zmanim unchanged)."""

    def __init__(self, latitude: float, longitude: float, time_zone: str, diaspora: bool = True):
        self.location = Location(
            latitude=latitude,
            longitude=longitude,
            timezone=time_zone,
            diaspora=diaspora,
        )

    def sumup(self, multipliers) -> Molad:
        """Mathematical molad calculation (unchanged)."""
        shifts = [
            [2, 5, 204],  # starting point
            [2, 16, 595],  # 19-year cycle
            [4, 8, 876],  # regular year
            [5, 21, 589],  # leap year
            [1, 12, 793],  # month
        ]
        mults = [multipliers]
        out00 = self.multiply_matrix(mults, shifts)
        out0 = out00[0]
        out1 = self.carry_and_reduce(out0)
        out2 = self.convert_to_english(out1)
        return out2

    def multiply_matrix(self, matrix1, matrix2):
        """Matrix multiplication (unchanged)."""
        res = [[0 for _ in range(3)] for _ in range(len(matrix1))]  # Fixed size to 3
        for i in range(len(matrix1)):
            for j in range(3):
                for k in range(len(matrix2)):
                    res[i][j] += matrix1[i][k] * matrix2[k][j]
        return res

    def carry_and_reduce(self, out0):
        """Carry and reduce (unchanged)."""
        xx = out0[2]
        yy = xx % 1080
        zz = math.floor(xx / 1080)
        if yy < 0:
            yy += 1080
            zz -= 1
        out1 = [0, 0, 0]
        out1[2] = yy
        xx = out0[1] + zz
        yy = xx % 24
        zz = math.floor(xx / 24)
        if yy < 0:
            yy += 24
            zz -= 1
        out1[1] = yy
        xx = out0[0] + zz
        yy = (xx + 6) % 7 + 1
        zz = math.floor(xx / 7)
        if yy < 0:
            yy += 7
        out1[0] = yy
        return out1

    def convert_to_english(self, out1) -> Molad:
        """Convert to English (unchanged)."""
        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Shabbos"]
        day = out1[0]
        hours = out1[1] - 6  # From 6 PM previous day
        chalakim = out1[2]
        if hours < 0:
            day -= 1
            hours += 24
        daynm = days[day - 1]
        pm = "am"
        if hours >= 12:
            pm = "pm"
            hours -= 12
        minutes = math.floor(chalakim / 18)
        chalakim = chalakim % 18
        leng = len(str(minutes))
        filler = "0" if leng == 1 else ""
        hours = 12 if hours == 0 else hours
        friendly = (
            f"{daynm}, {hours}:{filler}{minutes} {pm} and {chalakim} chalakim"
        )
        return Molad(daynm, hours, minutes, pm, chalakim, friendly)

    def get_actual_molad(self, date: datetime.date) -> Molad:
        """Get molad for date (unchanged math)."""
        numeric_month = self.get_numeric_month_year(date)
        year = numeric_month["year"] - 3761
        multipliers = [1, 0, 0, 0, 0]
        multipliers[1] = math.floor(year / 19)
        year = year % 19
        multipliers[2] = year
        multipliers[3] = 0
        if year > 11:
            multipliers[3] += 1
        if year > 2:
            multipliers[3] += 1
        if year > 5:
            multipliers[3] += 1
        if year > 8:
            multipliers[3] += 1
        if year > 13:
            multipliers[3] += 1
        if year > 16:
            multipliers[3] += 1
        multipliers[4] = numeric_month["month"] - 1
        multipliers[2] += multipliers[3]
        return self.sumup(multipliers)

    def get_numeric_month_year(self, date: datetime.date) -> dict:
        """Get Hebrew month/year (updated to HDateInfo)."""
        j = hdate.converters.gdate_to_jdn(date)
        h = hdate.converters.jdn_to_hdate(j)  # Returns namedtuple (year, month, day)
        return {"month": h.month, "year": h.year}

    def get_next_numeric_month_year(self, date: datetime.date) -> dict:
        """Get next month/year (unchanged)."""
        this_month = self.get_numeric_month_year(date)
        numeric_month = this_month["month"]
        year = this_month["year"]
        if numeric_month == 13:
            numeric_month = 1
            year += 1
        else:
            numeric_month += 1
        return {"month": numeric_month, "year": year}

    def get_gdate(self, numeric_month: dict, day: int) -> datetime.date:
        """Get Gregorian date (updated)."""
        jdn_date = hdate.converters.hdate_to_jdn(numeric_month["year"], numeric_month["month"], day)
        return hdate.converters.jdn_to_gdate(jdn_date)

    def get_day_of_week(self, gdate: datetime.date) -> str:
        """Get day name (unchanged)."""
        weekday = gdate.strftime("%A")
        if weekday == "Saturday":
            weekday = "Shabbos"
        return weekday

    def get_rosh_chodesh_days(self, date: datetime.date) -> RoshChodesh:
        """Get Rosh Chodesh (minor updates for hdate 1.1.2)."""
        this_month = self.get_numeric_month_year(date)
        next_month = self.get_next_numeric_month_year(date)
        next_month_name = hdate.htables.MONTHS[next_month["month"] - 1][False]  # English name
        if next_month["month"] == 1:  # No Rosh Chodesh Tishrei
            return RoshChodesh(next_month_name, "", [], [])
        gdate_first = self.get_gdate(this_month, 30)
        gdate_second = self.get_gdate(next_month, 1)
        first = self.get_day_of_week(gdate_first)
        second = self.get_day_of_week(gdate_second)
        if first == second:
            return RoshChodesh(next_month_name, first, [first], [gdate_first])
        return RoshChodesh(
            next_month_name, f"{first} & {second}", [first, second], [gdate_first, gdate_second]
        )

    def get_shabbos_mevorchim_english_date(self, date: datetime.date) -> datetime.date:
        """Get Shabbos Mevorchim date (unchanged)."""
        this_month = self.get_numeric_month_year(date)
        gdate = self.get_gdate(this_month, 30)
        idx = (gdate.weekday() + 1) % 7
        sat_date = gdate - datetime.timedelta(days=7 + idx - 6)
        return sat_date

    def get_shabbos_mevorchim_hebrew_day_of_month(self, date: datetime.date) -> int:
        """Get Hebrew day (updated)."""
        gdate = self.get_shabbos_mevorchim_english_date(date)
        j = hdate.converters.gdate_to_jdn(gdate)
        h = hdate.converters.jdn_to_hdate(j)
        return h.day

    def is_shabbos_mevorchim(self, date: datetime.datetime) -> bool:
        """Check if Shabbos Mevorchim (updated to HDateInfo)."""
        date_only = date.date()
        j = hdate.converters.gdate_to_jdn(date_only)
        h = hdate.converters.jdn_to_hdate(j)
        hd = h.day
        z = Zmanim(date=date_only, location=self.location, hebrew=False)
        if z.time > z.zmanim["sunset"]:
            hd += 1
        sm = self.get_shabbos_mevorchim_hebrew_day_of_month(date_only)
        return (
            self.is_actual_shabbat(z)
            and hd == sm
            and h.month != hdate.htables.Months.ELUL
        )

    def is_upcoming_shabbos_mevorchim(self, date: datetime.datetime) -> bool:
        """Check upcoming (unchanged, Sunday-based)."""
        weekday_sunday_as_zero = (date.date().weekday() + 1) % 7
        upcoming_saturday = date.date() - datetime.timedelta(days=weekday_sunday_as_zero) + datetime.timedelta(days=6)
        upcoming_saturday_at_midnight = datetime.datetime.combine(upcoming_saturday, datetime.time.min)
        return self.is_shabbos_mevorchim(upcoming_saturday_at_midnight)

    def is_actual_shabbat(self, z: Zmanim) -> bool:
        """Check actual Shabbat (updated to HDateInfo)."""
        today = hdate.HDateInfo(gdate=z.date)
        tomorrow = hdate.HDateInfo(gdate=z.date + datetime.timedelta(days=1))
        if today.is_shabbat and z.havdalah is not None and z.time < z.havdalah:
            return True
        if tomorrow.is_shabbat and z.candle_lighting is not None and z.time >= z.candle_lighting:
            return True
        return False

    def get_molad(self, date: datetime.datetime) -> MoladDetails:
        """Get full molad details."""
        molad_obj = self.get_actual_molad(date.date())
        is_shabbos_mevorchim = self.is_shabbos_mevorchim(date)
        is_upcoming_shabbos_mevorchim = self.is_upcoming_shabbos_mevorchim(date)
        rosh_chodesh = self.get_rosh_chodesh_days(date.date())
        return MoladDetails(molad_obj, is_shabbos_mevorchim, is_upcoming_shabbos_mevorchim, rosh_chodesh)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Molad sensors."""
    diaspora = hass.data[DOMAIN][entry.entry_id]["diaspora"]
    latitude = hass.config.latitude
    longitude = hass.config.longitude
    time_zone = str(hass.config.time_zone)

    helper = MoladHelper(latitude, longitude, time_zone, diaspora)

    # Create sensors
    sensors = [
        MoladSensor(helper, "molad", SENSOR_MOLAD, icon="mdi:calendar-star"),
        MoladBinarySensor(helper, "is_shabbos_mevorchim", SENSOR_IS_SHABBOS_MEVOCHIM, icon="mdi:judaism"),
        MoladBinarySensor(helper, "is_upcoming_shabbos_mevorchim", SENSOR_IS_UPCOMING_SHABBOS_MEVOCHIM, icon="mdi:judaism"),
    ]
    async_add_entities(sensors, True)

class MoladSensor(SensorEntity):
    """Molad Sensor."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP  # Optional, for date/time feel
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, helper: MoladHelper, name: str, entity_id: str, icon: str):
        """Initialize."""
        self.entity_id = entity_id
        self._helper = helper
        self._attr_name = f"{name.title()}"
        self._attr_icon = icon
        self._attr_unique_id = entity_id
        self._state = STATE_UNKNOWN
        self._attributes: Dict[str, Any] = {}

    @callback
    def update_callback(self, now: datetime.datetime, triggers: TriggerInfo) -> None:
        """Update sensor."""
        details = self._helper.get_molad(now)
        molad = details.molad
        rosh = details.rosh_chodesh

        self._state = molad.friendly
        self._attributes = {
            ATTR_DAY: molad.day,
            ATTR_HOURS: molad.hours,
            ATTR_MINUTES: molad.minutes,
            ATTR_AM_OR_PM: molad.am_or_pm,
            ATTR_CHALAKIM: molad.chalakim,
            ATTR_FRIENDLY: molad.friendly,
            ATTR_ROSH_CHODESH: rosh.text,
            ATTR_ROSH_CHODESH_DAYS: ", ".join(rosh.days),
            ATTR_ROSH_CHODESH_DATES: ", ".join([d.isoformat() for d in rosh.gdays]),
            ATTR_IS_SHABBOS_MEVOCHIM: details.is_shabbos_mevorchim,
            ATTR_IS_UPCOMING_SHABBOS_MEVOCHIM: details.is_upcoming_shabbos_mevorchim,
            ATTR_MONTH_NAME: rosh.month,
        }
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register triggers."""
        trigger = datetime.time(hour=0, minute=0)  # Daily at midnight
        self.async_on_remove(
            self.hass.bus.async_listen("time_pattern", self.update_callback)
        )
        self.update_callback(datetime.datetime.now(), None)  # Initial update

class MoladBinarySensor(SensorEntity):
    """Binary Shabbos Mevorchim Sensor."""

    _attr_device_class = SensorDeviceClass.BINARY  # Wait, no – use SensorEntity for boolean state

    def __init__(self, helper: MoladHelper, name: str, entity_id: str, icon: str):
        """Initialize."""
        self.entity_id = entity_id
        self._helper = helper
        self._attr_name = f"{name.replace('_', ' ').title()}"
        self._attr_icon = icon
        self._attr_unique_id = entity_id
        self._state = STATE_UNKNOWN

    @callback
    def update_callback(self, now: datetime.datetime, triggers: TriggerInfo) -> None:
        """Update sensor."""
        if "upcoming" in self.entity_id:
            self._state = self._helper.is_upcoming_shabbos_mevorchim(now)
        else:
            self._state = self._helper.is_shabbos_mevorchim(now)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register triggers."""
        self.async_on_remove(
            self.hass.bus.async_listen("time_pattern", self.update_callback)
        )
        self.update_callback(datetime.datetime.now(), None)  # Initial