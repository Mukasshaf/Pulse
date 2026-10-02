"""Unit tests for sensor bridge interfaces, the serial/replay bridges, and port detection."""
from __future__ import annotations

import csv
import math
import time
from collections.abc import Iterable
from pathlib import Path

import pytest

from src.game.bridge_interface import BridgeInterface, SensorSample, StubBridge
from src.game.constants import (
    BRIDGE_MIN_WINDOW_SAMPLES,
    BRIDGE_STALE_AFTER_MS,
    BridgeUnavailableError,
)
from src.game.sensor_bridge import (
    RECORD_FIELDNAMES,
    ReplayBridge,
    SerialBridge,
    SerialPortLike,
    create_bridge,
    list_candidate_ports,
    parse_sensor_line,
    probe_port,
    resolve_replay_source,
)


class _FakePort:
    """Serial port double that serves prepared lines, then times out (empty reads)."""

    def __init__(self, lines: Iterable[bytes]) -> None:
        self.lines: list[bytes] = list(lines)
        self.closed: bool = False

    def readline(self) -> bytes:
        return self.lines.pop(0) if self.lines else b""

    def close(self) -> None:
        self.closed = True


class _FakeClock:
    """Manually advanced millisecond clock."""

    def __init__(self, start_ms: int = 1_700_000_000_000) -> None:
        self.now_ms: int = start_ms

    def __call__(self) -> int:
        return self.now_ms


class _FakeComport:
    """Stand-in for a pyserial ListPortInfo entry."""

    def __init__(self, device: str, vid: int | None, description: str = "") -> None:
        self.device: str = device
        self.vid: int | None = vid
        self.description: str = description


def _firmware_line(idx: int, acc: tuple[int, int, int] = (100, -200, 16000)) -> bytes:
    return f"{idx},{idx * 15},2010,1500,{acc[0]},{acc[1]},{acc[2]}\n".encode()


def test_stub_bridge_protocol_compliance() -> None:
    """Verify StubBridge conforms to BridgeInterface protocol."""
    stub = StubBridge()
    assert isinstance(stub, BridgeInterface)
    assert stub.get_latest_sample() is None
    assert stub.get_mpu_variance() is None
    stub.close()


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


def test_parse_firmware_recorded_and_json_rows() -> None:
    """Verify the three accepted stream formats map onto the same row."""
    firmware = parse_sensor_line("12,180,2010,1500,100,-200,16000\r\n", arrival_unix_ms=5000)
    assert firmware is not None
    assert (firmware.sample_idx, firmware.timestamp_ms, firmware.unix_ts_ms) == (12, 180, 5000)
    assert (firmware.pulse_raw, firmware.gsr_raw) == (2010, 1500)
    sample = firmware.to_sample()
    assert isinstance(sample.bvp, float) and sample.bvp == 2010.0
    assert isinstance(sample.gsr, int) and sample.gsr == 1500
    assert (sample.acc_x, sample.acc_y, sample.acc_z) == (100.0, -200.0, 16000.0)

    # serial_reader.py output carries its own host timestamp, which wins over the arrival time
    recorded = parse_sensor_line("12,180,1724688000123,2010,1500,100,-200,16000", arrival_unix_ms=5000)
    assert recorded is not None
    assert recorded.unix_ts_ms == 1724688000123

    # JSON with short aliases; an extra firmware-side heart-rate key is ignored
    as_json = parse_sensor_line('{"n": 12, "t": 180, "ppg": 2010, "gsr": 1500, "ax": 100, "ay": -200, "az": 16000, "hr": 72}', 5000)
    assert as_json is not None
    assert as_json == firmware


def test_parse_rejects_malformed_rows() -> None:
    """Verify headers, comments, short rows, text and non-finite values are all rejected."""
    rejected = [
        "",
        "# firmware booting",
        "sample_idx,timestamp_ms,pulse_raw,gsr_raw,acc_x,acc_y,acc_z",
        "1,2,3,4,5,6",
        "1,2,3,4,5,6,7,8,9",
        "1,2,three,4,5,6,7",
        "ets Jun  8 2016 00:22:57",
        '{"ppg": 2010, "gsr": 1500, "ax": 1, "ay": 2}',
        '{"ppg": NaN, "gsr": 1500, "ax": 1, "ay": 2, "az": 3}',
        '{"ppg": true, "gsr": 1500, "ax": 1, "ay": 2, "az": 3}',
        "[1, 2, 3]",
        "{not json",
    ]
    for line in rejected:
        assert parse_sensor_line(line, 5000) is None, line


