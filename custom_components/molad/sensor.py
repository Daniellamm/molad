"""Support for Molad sensors - CORRECTED VERSION."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

import hdate
from hdate.hebrew_date import HebrewDate
from hdate.translator import set_language
from zoneinfo import ZoneInfo

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


class MoladHelper:
    # === CONSTANTS ===
    CHALAKIM_PER_HOUR = 1080
    CHALAKIM_PER_DAY = 24 * CHALAKIM_PER_HOUR
    CHALAKIM_PER_WEEK = 7 * CHALAKIM_PER_DAY
    LUNAR_MONTH_CHALAKIM = 29 * CHALAKIM_PER_DAY + 12 * CHALAKIM_PER_HOUR + 793  # 765433

    # Reference: Molad Tishrei, Year 1 = Monday 5h 204p (Hebrew time)
    # Hebrew time: Day 2 (Monday), Hour 5 (5 hours after 6pm Sunday)
    # Civil time: Sunday 11:11:20 PM
    REF_YEAR = 1
    REF_MONTH = 7  # Tishrei
    REF_DAY_OF_WEEK = 2  # Monday (Hebrew day, where Monday starts Sunday 6pm)
    REF_HOURS = 5  # Hebrew hours (hours after 6pm)
    REF_CHALAKIM = 204

    # Leap years in 19-year cycle: years 3,6,8,11,14,17,19
    LEAP_YEARS_IN_CYCLE = {3, 6, 8, 11, 14, 17, 19}

    def __init__(self, latitude: float, longitude: float, time_zone: str, diaspora: bool = True):
        set_language("en")
        self.location = hdate.Location(
            latitude=latitude,
            longitude=longitude,
            timezone=time_zone,
            diaspora=diaspora,
        )
        self.tz = ZoneInfo(time_zone)

    # === LEAP YEAR (FIXED) ===
    @staticmethod
    def _is_leap_year(year: int) -> bool:
        """Check if a Hebrew year is a leap year.
        
        Fixed: Year 19 (and 38, 57, etc.) are leap years.
        The issue was that 19 % 19 = 0, not 19.
        """
        position = year % 19
        if position == 0:
            position = 19  # Year 19 of cycle, not year 0
        return position in MoladHelper.LEAP_YEARS_IN_CYCLE

    # === MOLAD WITH LEAP YEARS (CORRECT) ===
    def _molad_raw(self, year: int, month: int) -> tuple[int, int, int, int]:
        """Calculate molad using full Metonic cycle (235 months per 19 years).
        
        Returns tuple of (day, hours_hebrew, minutes, chalakim) where hours are in Hebrew time.
        """
        years_from_ref = year - self.REF_YEAR  # e.g., year 5785 → 5784 years

        # Complete 19-year cycles
        complete_cycles = years_from_ref // 19
        total_months = complete_cycles * 235  # 19 years = 235 months

        # Remaining years in partial cycle
        remaining_years = years_from_ref % 19
        for y in range(1, remaining_years + 1):
            cycle_year = y
            total_months += 13 if cycle_year in self.LEAP_YEARS_IN_CYCLE else 12

        # Add months in current year up to target month
        # Hebrew year starts at Tishrei (month 7)
        if month >= 7:
            # Tishrei to target month
            total_months += (month - 7)  # Tishrei = 0 extra
        else:
            # Nisan to target month
            months_from_tishrei = 6  # Tishrei to Adar I
            if self._is_leap_year(year):
                months_from_tishrei = 7  # Tishrei to Adar II
            total_months += months_from_tishrei + (month - 1)  # Nisan = month 1

        # Total chalakim
        total_chalakim = total_months * self.LUNAR_MONTH_CHALAKIM
        total_chalakim += (self.REF_DAY_OF_WEEK - 1) * self.CHALAKIM_PER_DAY
        total_chalakim += self.REF_HOURS * self.CHALAKIM_PER_HOUR
        total_chalakim += self.REF_CHALAKIM
        total_chalakim %= self.CHALAKIM_PER_WEEK

        # Extract (returns Hebrew time)
        days = total_chalakim // self.CHALAKIM_PER_DAY + 1
        remainder = total_chalakim % self.CHALAKIM_PER_DAY
        hours = remainder // self.CHALAKIM_PER_HOUR
        remainder %= self.CHALAKIM_PER_HOUR
        minutes = remainder // 18
        chalakim = remainder % 18

        return days, hours, minutes, chalakim

    def _raw_to_molad(self, raw: tuple[int, int, int, int]) -> Molad:
        """Convert raw molad to Molad object.
        
        Fixed: Now converts Hebrew hours to civil hours for traditional announcements.
        Hebrew time starts at 6pm, so we subtract 6 hours to get civil time.
        """
        day_num, hours_hebrew, minutes, chalakim = raw
        days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Shabbos"]
        
        # Convert from Hebrew hours (starting at 6pm) to civil hours (starting at midnight)
        # Hebrew hour 0 = 6pm civil (18:00)
        # Hebrew hour 5 = 11pm civil (23:00)
        # Hebrew hour 18 = noon civil (12:00)
        civil_hours = hours_hebrew - 6
        if civil_hours < 0:
            civil_hours += 24
            # Going back before midnight means previous civil day
            day_num = day_num - 1 if day_num > 1 else 7
        
        day_name = days[day_num - 1]
        am_pm = "am" if civil_hours < 12 else "pm"
        hours12 = civil_hours % 12
        hours12 = 12 if hours12 == 0 else hours12

        filler = "0" if minutes < 10 else ""
        friendly = f"{day_name}, {hours12}:{filler}{minutes} {am_pm} and {chalakim} chalakim"

        return Molad(day_name, hours12, minutes, am_pm, chalakim, friendly)

    def get_actual_molad(self, gdate: datetime.date) -> Molad:
        h = HebrewDate.from_gdate(gdate)
        raw = self._molad_raw(h.year, h.month)
        return self._raw_to_molad(raw)

    # === HELPERS ===
    @staticmethod
    def _hebrew_month_year(gdate: datetime.date) -> dict:
        h = HebrewDate.from_gdate(gdate)
        return {"year": h.year, "month": h.month}

    @staticmethod
    def _next_hebrew_month(cur: dict) -> dict:
        if cur["month"] == 13:
            return {"month": 1, "year": cur["year"] + 1}
        return {"month": cur["month"] + 1, "year": cur["year"]}

    @staticmethod
    def _gdate_from_hebrew(hinfo: dict, day: int) -> datetime.date:
        h = HebrewDate(hinfo["year"], hinfo["month"], day)
        return h.to_gdate()

    @staticmethod
    def _dow_name(gdate: datetime.date) -> str:
        name = gdate.strftime("%A")
        return "Shabbos" if name == "Saturday" else name

    # === ROSH CHODESH ===
    def get_rosh_chodesh_days(self, gdate: datetime.date) -> RoshChodesh:
        cur = self._hebrew_month_year(gdate)
        nxt = self._next_hebrew_month(cur)
        g_second = self._gdate_from_hebrew(nxt, 1)
        second_dow = self._dow_name(g_second)
        info = hdate.HDateInfo(g_second)
        month_name = info.hdate.month.name

        if nxt["month"] == 7:  # Tishrei
            return RoshChodesh(month_name, "", [], [])

        try:
            g_first = self._gdate_from_hebrew(cur, 30)
            first_dow = self._dow_name(g_first)
            return RoshChodesh(month_name, f"{first_dow} & {second_dow}", [first_dow, second_dow], [g_first, g_second])
        except ValueError:
            return RoshChodesh(month_name, second_dow, [second_dow], [g_second])

    # === SHABBOS MEVORCHIM (FIXED) ===
    def _shabbos_mevorchim_date(self, gdate: datetime.date) -> datetime.date:
        cur = self._hebrew_month_year(gdate)
        has_30_days = False
        try:
            last = self._gdate_from_hebrew(cur, 30)
            has_30_days = True
        except ValueError:
            last = self._gdate_from_hebrew(cur, 29)

        days_back = (last.weekday() - 5) % 7
        if days_back == 0 and has_30_days:
            days_back = 7
        return last - timedelta(days=days_back)

    def _shabbos_mevorchim_hebrew_day(self, gdate: datetime.date) -> datetime.date:
        return self._shabbos_mevorchim_date(gdate)

    # === SHABBOS MEVORCHIM DETECTION (FRIDAY EVENING FIXED) ===
    def is_shabbos_mevorchim(self, now: datetime) -> bool:
        today = now.date()
        z = hdate.Zmanim(date=today, location=self.location)

        # Determine correct Hebrew date during Shabbat
        if self._is_actual_shabbat(z, now):
            # During Shabbat: use Saturday's date
            if today.weekday() == 5:  # Saturday
                h_date = today
            else:  # Friday evening
                h_date = today + timedelta(days=1)
        else:
            h_date = today

        h = HebrewDate.from_gdate(h_date)
        hd = h.day
        target_date = self._shabbos_mevorchim_hebrew_day(today)
        target_hd = HebrewDate.from_gdate(target_date).day

        return self._is_actual_shabbat(z, now) and hd == target_hd and h.month != 6

    def is_upcoming_shabbos_mevorchim(self, now: datetime) -> bool:
        wd = (now.date().weekday() + 1) % 7
        next_sat = now.date() - timedelta(days=wd) + timedelta(days=6)
        next_sat_dt = datetime.combine(next_sat, now.time())
        if now.tzinfo:
            next_sat_dt = next_sat_dt.replace(tzinfo=now.tzinfo)
        return self.is_shabbos_mevorchim(next_sat_dt)

    def _is_actual_shabbat(self, z: hdate.Zmanim, now: datetime) -> bool:
        """Check if now is during Shabbat (Friday evening to Saturday evening)."""
        if now.tzinfo is None:
            now = now.replace(tzinfo=self.tz)
        today = hdate.HDateInfo(z.date)
        tomorrow = hdate.HDateInfo(z.date + timedelta(days=1))
        
        # Saturday during the day until Havdalah
        if today.is_shabbat and z.havdalah and now < z.havdalah:
            return True
        # Friday evening after candle lighting
        if tomorrow.is_shabbat and z.candle_lighting and now >= z.candle_lighting:
            return True
        return False

    def get_molad(self, now: datetime) -> MoladDetails:
        molad_obj = self.get_actual_molad(now.date())
        shabbos_now = self.is_shabbos_mevorchim(now)
        shabbos_next = self.is_upcoming_shabbos_mevorchim(now)
        rosh = self.get_rosh_chodesh_days(now.date())
        return MoladDetails(molad_obj, shabbos_now, shabbos_next, rosh)


class MoladDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, diaspora: bool):
        self.helper = MoladHelper(hass.config.latitude, hass.config.longitude, str(hass.config.time_zone), diaspora)
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(minutes=30))

    async def _async_update_data(self):
        now = datetime.now(tz=self.helper.tz)
        details = self.helper.get_molad(now)
        m, r = details.molad, details.rosh_chodesh
        return {
            "state": m.friendly,
            "attributes": {
                ATTR_DAY: m.day,
                ATTR_HOURS: m.hours,
                ATTR_MINUTES: m.minutes,
                ATTR_AM_OR_PM: m.am_or_pm,
                ATTR_CHALAKIM: m.chalakim,
                ATTR_FRIENDLY: m.friendly,
                ATTR_ROSH_CHODESH: r.text,
                ATTR_ROSH_CHODESH_DAYS: ", ".join(r.days),
                ATTR_ROSH_CHODESH_DATES: ", ".join(d.isoformat() for d in r.gdays),
                ATTR_IS_SHABBOS_MEVOCHIM: details.is_shabbos_mevorchim,
                ATTR_IS_UPCOMING_SHABBOS_MEVOCHIM: details.is_upcoming_shabbos_mevorchim,
                ATTR_MONTH_NAME: r.month,
            },
        }


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_config_entry_first_refresh()
    async_add_entities([
        MoladSensor(coordinator),
        ShabbosMevorchimSensor(coordinator, True),
        ShabbosMevorchimSensor(coordinator, False),
    ])


class MoladSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:moon-waning-crescent"
    def __init__(self, coordinator): super().__init__(coordinator); self._attr_unique_id = f"{DOMAIN}_{SENSOR_MOLAD}"; self._attr_name = "Molad"
    @property def native_value(self): return self.coordinator.data["state"]
    @property def extra_state_attributes(self): return self.coordinator.data["attributes"]


class ShabbosMevorchimSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, is_today: bool):
        super().__init__(coordinator)
        self.is_today = is_today
        key = SENSOR_IS_SHABBOS_MEVOCHIM if is_today else SENSOR_IS_UPCOMING_SHABBOS_MEVOCHIM
        self._attr_unique_id = f"{DOMAIN}_{key}"
        self._attr_name = "Today is Shabbos Mevorchim" if is_today else "Upcoming Shabbos is Mevorchim"
        self._attr_icon = "mdi:judaism"
    @property def native_value(self): return self.coordinator.data["attributes"].get(ATTR_IS_SHABBOS_MEVOCHIM if self.is_today else ATTR_IS_UPCOMING_SHABBOS_MEVOCHIM, False)
    @property def is_on(self): return self.native_value
