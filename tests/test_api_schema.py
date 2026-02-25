"""Basic schema and validation tests."""

import pytest
from pydantic import ValidationError

from roof_api.api.schemas import AnalisarTelhadoRequest, AguaOut
from uuid import uuid4


def test_analisar_request_valid():
    r = AnalisarTelhadoRequest(lat=38.72, lon=-9.14)
    assert r.lat == 38.72 and r.lon == -9.14


def test_analisar_request_invalid_lat():
    with pytest.raises(ValidationError):
        AnalisarTelhadoRequest(lat=100, lon=0)


def test_analisar_request_invalid_lon():
    with pytest.raises(ValidationError):
        AnalisarTelhadoRequest(lat=0, lon=200)


def test_agua_out():
    a = AguaOut(
        id=uuid4(),
        area_real_m2=50.0,
        inclinacao_graus=25.0,
        orientacao_azimute=180.0,
        geometria_wkt="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
    )
    assert a.area_real_m2 == 50.0
