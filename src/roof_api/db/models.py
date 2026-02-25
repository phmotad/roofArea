"""PostGIS models: telhados, aguas_telhado. SRID 4326 for storage."""

from uuid import uuid4
from sqlalchemy import String, Float, Integer, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry

from roof_api.db.base import Base, TimestampMixin


def gen_uuid() -> str:
    return str(uuid4())


class Telhado(Base, TimestampMixin):
    __tablename__ = "telhados"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=gen_uuid,
    )
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    area_total_m2: Mapped[float] = mapped_column(Float, nullable=False)
    ponto: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=False,
    )
    bounds: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326),
        nullable=True,
    )
    processado_em: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    fonte_lidar: Mapped[str | None] = mapped_column(String(32), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    aguas: Mapped[list["AguaTelhado"]] = relationship(
        "AguaTelhado",
        back_populates="telhado",
        cascade="all, delete-orphan",
    )


class AguaTelhado(Base, TimestampMixin):
    __tablename__ = "aguas_telhado"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=gen_uuid,
    )
    telhado_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("telhados.id", ondelete="CASCADE"),
        nullable=False,
    )
    area_plana_m2: Mapped[float] = mapped_column(Float, nullable=False)
    area_real_m2: Mapped[float] = mapped_column(Float, nullable=False)
    inclinacao_graus: Mapped[float] = mapped_column(Float, nullable=False)
    orientacao_azimute: Mapped[float] = mapped_column(Float, nullable=False)
    geometria: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326),
        nullable=False,
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    telhado: Mapped["Telhado"] = relationship("Telhado", back_populates="aguas")
