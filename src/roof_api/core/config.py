"""Application configuration from environment. No secrets in code."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://localhost/roof_db"
    database_sync_url: str = "postgresql://localhost/roof_db"
    geo_buffer_meters: float = 35.0
    ortho_tile_url: str = ""
    mapbox_access_token: str = ""
    lidar_dgt_path: str = ""
    lidar_pnoa_path: str = ""
    segmentation_model_path: str = "./models/unet_roof.pt"
    segmentation_num_classes: int = 1
    segmentation_prob_threshold: float = 0.6
    output_image_base64: bool = False
    cache_ttl_seconds: int = 86400
    min_roof_area_m2: float = 10.0
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
