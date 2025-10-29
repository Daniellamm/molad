"""Support for Molad sensors."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
import math
import pytz

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

# OFFICIAL HA STYLE — hdate 1.1.2
import hdate
from hdate.hebrew_date import HebrewDate
from hdate.translator import set_language

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
    DOMAIN,
    SENSOR_MOLAD,
    SENSOR_IS_SHABBOS_MEVOCHIM,
    SENSOR_IS_UPCOMING_SHABBOS_MEVOCHIM,
)

_LOGGER = logging.getLogger(__name__)


# === CLASSES ===
class Molad:
    def __init__(self, day: str, hours: int, minutes: int, am_or_pm: str, chalakim: int, friendly: str):
        self.day = day
        self.hours = hours
        self.minutes = minutes
        self.am_or_pm = am_or_pm
        self.chalakim = chalakim
        self.friendly = friendly


class RoshChodesh:
    def __init__(self, month: str, text: str, days: list, gdays: list | None = None):
        self.month = month
        self.text = text
        self.days = days
        self.gdays = gdays or []


class MoladDetails:
    def __init__(
        self, molad: Molad, is_shabbos_mevorchim: bool, is_upcoming_shabbos_mevorchim: bool, rosh_chodesh: RoshChodesh
    ):
        self.molad = molad
        self.is_shabbos_mevorchim = is_shabbos_mevorchim
        self.is_upcoming_shabbos_mevorchim = is_upcoming_shabbos_mevorchim
        self.rosh_chodesh = rosh_chodesh


# === MOLAD HELPER ===
class MoladHelper:
    def __init__(self, latitude: float, longitude: float, time_zone: str, diaspora: bool = True):
        set_language("en")  # SET ENGLISH
        self.location = hdate.Location(
            latitude=latitude,
            longitude=longitude,
            timezone=time_zone,
            diaspora=diaspora,
        )

    def sumup(self, multipliers) -> Molad:
        shifts = [
            [2, 5, 204],
            [2, 16, 595],
            [4, 8, 876],
            [5, 21, 589],
            [1, 12, 793],
        ]
        out00 = self.multiply_matrix([multipliers], shifts)
        out0 = out00[0]
        out1 = self.carry_and_reduce(out0)
        out2 = self.convert_to_english(out1)
        return out2

    def multiply_matrix(self, matrix1, matrix2):
        res = [[0] * 3 for _ in matrix1]
        for i in range(len(matrix1)):
            for j in range(3):
                for k in range(len(matrix2)):
                    res[i][j] += matrix1[i][k] * matrix2[k][j]
        return res

    def carry_and_reduce(self, out0):
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
        out1[0] = yy
        return out1

    def convert_to_english(self, out1) -> Molad:
        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Shabbos"]
        day = out1[0]
        hours = out1[1] - 6
        chalakim = out1[2]
        if hours < 0:
            day -= 1
            hours += 24
        daynm = days[day - 1]
        pm = "am" if hours < 12 else "pm"
        hours = hours % 12
        hours = 12 if hours == 0 else hours
        minutes = math.floor(chalakim / 18)
        chalakim = chalakim % 18
        filler = "0" if minutes < 10 else ""
        friendly = f"{daynm}, {hours}:{filler}{minutes} {pm} and {chalakim} chalakim"
        return Molad(daynm, hours, minutes, pm, chalakim, friendly)

    def get_actual_molad(self, date: datetime.date) -> Molad:
        numeric_month = self.get_numeric_month_year(date)
        year = numeric_month["year"] - 3761
        multipliers = [1, 0, 0, 0, 0]
        multipliers[1] = math.floor(year / 19)
        year = year % 19
        multipliers[2] = year
        multipliers[3] = 0
        for threshold in [3, 6, 9, 12, 14, 17]:
            if year > threshold:
                multipliers[3] += 1
        multipliers[4] = numeric_month["month"] - 1
        multipliers[2] += multipliers[3]
        return self.sumup(multipliers)

    def get_numeric_month_year(self, date: datetime.date) -> dict:
        h = HebrewDate.from_gdate(date)  # FIXED
        return {"month": h.month, "year": h.year}  # FIXED

    def get_next_numeric_month_year(self, date: datetime.date) -> dict:
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
        h = HebrewDate(numeric_month["year"], numeric_month["month"], day)  # FIXED
        return h.to_gdate()  # FIXED

    def get_day_of_week(self, gdate: datetime.date) -> str:
        weekday = gdate.strftime("%A")
        return "Shabbos" if weekday == "Saturday" else weekday

    def get_rosh_chodesh_days(self, date: datetime.date) -> RoshChodesh:
        this_month = self.get_numeric_month_year(date)
        next_month = self.get_next_numeric_month_year(date)
        next_hdate = HebrewDate(next_month["year"], next_month["month"], 1)  # FIXED
        next_month_name = next_hdate.month_name  # FIXED
        if next_month["month"] == 1:
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
        this_month = self.get_numeric_month_year(date)
        
        # Try day 30 first, fall back to day 29 if month doesn't have 30 days
        try:
            gdate = self.get_gdate(this_month, 30)
        except ValueError:
            # Month only has 29 days
            gdate = self.get_gdate(this_month, 29)
        
        idx = (gdate.weekday() + 1) % 7
        sat_date = gdate - timedelta(days=7 + idx - 6)
        return sat_date

    def get_shabbos_mevorchim_hebrew_day_of_month(self, date: datetime.date) -> int:
        gdate = self.get_shabbos_mevorchim_english_date(date)
        h = HebrewDate.from_gdate(gdate)  # FIXED
        return h.day  # FIXED

    def is_shabbos_mevorchim(self, date: datetime) -> bool:
        date_only = date.date()
        h = HebrewDate.from_gdate(date_only)
        hd = h.day
        z = hdate.Zmanim(date=date_only, location=self.location)
        
        # z.zmanim["sunset"] is a timezone-aware datetime, compare directly
        sunset = z.zmanim.get("sunset")
        if sunset and date > sunset:
            hd += 1
        
        sm = self.get_shabbos_mevorchim_hebrew_day_of_month(date_only)
        return (
            self.is_actual_shabbat(z, date)
            and hd == sm
            and h.month != 6  # Elul
        )

    def is_upcoming_shabbos_mevorchim(self, date: datetime) -> bool:
        weekday_sunday_as_zero = (date.date().weekday() + 1) % 7
        upcoming_saturday = date.date() - timedelta(days=weekday_sunday_as_zero) + timedelta(days=6)
        upcoming_saturday_at_midnight = datetime.combine(upcoming_saturday, datetime.min.time())
        return self.is_shabbos_mevorchim(upcoming_saturday_at_midnight)

    def is_actual_shabbat(self, z: hdate.Zmanim, current_time: datetime) -> bool:
        today = hdate.HDateInfo(z.date)
        tomorrow = hdate.HDateInfo(z.date + timedelta(days=1))
        
        # Make current_time timezone-aware if it isn't already
        if current_time.tzinfo is None:
            current_time = self.location.timezone.localize(current_time)
        
        # Check if it's Shabbat now (before havdalah)
        if today.is_shabbat and z.havdalah and current_time < z.havdalah:
            return True
        # Check if Shabbat starts soon (after candle lighting)
        if tomorrow.is_shabbat and z.candle_lighting and current_time >= z.candle_lighting:
            return True
        return False

    def get_molad(self, date: datetime) -> MoladDetails:
        molad_obj = self.get_actual_molad(date.date())
        is_shabbos_mevorchim = self.is_shabbos_mevorchim(date)
        is_upcoming_shabbos_mevorchim = self.is_upcoming_shabbos_mevorchim(date)
        rosh_chodesh = self.get_rosh_chodesh_days(date.date())
        return MoladDetails(molad_obj, is_shabbos_mevorchim, is_upcoming_shabbos_mevorchim, rosh_chodesh)


# === COORDINATOR ===
class MoladDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, diaspora: bool):
        self.helper = MoladHelper(
            hass.config.latitude,
            hass.config.longitude,
            str(hass.config.time_zone),
            diaspora,
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=30),
        )

    async def _async_update_data(self):
        now = datetime.now()
        details = self.helper.get_molad(now)
        molad = details.molad
        rosh = details.rosh_chodesh

        return {
            "state": molad.friendly,
            "attributes": {
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
            },
        }


# === SETUP ===
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        MoladSensor(coordinator),
        ShabbosMevorchimSensor(coordinator, is_today=True),
        ShabbosMevorchimSensor(coordinator, is_today=False),
    ]
    async_add_entities(entities)


# === SENSORS ===
class MoladSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:moon-waning-crescent"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{SENSOR_MOLAD}"
        self._attr_name = "Molad"

    @property
    def native_value(self):
        return self.coordinator.data["state"]

    @property
    def extra_state_attributes(self):
        return self.coordinator.data["attributes"]


class ShabbosMevorchimSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, is_today: bool):
        super().__init__(coordinator)
        self.is_today = is_today
        key = SENSOR_IS_SHABBOS_MEVOCHIM if is_today else SENSOR_IS_UPCOMING_SHABBOS_MEVOCHIM
        self._attr_unique_id = f"{DOMAIN}_{key}"
        self._attr_name = "Today is Shabbos Mevorchim" if is_today else "Upcoming Shabbos is Mevorchim"
        self._attr_icon = "mdi:judaism"

    @property
    def native_value(self):
        key = ATTR_IS_SHABBOS_MEVOCHIM if self.is_today else ATTR_IS_UPCOMING_SHABBOS_MEVOCHIM
        return self.coordinator.data["attributes"].get(key, False)

    @property
    def is_on(self):
        return self.native_value
