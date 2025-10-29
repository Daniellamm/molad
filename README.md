# Molad Sensor for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![GitHub Release](https://img.shields.io/github/v/release/Daniellamm/molad)](https://github.com/Daniellamm/molad/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive Home Assistant integration for tracking the **Molad** (Jewish lunar month calculation) with automatic **Shabbos Mevorchim** alerts and **Rosh Chodesh** information.

> **Originally created by** [@chaimchaikin](https://github.com/chaimchaikin/molad-ha)  
> **Upgraded & maintained by** [@Daniellamm](https://github.com/Daniellamm)

---

## ✨ Features

- 🌙 **Molad Sensor** with 12 detailed attributes
- 📅 **Rosh Chodesh** dates and day-of-week information
- 🕯️ **Shabbos Mevorchim** detection (today & upcoming)
- 🔄 **Automatic daily updates** at midnight
- 🌍 **Works in Israel & Diaspora** with configurable settings
- 📦 **Fully standalone** - only requires `hdate[astral]==1.1.2`
- 🎯 **HACS-ready** for easy installation

---

## 📊 Sensors

### 1. `sensor.molad`

Displays the Molad time for the upcoming Rosh Chodesh.

**State**: Human-readable molad time (e.g., `"Thursday, 1:38 pm and 9 chalakim"`)

**Attributes**:

| Attribute | Description | Example |
|-----------|-------------|---------|
| `day` | Day of the week | `Thursday` |
| `hours` | Hour (12-hour format) | `1` |
| `minutes` | Minutes | `38` |
| `am_or_pm` | AM or PM | `pm` |
| `chalakim` | Parts (1 chelek = 1/18 minute) | `9` |
| `friendly` | Full formatted text | `Thursday, 1:38 pm and 9 chalakim` |
| `rosh_chodesh` | Rosh Chodesh day(s) | `Friday` |
| `rosh_chodesh_days` | Comma-separated days | `Friday` |
| `rosh_chodesh_dates` | Gregorian date(s) | `2025-11-20` |
| `is_shabbos_mevorchim` | Is today Shabbos Mevorchim? | `false` |
| `is_upcoming_shabbos_mevorchim` | Is upcoming Shabbos Mevorchim? | `false` |
| `month_name` | Hebrew month name | `KISLEV` |

---

### 2. `sensor.is_shabbos_mevorchim`

Binary sensor indicating if **today** is Shabbos Mevorchim.

**State**: `true` or `false`

---

### 3. `sensor.is_upcoming_shabbos_mevorchim`

Binary sensor indicating if the **next Shabbos** is Shabbos Mevorchim.

**State**: `true` or `false`

> **Note**: Counts from Sunday through Saturday of the current week.

---

## 📥 Installation

### Method 1: HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Go to **Integrations**
3. Click the **⋮** (three dots) menu → **Custom repositories**
4. Add the following:
   - **Repository**: `https://github.com/Daniellamm/molad`
   - **Category**: `Integration`
5. Click **Add**
6. Search for **"Molad"** in HACS
7. Click **Download**
8. **Restart Home Assistant**
9. Go to **Settings** → **Devices & Services** → **Add Integration** → Search for **"Molad"**
10. Configure your location (Israel or Diaspora)

---

### Method 2: Manual Installation

1. Download the `molad` folder from this repository
2. Copy it to your Home Assistant config directory:
   ```
   config/custom_components/molad/
   ```
3. **Restart Home Assistant**
4. Go to **Settings** → **Devices & Services** → **Add Integration** → Search for **"Molad"**
5. Configure your location (Israel or Diaspora)

> **Tip**: Use the **File Editor** add-on or **Samba/SSH** to access your config folder.

---

## ⚙️ Configuration

The integration uses a config flow (GUI setup), but you can also configure it via YAML:

```yaml
# configuration.yaml (optional)
molad:
  diaspora: true  # Set to false if in Israel
```

**Default**: `diaspora: true`

---

## 🎨 Example Dashboard Card

### Basic Card

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

### Advanced Card with Attributes

```yaml
type: custom:stack-in-card
cards:
  - type: markdown
    content: |
      ## 🌙 Molad for {{ state_attr('sensor.molad', 'month_name') }}
      
      **Molad Time**: {{ states('sensor.molad') }}  
      **Rosh Chodesh**: {{ state_attr('sensor.molad', 'rosh_chodesh') }}  
      **Date**: {{ state_attr('sensor.molad', 'rosh_chodesh_dates') }}
      
      {% if is_state('sensor.is_shabbos_mevorchim', 'true') %}
      🕯️ **Today is Shabbos Mevorchim!**
      {% elif is_state('sensor.is_upcoming_shabbos_mevorchim', 'true') %}
      📅 **Upcoming Shabbos is Mevorchim**
      {% endif %}
```

---

### Automation Example

Get notified before Shabbos Mevorchim:

```yaml
automation:
  - alias: "Notify Before Shabbos Mevorchim"
    trigger:
      - platform: state
        entity_id: sensor.is_upcoming_shabbos_mevorchim
        to: "true"
    action:
      - service: notify.mobile_app
        data:
          title: "Shabbos Mevorchim This Week"
          message: >
            The upcoming Shabbos is Shabbos Mevorchim!
            Molad: {{ states('sensor.molad') }}
            Rosh Chodesh: {{ state_attr('sensor.molad', 'month_name') }}
            on {{ state_attr('sensor.molad', 'rosh_chodesh_dates') }}
```

---

## 🔧 Troubleshooting

### Sensor Not Updating

1. Check that the integration is properly installed
2. Restart Home Assistant
3. Check the logs for errors: **Settings** → **System** → **Logs**

### Wrong Times Displayed

Make sure your Home Assistant **timezone** is set correctly:
- Go to **Settings** → **System** → **General** → **Time Zone**

### Diaspora vs. Israel

The `diaspora` setting affects how Shabbos times are calculated. Make sure this matches your location:
- `diaspora: true` - Outside of Israel (default)
- `diaspora: false` - In Israel

---

## 📚 Background

### What is Molad?

The **Molad** (מולד) is the astronomical moment of the new moon, calculated precisely using traditional Jewish calendar mathematics. It's announced on **Shabbos Mevorchim** (the Shabbos before Rosh Chodesh, except for the month of Tishrei).

### What are Chalakim?

A **chelek** (plural: chalakim) is a unit of time equal to **1/18 of a minute** (3⅓ seconds). The molad is traditionally specified in:
- Day of the week
- Hour (after 6pm the previous evening in Hebrew time)
- Minutes and chalakim

This integration displays the molad in **civil time** (starting at midnight) for easier understanding.

---

## 🙏 Credits & Thanks

- **Original Author**: [@chaimchaikin](https://github.com/chaimchaikin) - Created the original [molad-ha](https://github.com/chaimchaikin/molad-ha) integration
- **Mathematical Foundation**: Based on traditional Jewish calendar calculations and the `hdate` library
- **Maintained & Enhanced**: [@Daniellamm](https://github.com/Daniellamm) - Made it standalone, HACS-ready, and fully self-contained

---

## 📄 License

[MIT License](LICENSE) - Free to use, modify, and distribute.

---

## 💬 Support & Contributions

- 🐛 Found a bug? [Open an issue](https://github.com/Daniellamm/molad/issues)
- 💡 Have a feature request? [Open an issue](https://github.com/Daniellamm/molad/issues)
- 🤝 Want to contribute? Pull requests are welcome!
- 📧 Questions? Message me on [GitHub](https://github.com/Daniellamm)

---

## 🌟 Star this repo

If you find this integration useful, please give it a ⭐ on GitHub!
