"""Unit tests for sensor bridge interfaces and stub implementations."""
from __future__ import annotations

from src.game.bridge_interface import BridgeInterface, SensorSample, StubBridge


def test_stub_bridge_protocol_compliance() -> None:
    """Verify StubBridge conforms to BridgeInterface protocol."""
    stub = StubBridge()
    assert isinstance(stub, BridgeInterface)
    assert stub.get_latest_sample() is None
    assert stub.get_mpu_variance() is None


def test_sensor_sample_fields() -> None:
    """Verify SensorSample field types and construction."""
    sample = SensorSample(
        unix_ts_ms=1724688000000,
        bvp=512.4,
        gsr=2048,
        acc_x=0.01,
        acc_y=-0.02,
        acc_z=0.98,
    )
    assert isinstance(sample.unix_ts_ms, int)
    assert isinstance(sample.bvp, float)
    assert isinstance(sample.gsr, int)
    assert isinstance(sample.acc_x, float)
    assert isinstance(sample.acc_y, float)
    assert isinstance(sample.acc_z, float)