def test_serial_bridge_reports_latest_sample_and_variance() -> None:
    """Verify the rolling variance equals the population variance of acceleration magnitude."""
    clock = _FakeClock()
    accs = [(100 + 7 * i, -200 + 3 * i, 16000 - 11 * i) for i in range(40)]
    port = _FakePort([b"ets boot garbage\n"] + [_firmware_line(i, acc) for i, acc in enumerate(accs)])
    bridge = SerialBridge(port, device="COM9", baud=115200, clock_ms=clock)
    assert isinstance(bridge, BridgeInterface)
    assert bridge.get_latest_sample() is None
    assert bridge.get_mpu_variance() is None

    for index in range(41):
        assert bridge.read_once() is True
        clock.now_ms += 15
        if index == BRIDGE_MIN_WINDOW_SAMPLES - 5:
            assert bridge.get_mpu_variance() is None  # too few samples for a stable variance
    assert bridge.read_once() is False  # port idle
    assert bridge.rows_rejected == 1
    assert bridge.rows_ingested == 40
    assert bridge.gap_events == 0

    magnitudes = [math.sqrt(x * x + y * y + z * z) for x, y, z in accs]
    mean = sum(magnitudes) / len(magnitudes)
    expected = sum((m - mean) ** 2 for m in magnitudes) / len(magnitudes)
    variance = bridge.get_mpu_variance()
    assert variance is not None
    assert math.isclose(variance, expected, rel_tol=1e-9)

    latest = bridge.get_latest_sample()
    assert latest is not None
    assert latest.acc_x == float(accs[-1][0])
    assert bridge.get_latest_sample() is None  # already consumed

    # Telemetry that stops arriving is reported as absent, not frozen at its last value
    clock.now_ms += BRIDGE_STALE_AFTER_MS + 1
    assert bridge.get_mpu_variance() is None
    bridge.close()
    assert port.closed is True
    bridge.close()  # idempotent


