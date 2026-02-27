# Nutify Link — Home Assistant Integration

A custom Home Assistant integration that pulls real-time UPS metrics from a [Nutify](https://github.com/DartSteven/Nutify) server and exposes them as sensors.

## What is Nutify?

Nutify is a web-based UPS (Uninterruptible Power Supply) monitoring platform that sits on top of [Network UPS Tools (NUT)](https://networkupstools.org/). It collects UPS data, generates reports, and provides an interactive dashboard. Nutify Link bridges Nutify's REST API with Home Assistant so you can monitor your UPS health, trigger automations on power events, and track energy consumption.

---

## Requirements

- Home Assistant 2024.1 or newer
- Nutify v0.1.7 or newer running and accessible on your network
- Nutify credentials (unless `DISABLE_AUTH=true` is set on your Nutify instance)

---

## Installation

### Manual Installation

1. Copy the `nutify_link/` folder into your Home Assistant `config/custom_components/` directory:
   ```
   config/
   └── custom_components/
       └── nutify_link/
           ├── __init__.py
           ├── manifest.json
           ├── const.py
           ├── config_flow.py
           ├── coordinator.py
           ├── sensor.py
           ├── strings.json
           └── translations/
               └── en.json
   ```

2. Restart Home Assistant.

3. Go to **Settings → Integrations → Add Integration** and search for **Nutify Link**.

### HACS (Future)

This integration is not yet available in HACS. Manual installation is required.

---

## Configuration

The integration is configured via the Home Assistant UI (no YAML required).

### Setup Steps

**Step 1 — Connection:**
| Field | Description | Default |
|---|---|---|
| Host | IP address or hostname of your Nutify server | — |
| Port | Port Nutify is listening on | `5050` |
| Use SSL | Enable HTTPS (use if behind a reverse proxy with TLS) | `false` |

**Step 2 — Authentication:**
| Field | Description |
|---|---|
| Username | Your Nutify username |
| Password | Your Nutify password |

> If your Nutify instance has `DISABLE_AUTH=true` set, leave username and password fields blank (or enter any value — authentication is skipped).

### Options (after setup)

Click the gear icon on the integration card to change:
| Option | Description | Range | Default |
|---|---|---|---|
| Scan Interval | How often to poll Nutify for new data (seconds) | 10–300 | 30 |

---

## Sensors Created

All sensors are grouped under a single **Nutify Link UPS** device.

### Battery

| Sensor | Unit | Description |
|---|---|---|
| Battery Charge | % | Current battery charge level |
| Battery Runtime | min | Estimated runtime remaining on battery |
| Battery Temperature | °C | Battery temperature *(see note below)* |
| Battery Voltage | V | Battery voltage |

> **Battery Temperature sensor:** This sensor is only created if your UPS hardware reports battery temperature via NUT. During the first data fetch at install time, the integration checks whether the `battery_temperature` variable is present in the NUT response. If your UPS does not expose this value, the sensor will not appear in Home Assistant at all — this is expected behaviour, not an error. UPS models that do report battery temperature will have the sensor created automatically with no extra configuration required.

### Power

| Sensor | Unit | Description |
|---|---|---|
| UPS Load | % | Current load as a percentage of nominal capacity |
| Real Power | W | Actual power consumption in watts |
| Apparent Power | VA | Apparent power (volt-amperes) |
| Nominal Power | W | UPS nominal power rating |

### Voltage & Frequency

| Sensor | Unit | Description |
|---|---|---|
| Input Voltage | V | Mains/utility input voltage |
| Output Voltage | V | Voltage delivered to connected devices |
| Input Frequency | Hz | Mains input frequency |
| Output Frequency | Hz | Output frequency |

### Status

| Sensor | Description |
|---|---|
| UPS Status | Raw NUT status code (OL, OB, LB, etc.) |
| UPS Status Display | Human-readable status (Online, On Battery, Low Battery, etc.) |

### Energy

| Sensor | Unit | Description |
|---|---|---|
| Energy Consumption | kWh | Cumulative energy consumed (requires Nutify energy data) |

---

## UPS Status Codes

The **UPS Status** sensor reports raw NUT status codes. The **UPS Status Display** sensor translates these:

| Code | Display |
|---|---|
| OL | Online |
| OB | On Battery |
| LB | Low Battery |
| HB | High Battery |
| RB | Replace Battery |
| CHRG | Charging |
| DISCHRG | Discharging |
| BYPASS | Bypass |
| CAL | Calibrating |
| OFF | Offline |
| OVER | Overloaded |
| TRIM | Trimming |
| BOOST | Boosting |

Statuses can be combined (e.g., `OL CHRG` = Online and Charging).

---

## API Endpoints Used

This integration polls the following Nutify endpoints:

| Endpoint | Purpose |
|---|---|
| `POST /auth/api/login` | Session authentication |
| `GET /api/data/all` | Primary UPS data (all NUT variables) |
| `GET /api/battery/metrics` | Extended battery metrics |
| `GET /api/power/metrics` | Extended power metrics |
| `GET /api/voltage/metrics` | Extended voltage metrics |

Data is merged from all endpoints and made available to all sensors.

---

## Automation Examples

### Alert when on battery power

```yaml
automation:
  - alias: "UPS - Alert on battery"
    trigger:
      - platform: state
        entity_id: sensor.nutify_link_ups_status_display
        to: "On Battery"
    action:
      - service: notify.mobile_app
        data:
          title: "Power Outage"
          message: "UPS is running on battery! Runtime remaining: {{ states('sensor.nutify_link_ups_battery_runtime') }} minutes"
```

### Alert on low battery

```yaml
automation:
  - alias: "UPS - Low battery warning"
    trigger:
      - platform: numeric_state
        entity_id: sensor.nutify_link_ups_battery_charge
        below: 20
    action:
      - service: notify.mobile_app
        data:
          title: "UPS Low Battery"
          message: "Battery charge is {{ states('sensor.nutify_link_ups_battery_charge') }}%. Shut down systems!"
```

---

## Troubleshooting

**Sensors show "Unavailable"**
- Check that Nutify is running and accessible at the configured host/port.
- Verify your credentials are correct.
- Check the Home Assistant logs: **Settings → System → Logs** and filter for `nutify_link`.

**Authentication errors after Nutify update**
- Go to **Settings → Integrations**, find Nutify Link, and click **Re-authenticate**.

**The Battery Temperature sensor is missing**
- Not all UPS models expose battery temperature via NUT. If your UPS does not report it, the sensor is intentionally not created at install time. This is normal — see the [Battery Temperature note](#battery) above.

**Some sensors are always unavailable**
- Not all UPS models expose all NUT variables. Sensors for unsupported variables will remain unavailable. If a sensor was previously working and is now unavailable, check that Nutify is healthy and the UPS is responding.

---

## Future: API Key Authentication

The Nutify developer is working on an API key mechanism. When available, this integration will be updated to support it with minimal configuration changes. No existing sensors or automations will be affected.

---

## Source

- Nutify: https://github.com/DartSteven/Nutify
- Home Assistant Custom Components: https://developers.home-assistant.io/docs/creating_component_index
