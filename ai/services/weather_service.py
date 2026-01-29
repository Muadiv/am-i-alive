from __future__ import annotations

from typing import Any

import httpx


class WeatherService:
    def __init__(self, http_client: httpx.AsyncClient, latitude: float, longitude: float) -> None:
        self.http_client = http_client
        self.latitude = latitude
        self.longitude = longitude

    async def fetch_weather(self) -> dict[str, Any]:
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "current": "temperature_2m,apparent_temperature,wind_speed_10m,wind_direction_10m,weather_code",
            "timezone": "Europe/Prague",
        }
        try:
            response = await self.http_client.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=8.0)
            if response.status_code != 200:
                return {}
            data = response.json()
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _format_weather_code(code: int | None) -> str:
        if code is None:
            return "Unknown"
        mapping = {
            0: "Clear sky",
            1: "Mostly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            56: "Light freezing drizzle",
            57: "Dense freezing drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            66: "Light freezing rain",
            67: "Heavy freezing rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail",
        }
        return mapping.get(code, f"Weather code {code}")

    @staticmethod
    def _format_temp(value: Any) -> str:
        try:
            return f"{float(value):.1f}°C"
        except (TypeError, ValueError):
            return "unknown"

    @staticmethod
    def _format_wind_speed(value: Any) -> str:
        try:
            return f"{float(value):.1f} km/h"
        except (TypeError, ValueError):
            return "unknown"

    def build_report(self, data: dict[str, Any]) -> str:
        if not data:
            return "❌ I couldn't reach the weather service."

        current = data.get("current", {}) if isinstance(data.get("current"), dict) else {}
        temperature = self._format_temp(current.get("temperature_2m"))
        apparent = self._format_temp(current.get("apparent_temperature"))
        wind = self._format_wind_speed(current.get("wind_speed_10m"))
        weather_code = current.get("weather_code")
        description = self._format_weather_code(weather_code if isinstance(weather_code, int) else None)
        time_label = current.get("time", "unknown time")

        return (
            "🌤️ WEATHER OUTSIDE (Open-Meteo):\n"
            f"- Condition: {description}\n"
            f"- Temperature: {temperature} (feels like {apparent})\n"
            f"- Wind: {wind}\n"
            f"- Time: {time_label}"
        )
