"""
电力市场数据源接口包
"""

from .weather_api import (
    fetch_weather_single,
    fetch_weather_multi,
    fetch_weather_guangdong_avg,
    fetch_current_observation,
    fetch_all_cities_current,
    GUANGDONG_CITIES,
)

from .fuel_api import (
    fetch_coal_price_cctd,
    fetch_lng_price_shpgx,
    build_fuel_display_data,
    get_fuel_latest_summary,
)

from .price_api import (
    fetch_guangdong_spot_from_bjx,
    fetch_guangdong_spot_from_gddl,
    fetch_electricity_data,
    fetch_price_news,
    generate_guangdong_price_template,
)

from .maintenance_api import (
    load_maintenance_from_excel,
    get_maintenance_template,
    save_maintenance_template,
    calculate_security_margin,
)

__all__ = [
    "fetch_weather_single", "fetch_weather_multi", "fetch_weather_guangdong_avg",
    "fetch_current_observation", "fetch_all_cities_current", "GUANGDONG_CITIES",
    "fetch_coal_price_cctd", "fetch_lng_price_shpgx", "build_fuel_display_data", "get_fuel_latest_summary",
    "fetch_guangdong_spot_from_bjx", "fetch_guangdong_spot_from_gddl", "fetch_electricity_data",
    "fetch_price_news", "generate_guangdong_price_template",
    "load_maintenance_from_excel", "get_maintenance_template", "save_maintenance_template",
    "calculate_security_margin",
]