def test_serial_bridge_counts_gaps_and_records_serial_reader_schema(tmp_path: Path) -> None:
    """Verify a dropped sample is counted and the recording matches serial_reader.py's CSV."""
    clock = _FakeClock()
    record_path = tmp_path / "S01_1" / "sensor_stream.csv"
    port = _FakePort([_firmware_line(0), _firmware_line(1), _firmware_line(5), b"bad,row\n"])
    bridge = SerialBridge(port, record_path=record_path, clock_ms=clock)
    while bridge.read_once():
        clock.now_ms += 15
    bridge.close()
    assert bridge.gap_events == 1

    with open(record_path, encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert tuple(rows[0]) == RECORD_FIELDNAMES
    assert rows[0] == ["sample_idx", "timestamp_ms", "unix_ts_ms", "pulse_raw", "gsr_raw", "acc_x", "acc_y", "acc_z"]
    assert len(rows) == 4
    assert rows[1] == ["0", "0", str(1_700_000_000_000), "2010", "1500", "100", "-200", "16000"]
    assert rows[3][0] == "5"


def test_serial_bridge_background_thread_and_port_failure() -> None:
    """Verify the reader thread ingests rows, and a failing port stops it without raising."""
    port = _FakePort([_firmware_line(i) for i in range(30)])
    bridge = SerialBridge(port)
    bridge.start()
    deadline = time.monotonic() + 3.0
    while bridge.rows_ingested < 30 and time.monotonic() < deadline:
        time.sleep(0.01)
    bridge.close()
    assert bridge.rows_ingested == 30
    assert port.closed is True

    class _BrokenPort(_FakePort):
        def readline(self) -> bytes:
            raise OSError("device disconnected")

    broken = SerialBridge(_BrokenPort([]))
    assert broken.read_once() is False
    assert broken.error == "device disconnected"
    assert broken.get_mpu_variance() is None
    broken.close()


def test_port_scan_keeps_only_known_usb_serial_bridges() -> None:
    """Verify auto-detection never selects Bluetooth or unknown-vendor ports."""
    ports = [
        _FakeComport("COM1", None, "Communications Port"),
        _FakeComport("COM5", 0x1234, "Unknown gadget"),
        _FakeComport("COM3", 0x10C4, "Silicon Labs CP210x USB to UART Bridge"),
        _FakeComport("COM7", 0x1A86, "USB-SERIAL CH340"),
    ]
    found = list_candidate_ports(lambda: ports)
    assert [info.device for info in found] == ["COM3", "COM7"]
    assert found[0].description.startswith("Silicon Labs")
    assert list_candidate_ports(list) == []


def test_probe_negotiates_baud_and_skips_busy_or_foreign_ports() -> None:
    """Verify probing accepts the first baud rate that yields valid rows and rejects everything else."""
    ticks = iter(range(10_000))

    def monotonic() -> float:
        return next(ticks) * 0.1

    opened: list[tuple[str, int]] = []

    def opener(device: str, baud: int) -> SerialPortLike:
        opened.append((device, baud))
        if device == "COM_BUSY":
            raise OSError("Access is denied")
        if device == "COM_OTHER" or baud != 115200:
            return _FakePort([b"\xff\xfe garbage\n"] * 5)
        return _FakePort([b"boot\n"] + [_firmware_line(i) for i in range(10)])

    assert probe_port("COM_BUSY", opener, bauds=(115200,), monotonic=monotonic) is None
    assert probe_port("COM_OTHER", opener, bauds=(115200,), timeout_s=1.0, monotonic=monotonic) is None

    opened.clear()
    result = probe_port("COM_ESP", opener, bauds=(57600, 115200), timeout_s=1.0, monotonic=monotonic)
    assert result is not None
    port, baud = result
    assert baud == 115200
    assert opened == [("COM_ESP", 57600), ("COM_ESP", 115200)]
    assert isinstance(port, _FakePort) and port.closed is False  # handed over open


def test_create_bridge_modes_and_fallback(tmp_path: Path) -> None:
    """Verify auto falls back to the stub, serial insists on hardware, and a found port goes live."""
    setup = create_bridge("stub")
    assert isinstance(setup.bridge, StubBridge) and setup.mode == "stub"

    def no_ports() -> list[_FakeComport]:
        return []

    def never_opened(device: str, baud: int) -> SerialPortLike:
        raise AssertionError("no port should be opened when none is listed")

    fallback = create_bridge("auto", opener=never_opened, comports=no_ports)
    assert isinstance(fallback.bridge, StubBridge)
    assert fallback.mode == "stub" and "no ESP32" in fallback.detail
    with pytest.raises(BridgeUnavailableError):
        create_bridge("serial", opener=never_opened, comports=no_ports)
    with pytest.raises(BridgeUnavailableError):
        create_bridge("replay")
    with pytest.raises(BridgeUnavailableError):
        create_bridge("telepathy")

    def busy(device: str, baud: int) -> SerialPortLike:
        raise OSError("Access is denied")

    held = create_bridge("auto", port="COM3", opener=busy)
    assert isinstance(held.bridge, StubBridge) and "serial_reader.py" in held.detail

    def esp32(device: str, baud: int) -> SerialPortLike:
        return _FakePort([_firmware_line(i) for i in range(50)])

    record_path = tmp_path / "sensor_stream.csv"
    live = create_bridge("auto", opener=esp32, comports=lambda: [_FakeComport("COM3", 0x10C4)], record_path=record_path)
    assert isinstance(live.bridge, SerialBridge)
    assert live.mode == "serial" and "COM3" in live.detail and "115200" in live.detail
    live.bridge.close()
    assert record_path.is_file()


def test_replay_bridge_paces_a_recording(tmp_path: Path) -> None:
    """Verify a recording is replayed on its own timeline rather than all at once."""
    source = tmp_path / "recorded_20261002_101500.csv"
    lines = [",".join(RECORD_FIELDNAMES)]
    lines += [f"{i},{i * 15},{1_724_688_000_000 + i * 15},2010,1500,{100 + i},-200,16000" for i in range(100)]
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")

    clock = _FakeClock()
    bridge = ReplayBridge(source, clock_ms=clock)
    assert isinstance(bridge, BridgeInterface)
    assert bridge.advance() == 1  # only the first row is due at t=0
    clock.now_ms += 150
    assert bridge.advance() == 10
    clock.now_ms += 10_000
    assert bridge.advance() == 89
    assert bridge.is_finished() is True
    assert bridge.rows_ingested == 100
    bridge.close()

    assert resolve_replay_source(tmp_path) == source
    with pytest.raises(BridgeUnavailableError):
        resolve_replay_source(tmp_path / "missing")


def test_replay_bridge_follows_a_file_being_written(tmp_path: Path) -> None:
    """Verify follow mode ignores history and ingests only complete rows appended afterwards."""
    source = tmp_path / "recorded_live.csv"
    source.write_text(",".join(RECORD_FIELDNAMES) + "\n0,0,1724688000000,2010,1500,1,2,3\n", encoding="utf-8")
    clock = _FakeClock()
    bridge = ReplayBridge(source, follow=True, clock_ms=clock)
    assert bridge.poll_follow() == 0  # rows written before the game started are not live

    with open(source, "a", encoding="utf-8") as writer:
        writer.write("1,15,1724688000015,2010,1500,100,-200,16000\n")
        writer.write("2,30,1724688000030,2010,1500,1")  # serial_reader is mid-row
        writer.flush()
        assert bridge.poll_follow() == 1
        writer.write("01,-200,16000\n")
        writer.flush()
        assert bridge.poll_follow() == 1
    latest = bridge.get_latest_sample()
    assert latest is not None and latest.acc_x == 101.0
    assert bridge.advance() == 0  # paced replay is inactive in follow mode
    bridge.close()
