"""Alter aguas_telhado.geometria to MULTIPOLYGON.

Revision ID: 002
Revises: 001
Create Date: 2025-02-09

"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE aguas_telhado "
        "ALTER COLUMN geometria TYPE geometry(MultiPolygon, 4326) USING ST_Multi(geometria)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE aguas_telhado "
        "ALTER COLUMN geometria TYPE geometry(Polygon, 4326) USING ST_GeometryN(geometria, 1)"
    )
