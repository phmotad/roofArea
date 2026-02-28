"""Application configuration from environment. No secrets in code."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file_path() -> str:
    """Prefer .env in project root (parent of src/roof_api) so API loads it from any cwd."""
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        return str(cwd_env)
    try:
        project_root = Path(__file__).resolve().parent.parent.parent
        if (project_root / ".env").exists():
            return str(project_root / ".env")
    except Exception:
        pass
    return ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file_path(),
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
    segmentation_model_path: str = "./models/deeplabv3_roof_multiclass.pt"
    segmentation_num_classes: int = 5
    segmentation_deeplab_backbone: Literal["resnet50", "resnet101", "mobilenet_v3_large"] = "resnet50"
    segmentation_prob_threshold: float = 0.6
    segmentation_lines_model_path: str = ""
    output_image_base64: bool = False
    cache_ttl_seconds: int = 86400
    min_roof_area_m2: float = 10.0
    max_roof_distance_from_point_m: float = 0.0
    render_only_waters: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
