"""Weather lookup service used by agent tools."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from src.config import settings


WEATHER_CODE_TEXT = {
    0: "晴",
    1: "大部晴朗",
    2: "局部多云",
    3: "阴",
    45: "雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "中等毛毛雨",
    55: "大毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    80: "小阵雨",
    81: "中等阵雨",
    82: "强阵雨",
    95: "雷暴",
    96: "雷暴伴小冰雹",
    99: "雷暴伴大冰雹",
}


@dataclass(frozen=True, slots=True)
class WeatherResult:
    city: str
    country: str
    date: str
    summary: str
    temperature_min: float | None = None
    temperature_max: float | None = None
    precipitation_probability: int | None = None
    wind_speed_max: float | None = None

    def to_text(self) -> str:
        parts = [
            f"城市：{self.city}{f'，{self.country}' if self.country else ''}",
            f"日期：{self.date}",
            f"天气：{self.summary}",
        ]
        if self.temperature_min is not None and self.temperature_max is not None:
            parts.append(f"气温：{self.temperature_min:g}°C - {self.temperature_max:g}°C")
        if self.precipitation_probability is not None:
            parts.append(f"最大降水概率：{self.precipitation_probability}%")
        if self.wind_speed_max is not None:
            parts.append(f"最大风速：{self.wind_speed_max:g} km/h")
        return "\n".join(parts)


class WeatherService:
    """Query weather through Open-Meteo's public APIs."""

    def __init__(
        self,
        *,
        geocoding_url: str = settings.weather.geocoding_url,
        forecast_url: str = settings.weather.forecast_url,
        timeout_seconds: float = settings.weather.timeout_seconds,
    ) -> None:
        self.geocoding_url = geocoding_url
        self.forecast_url = forecast_url
        self.timeout_seconds = timeout_seconds

    def get_weather(self, *, city: str, target_date: str) -> WeatherResult:
        normalized_city = city.strip()
        if not normalized_city:
            raise ValueError("city 不能为空")
        normalized_date = self._normalize_date(target_date)
        location = self._geocode(normalized_city)
        forecast = self._forecast(location["latitude"], location["longitude"], normalized_date)
        daily = forecast.get("daily") if isinstance(forecast, dict) else None
        if not isinstance(daily, dict) or not daily.get("time"):
            raise RuntimeError("天气服务未返回可用的日天气数据")

        weather_code = self._first(daily.get("weather_code"))
        return WeatherResult(
            city=str(location.get("name") or normalized_city),
            country=str(location.get("country") or ""),
            date=normalized_date,
            summary=WEATHER_CODE_TEXT.get(int(weather_code), f"天气代码 {weather_code}") if weather_code is not None else "未知",
            temperature_min=self._first(daily.get("temperature_2m_min")),
            temperature_max=self._first(daily.get("temperature_2m_max")),
            precipitation_probability=self._first(daily.get("precipitation_probability_max")),
            wind_speed_max=self._first(daily.get("wind_speed_10m_max")),
        )

    def _geocode(self, city: str) -> dict[str, Any]:
        payload = self._get_json(
            self.geocoding_url,
            {
                "name": city,
                "count": 1,
                "language": "zh",
                "format": "json",
            },
        )
        results = payload.get("results") if isinstance(payload, dict) else None
        if not results:
            raise RuntimeError(f"未找到城市 {city} 的位置信息")
        return dict(results[0])

    def _forecast(self, latitude: float, longitude: float, target_date: str) -> dict[str, Any]:
        return self._get_json(
            self.forecast_url,
            {
                "latitude": latitude,
                "longitude": longitude,
                "daily": ",".join(
                    [
                        "weather_code",
                        "temperature_2m_max",
                        "temperature_2m_min",
                        "precipitation_probability_max",
                        "wind_speed_10m_max",
                    ]
                ),
                "timezone": "auto",
                "start_date": target_date,
                "end_date": target_date,
            },
        )

    def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        request_url = f"{url}?{urlencode(params)}"
        with urlopen(request_url, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _normalize_date(value: str) -> str:
        try:
            return date.fromisoformat(value.strip()).isoformat()
        except ValueError as exc:
            raise ValueError("date 必须是 YYYY-MM-DD 格式；相对日期请先调用 get_current_date 后换算") from exc

    @staticmethod
    def _first(value: Any) -> Any:
        if isinstance(value, list):
            return value[0] if value else None
        return value
