"""Initial PostGIS schema: telhados, aguas_telhado.

Revision ID: 001
Revises:
Create Date: 2025-02-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "telhados",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("area_total_m2", sa.Float(), nullable=False),
        sa.Column("ponto", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("bounds", Geometry("POLYGON", srid=4326), nullable=True),
        sa.Column("processado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("fonte_lidar", sa.String(32), nullable=True),
        sa.Column("metadata_json", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_telhados_lat_lon", "telhados", ["lat", "lon"], unique=False)

    op.create_table(
        "aguas_telhado",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("telhado_id", sa.UUID(), nullable=False),
        sa.Column("area_plana_m2", sa.Float(), nullable=False),
        sa.Column("area_real_m2", sa.Float(), nullable=False),
        sa.Column("inclinacao_graus", sa.Float(), nullable=False),
        sa.Column("orientacao_azimute", sa.Float(), nullable=False),
        sa.Column("geometria", Geometry("POLYGON", srid=4326), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["telhado_id"], ["telhados.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_aguas_telhado_telhado_id", "aguas_telhado", ["telhado_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_aguas_telhado_telhado_id", table_name="aguas_telhado")
    op.drop_table("aguas_telhado")
    op.drop_index("ix_telhados_lat_lon", table_name="telhados")
    op.drop_table("telhados")
