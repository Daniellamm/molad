# Molad Sensor for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![GitHub Release](https://img.shields.io/github/v/release/Daniellamm/molad)](https://github.com/Daniellamm/molad/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Molad (New Moon) Sensor with Rosh Chodesh & Shabbos Mevorchim alerts** — **fully standalone, no external Python package required.**

> **Originally created by [@chaimchaikin](https://github.com/chaimchaikin/molad-ha)**  
> **Upgraded & maintained by [@Daniellamm](https://github.com/Daniellamm)**

---

## Features

| Feature | Included |
|-------|----------|
| `sensor.molad` with **12 detailed attributes** | Yes |
| `sensor.is_shabbos_mevorchim` | Yes |
| `sensor.is_upcoming_shabbos_mevorchim` | Yes |
| Uses **only `hdate[astral]==1.1.2`** | Yes |
| **No external `molad` package needed** | Yes |
| Daily update at midnight | Yes |
| HACS‑ready | Yes |
| Works in Israel & Diaspora | Yes |

---

## Sensors

### 1. `sensor.molad`
**State**: Human‑readable molad time  
**Attributes**:

| Attribute | Description | Example |
|---------|-----------|--------|
| `day` | Day of the week | `Sunday` |
| `hours` | Hour (12‑hour) | `3` |
| `minutes` | Minutes | `36` |
| `am_or_pm` | AM/PM | `pm` |
| `chalakim` | Parts (1/18 minute) | `15` |
| `friendly` | Full text | `Sunday, 3:36 pm and 15 chalakim` |
| `rosh_chodesh` | Rosh Chodesh days | `Monday & Tuesday` |
| `rosh_chodesh_days` | List of days | `Monday, Tuesday` |
| `rosh_chodesh_dates` | Gregorian dates | `2024‑12‑31, 2025‑01‑01` |
| `is_shabbos_mevorchim` | Today is Shabbos Mevorchim | `false` |
| `is_upcoming_shabbos_mevorchim` | Upcoming Shabbos is Mevorchim | `false` |
| `month_name` | Hebrew month name | `Tammuz` |

---

### 2. `sensor.is_shabbos_mevorchim`
- `true` if **today** is Shabbos Mevorchim
- `false` otherwise

---

### 3. `sensor.is_upcoming_shabbos_mevorchim`
- `true` if the **next Saturday** is Shabbos Mevorchim
- `false` otherwise
> **Note**: Counts from Sunday (same as original)

---

## Installation

### Option 1: HACS (Recommended)

1. In **HACS → Integrations**
2. Click **three dots → Custom repositories**
3. Add:
   - **URL**: `https://github.com/Daniellamm/molad`
   - **Category**: `Integration`
4. Click **Add**
5. Search **"Molad" → Install**
6. **Restart Home Assistant**

---

### Option 2: Manual

1. Copy the `molad` folder to your Home Assistant config directory at:  
   `config/custom_components/molad/`  
   *(On most systems: `/config/custom_components/molad/`)*

2. Restart Home Assistant

> **Tip**: Use **File Editor** (in HA) or **Samba/FTP** to access the `config` folder.

---

## Configuration (Optional)

```yaml
# configuration.yaml
molad:
  diaspora: true  # Set to false if in Israel
```

> Default: `true` (diaspora timing)

---

## Example Dashboard Card

```yaml
type: entities
title: Molad & Rosh Chodesh
entities:
  - entity: sensor.molad
    name: Next Molad
  - entity: sensor.is_shabbos_mevorchim
    name: Today is Shabbos Mevorchim
  - entity: sensor.is_upcoming_shabbos_mevorchim
    name: Upcoming Shabbos is Mevorchim
```


---

## Credits & Thanks

- **Original Author**: [@chaimchaikin](https://github.com/chaimchaikin)  
  → Created the original [molad‑ha](https://github.com/chaimchaikin/molad-ha) HACS integration
- **Mathematical Molad Logic**: Based on `hdate` and traditional Jewish calendar calculations
- **Maintained & Upgraded**: [@Daniellamm](https://github.com/Daniellamm)  
  → Made it **standalone**, **HACS‑ready**, and **fully self‑contained**

---

## License

[MIT License](LICENSE) — free to use, modify, and distribute.

---

## Support

- Open an [issue](https://github.com/Daniellamm/molad/issues)
- Or message me on [GitHub](https://github.com/Daniellamm)

