"""
Weather tool.

Uses Open-Meteo (no API key required) for geocoding + current-conditions
forecast. This keeps the tool functional out of the box; if the deployer
sets WEATHER_API_KEY for a premium provider, later phases can branch on it.
"""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.agents.tools.registry import ToolSpec
from app.core.cache import cached
from app.core.exceptions import ExternalServiceError, NotFoundError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=6), reraise=True)
async def _get(client: httpx.AsyncClient, url: str, params: dict) -> dict:
    response = await client.get(url, params=params)
    response.raise_for_status()
    return response.json()


@cached(600, key_prefix="weather")
async def _get_weather(location: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            geo = await _get(client, GEOCODING_URL, {"name": location, "count": 1})
            if not geo.get("results"):
                raise NotFoundError(f"Location '{location}' not found.")

            place = geo["results"][0]
            forecast = await _get(
                client,
                FORECAST_URL,
                {
                    "latitude": place["latitude"],
                    "longitude": place["longitude"],
                    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                    "timezone": "auto",
                },
            )
    except NotFoundError:
        raise
    except httpx.HTTPError as exc:
        logger.error("Weather lookup failed for %s: %s", location, exc)
        raise ExternalServiceError(f"Weather lookup failed: {exc}", error_code="weather_error") from exc

    current = forecast.get("current", {})
    code = current.get("weather_code")
    return {
        "location": f"{place.get('name')}, {place.get('country', '')}".strip(", "),
        "temperature_c": current.get("temperature_2m"),
        "humidity_percent": current.get("relative_humidity_2m"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "condition": _WEATHER_CODES.get(code, "Unknown"),
    }


def build_weather_tool() -> ToolSpec:
    return ToolSpec(
        name="get_weather",
        description="Get the current weather conditions for a city or location name.",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name, optionally with country, e.g. 'Vadodara, India'.",
                }
            },
            "required": ["location"],
        },
        handler=_get_weather,
    )
