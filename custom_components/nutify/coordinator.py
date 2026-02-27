"""DataUpdateCoordinator for the Nutify UPS Monitor integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_BATTERY_METRICS,
    API_DATA_ALL,
    API_LOGIN,
    API_POWER_METRICS,
    API_VOLTAGE_METRICS,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USE_SSL,
    CONF_USERNAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class NutifyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that polls Nutify endpoints and manages session auth."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        config = entry.data
        self._host = config[CONF_HOST]
        self._port = config[CONF_PORT]
        self._use_ssl = config.get(CONF_USE_SSL, False)
        self._username = config.get(CONF_USERNAME, "")
        self._password = config.get(CONF_PASSWORD, "")
        scan_interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        self._base_url = (
            f"{'https' if self._use_ssl else 'http'}://{self._host}:{self._port}"
        )
        self._session: aiohttp.ClientSession | None = None
        self._authenticated = False

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def _get_session(self) -> aiohttp.ClientSession:
        """Return (or create) a shared aiohttp session with cookie jar."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                cookie_jar=aiohttp.CookieJar(),
            )
            self._authenticated = False
        return self._session

    async def async_close(self) -> None:
        """Close the underlying aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def _authenticate(self) -> None:
        """POST to Nutify login endpoint and store the session cookie."""
        if not self._username:
            # Auth is disabled on this Nutify instance — nothing to do.
            self._authenticated = True
            return

        session = self._get_session()
        url = f"{self._base_url}{API_LOGIN}"
        try:
            async with session.post(
                url,
                json={"username": self._username, "password": self._password},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    body = await resp.json()
                    if body.get("success"):
                        self._authenticated = True
                        _LOGGER.debug("Authenticated with Nutify at %s", self._base_url)
                        return
                    raise ConfigEntryAuthFailed(
                        f"Nutify login failed: {body.get('message', 'unknown error')}"
                    )
                if resp.status in (401, 403):
                    raise ConfigEntryAuthFailed(
                        "Invalid Nutify credentials (HTTP %d)", resp.status
                    )
                raise UpdateFailed(
                    f"Unexpected status {resp.status} from Nutify login endpoint"
                )
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Cannot connect to Nutify: {err}") from err

    # ------------------------------------------------------------------
    # Data fetching helpers
    # ------------------------------------------------------------------

    async def _fetch_json(
        self, path: str, *, retry_auth: bool = True
    ) -> dict[str, Any]:
        """Fetch a JSON endpoint, re-authenticating once on 401/403."""
        session = self._get_session()
        url = f"{self._base_url}{path}"
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status in (401, 403):
                    if retry_auth:
                        _LOGGER.debug(
                            "Session expired (HTTP %d), re-authenticating…",
                            resp.status,
                        )
                        self._authenticated = False
                        await self._authenticate()
                        return await self._fetch_json(path, retry_auth=False)
                    raise ConfigEntryAuthFailed(
                        "Nutify re-authentication failed (HTTP %d)" % resp.status
                    )
                if resp.status != 200:
                    raise UpdateFailed(
                        f"Nutify returned HTTP {resp.status} for {path}"
                    )
                return await resp.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Cannot connect to Nutify: {err}") from err

    # ------------------------------------------------------------------
    # Coordinator update
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from all relevant Nutify endpoints and merge results."""
        if not self._authenticated:
            await self._authenticate()

        merged: dict[str, Any] = {}

        # 1. Primary data: all NUT variables
        try:
            primary = await self._fetch_json(API_DATA_ALL)
            if primary.get("success") and isinstance(primary.get("data"), dict):
                merged.update(primary["data"])
        except UpdateFailed:
            raise  # Re-raise — primary endpoint is required

        # 2. Battery metrics (optional; log warning on failure)
        try:
            batt = await self._fetch_json(API_BATTERY_METRICS)
            if batt.get("success") and isinstance(batt.get("data"), dict):
                # Prefix to avoid collisions with primary data keys
                for k, v in batt["data"].items():
                    merged.setdefault(f"_battery.{k}", v)
        except (UpdateFailed, ConfigEntryAuthFailed) as err:
            _LOGGER.warning("Could not fetch battery metrics: %s", err)

        # 3. Power metrics (optional)
        try:
            power = await self._fetch_json(API_POWER_METRICS)
            if power.get("success") and isinstance(power.get("data"), dict):
                for k, v in power["data"].items():
                    merged.setdefault(f"_power.{k}", v)
        except (UpdateFailed, ConfigEntryAuthFailed) as err:
            _LOGGER.warning("Could not fetch power metrics: %s", err)

        # 4. Voltage metrics (optional)
        try:
            volt = await self._fetch_json(API_VOLTAGE_METRICS)
            if volt.get("success") and isinstance(volt.get("data"), dict):
                for k, v in volt["data"].items():
                    merged.setdefault(f"_voltage.{k}", v)
        except (UpdateFailed, ConfigEntryAuthFailed) as err:
            _LOGGER.warning("Could not fetch voltage metrics: %s", err)

        return merged


async def validate_connection(
    host: str,
    port: int,
    use_ssl: bool,
    username: str,
    password: str,
) -> None:
    """Attempt a login to validate that Nutify is reachable and credentials work.

    Raises:
        UpdateFailed: If the server cannot be reached.
        ConfigEntryAuthFailed: If the credentials are rejected.
    """
    base_url = f"{'https' if use_ssl else 'http'}://{host}:{port}"
    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
        if not username:
            # Auth disabled — just check reachability via the login endpoint
            url = f"{base_url}{API_LOGIN}"
            try:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    # Any HTTP response means the server is reachable
                    if resp.status >= 500:
                        raise UpdateFailed(
                            f"Nutify server error: HTTP {resp.status}"
                        )
            except aiohttp.ClientError as err:
                raise UpdateFailed(f"Cannot connect to Nutify: {err}") from err
            return

        url = f"{base_url}{API_LOGIN}"
        try:
            async with session.post(
                url,
                json={"username": username, "password": password},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status in (401, 403):
                    raise ConfigEntryAuthFailed("Invalid credentials")
                if resp.status != 200:
                    raise UpdateFailed(f"Nutify returned HTTP {resp.status}")
                body = await resp.json()
                if not body.get("success"):
                    raise ConfigEntryAuthFailed(
                        body.get("message", "Login failed")
                    )
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Cannot connect to Nutify: {err}") from err
