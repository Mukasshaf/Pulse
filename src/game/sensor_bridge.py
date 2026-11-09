"""Live and replayed sensor bridges for the Pulse engine (ESP32 serial stream or recorded CSV).

Stream contract (firmware/firmware.ino, 115200 baud, 66.67 Hz):
    sample_idx,timestamp_ms,pulse_raw,gsr_raw,acc_x,acc_y,acc_z

A serial port can be opened by one process only. Two topologies are therefore supported:

* Decoupled (primary data path): ``src/hardware/serial_reader.py`` owns the port and records the
  session. The engine runs ``ReplayBridge(follow=True)`` on the CSV that serial_reader is writing.
* Integrated: the engine owns the port through ``SerialBridge`` and writes the same CSV schema
  serial_reader produces, so the recording is never lost.
"""
from __future__ import annotations

import contextlib
import csv
import importlib
import threading
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import IO, Protocol

from src.game.bridge_interface import BridgeInterface, StubBridge
from src.game.constants import (
    BRIDGE_BAUD_CANDIDATES,
    BRIDGE_PROBE_TIMEOUT_S,
    BRIDGE_PROBE_VALID_ROWS,
    BridgeUnavailableError,
)
from src.game.sensor_replay import (
    ReplayBridge,
    load_recorded_rows,
    resolve_replay_source,
)
from src.game.sensor_stream import (
    POLL_IDLE_S,
    RECORD_FIELDNAMES,
    SensorRow,
    StreamBridge,
    parse_sensor_line,
    wall_ms,
)

# The stream and replay halves live in sensor_stream.py and sensor_replay.py; their public names stay importable here
__all__ = [
    "KNOWN_USB_SERIAL_VIDS",
    "RECORD_FIELDNAMES",
    "BridgeSetup",
    "PortInfo",
    "PortOpener",
    "ReplayBridge",
    "SensorRow",
    "SerialBridge",
    "SerialPortLike",
    "StreamBridge",
    "create_bridge",
    "list_candidate_ports",
    "load_recorded_rows",
    "open_serial_port",
    "parse_sensor_line",
    "probe_port",
    "pyserial_available",
    "resolve_replay_source",
]

# USB vendor IDs of the serial bridges found on ESP32 boards: CP210x, CH340/CH9102, FTDI, Espressif native USB
KNOWN_USB_SERIAL_VIDS: frozenset[int] = frozenset({0x10C4, 0x1A86, 0x0403, 0x303A})


class SerialPortLike(Protocol):
    """The slice of a pyserial port the bridge needs; tests supply a fake."""

    def readline(self) -> bytes:
        """Return one line, or empty bytes on timeout."""
        ...

    def close(self) -> None:
        """Release the port."""
        ...


class _RowWriter(Protocol):
    """Structural type of a csv.writer object."""

    def writerow(self, row: Iterable[object]) -> object:
        """Write one row."""
        ...


PortOpener = Callable[[str, int], SerialPortLike]


class SerialBridge(StreamBridge):
    """Owns an ESP32 serial port, parses its stream on a background thread, and records every valid row."""

    def __init__(
        self,
        port: SerialPortLike,
        device: str = "",
        baud: int = 0,
        record_path: Path | None = None,
        clock_ms: Callable[[], int] | None = None,
    ) -> None:
        """Wrap an already-open port. record_path enables the serial_reader-compatible CSV recording."""
        super().__init__(clock_ms)
        self.device: str = device
        self.baud: int = baud
        self.record_path: Path | None = record_path
        self.error: str | None = None
        self._port: SerialPortLike = port
        self._stop: threading.Event = threading.Event()
        self._thread: threading.Thread | None = None
        self._closed: bool = False
        self._record_file: IO[str] | None = None
        self._record_writer: _RowWriter | None = None
        self._record_stack: contextlib.ExitStack[bool | None] = contextlib.ExitStack()
        if record_path is not None:
            record_path.parent.mkdir(parents=True, exist_ok=True)
            with contextlib.ExitStack() as stack:
                handle = stack.enter_context(open(record_path, mode="w", newline="", encoding="utf-8"))
                writer = csv.writer(handle, lineterminator="\n")
                writer.writerow(RECORD_FIELDNAMES)
                handle.flush()
                self._record_file = handle
                self._record_writer = writer
                # Header is on disk: keep the handle open for the session; close() releases it
                self._record_stack = stack.pop_all()

    def _record(self, row: SensorRow) -> None:
        """Append one row to the recording. A write failure stops recording but not telemetry."""
        if self._record_writer is None or self._record_file is None:
            return
        try:
            self._record_writer.writerow([
                row.sample_idx, row.timestamp_ms, row.unix_ts_ms,
                row.pulse_raw, row.gsr_raw, row.acc_x, row.acc_y, row.acc_z,
            ])
            self._record_file.flush()
        except OSError as exc:
            self.error = f"recording stopped: {exc}"
            self._record_writer = None

    def read_once(self) -> bool:
        """Read and process one line from the port. Return False when the port yielded nothing."""
        try:
            raw = self._port.readline()
        except (OSError, ValueError) as exc:
            self.error = str(exc)
            self._stop.set()
            return False
        if not raw:
            return False
        arrival_ms = self._clock_ms()
        row = parse_sensor_line(raw.decode("utf-8", errors="replace"), arrival_ms)
        if row is None:
            self.rows_rejected += 1
            return True
        self._ingest(row, arrival_ms)
        self._record(row)
        return True

    def _run(self) -> None:
        """Background loop: read until stopped or the port fails."""
        while not self._stop.is_set():
            if not self.read_once():
                self._stop.wait(POLL_IDLE_S)

    def start(self) -> None:
        """Start the background reader thread. Idempotent."""
        if self._thread is None and not self._closed:
            self._thread = threading.Thread(target=self._run, name="pulse-serial-bridge", daemon=True)
            self._thread.start()

    def close(self) -> None:
        """Stop the reader, then release the port and the recording. Idempotent."""
        if self._closed:
            return
        self._closed = True
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        with contextlib.suppress(OSError):
            self._port.close()
        self._record_stack.close()


@dataclass(frozen=True)
class PortInfo:
    """A serial port that looks like an ESP32 USB bridge."""

    device: str
    description: str
    vid: int


def _load_module(name: str) -> ModuleType | None:
    """Import an optional module, returning None when it is not installed."""
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


def pyserial_available() -> bool:
    """Return True when pyserial can be imported."""
    return _load_module("serial") is not None


def list_candidate_ports(comports: Callable[[], Iterable[object]] | None = None) -> list[PortInfo]:
    """Scan serial ports and keep those whose USB vendor ID belongs to a known ESP32 serial bridge.

    Other ports (Bluetooth COM ports, unrelated instruments) are never opened by auto-detection.
    """
    if comports is None:
        list_ports = _load_module("serial.tools.list_ports")
        if list_ports is None:
            return []
        entries: Iterable[object] = list_ports.comports()
    else:
        entries = comports()
    found: list[PortInfo] = []
    for entry in entries:
        vid = getattr(entry, "vid", None)
        device = getattr(entry, "device", None)
        if isinstance(vid, int) and isinstance(device, str) and device and vid in KNOWN_USB_SERIAL_VIDS:
            found.append(PortInfo(device=device, description=str(getattr(entry, "description", "")), vid=vid))
    return found


def open_serial_port(device: str, baud: int) -> SerialPortLike:
    """Open a port the same way serial_reader.py does. Raises OSError if it is busy or missing."""
    serial_module = _load_module("serial")
    if serial_module is None:
        raise BridgeUnavailableError("pyserial is not installed (uv add pyserial)")
    port: SerialPortLike = serial_module.Serial(device, baud, timeout=0.25)
    return port


def probe_port(
    device: str,
    opener: PortOpener,
    bauds: Sequence[int] = BRIDGE_BAUD_CANDIDATES,
    timeout_s: float = BRIDGE_PROBE_TIMEOUT_S,
    min_valid_rows: int = BRIDGE_PROBE_VALID_ROWS,
    monotonic: Callable[[], float] = time.monotonic,
) -> tuple[SerialPortLike, int] | None:
    """Negotiate a baud rate: return (open port, baud) for the first rate that yields valid rows.

    The port is handed back open so the bridge can keep reading without a second open (and a
    second board reset). Returns None when the port is busy or never produces the Pulse stream.
    """
    for baud in bauds:
        try:
            port = opener(device, baud)
        except OSError:
            continue  # busy (for example serial_reader.py already owns it) or unplugged
        valid = 0
        deadline = monotonic() + timeout_s
        try:
            while monotonic() < deadline:
                raw = port.readline()
                if raw and parse_sensor_line(raw.decode("utf-8", errors="replace"), wall_ms()) is not None:
                    valid += 1
                    if valid >= min_valid_rows:
                        return (port, baud)
        except (OSError, ValueError):
            valid = 0
        with contextlib.suppress(OSError):
            port.close()
    return None


@dataclass(frozen=True)
class BridgeSetup:
    """The bridge chosen for a session plus a one-line status for the operator."""

    bridge: BridgeInterface
    mode: str
    detail: str


def _serial_bridge_setup(
    required: bool,
    port: str | None,
    record_path: Path | None,
    opener: PortOpener | None,
    comports: Callable[[], Iterable[object]] | None,
) -> BridgeSetup:
    """Find and open the ESP32 stream. Fall back to StubBridge unless the bridge is required."""
    reason = "no ESP32-like serial port found"
    if opener is None and not pyserial_available():
        reason = "pyserial is not installed (uv add pyserial)"
        devices: list[str] = []
    else:
        devices = [port] if port else [info.device for info in list_candidate_ports(comports)]
    for device in devices:
        probed = probe_port(device, opener if opener is not None else open_serial_port)
        if probed is None:
            reason = (
                f"no valid sensor stream on {device} (port busy or not the Pulse firmware). "
                "If serial_reader.py owns the port, use --bridge replay --bridge-follow --bridge-source <its CSV>"
            )
            continue
        opened, baud = probed
        bridge = SerialBridge(opened, device=device, baud=baud, record_path=record_path)
        bridge.start()
        recording = f", recording to {record_path}" if record_path is not None else ""
        return BridgeSetup(bridge, "serial", f"live stream on {device} at {baud} baud{recording}")
    if required:
        raise BridgeUnavailableError(reason)
    return BridgeSetup(StubBridge(), "stub", reason)


def create_bridge(
    mode: str,
    port: str | None = None,
    source: Path | None = None,
    follow: bool = False,
    record_path: Path | None = None,
    opener: PortOpener | None = None,
    comports: Callable[[], Iterable[object]] | None = None,
) -> BridgeSetup:
    """Build the session bridge for a --bridge mode: auto, serial, replay, or stub.

    auto   -- use the ESP32 if one answers, otherwise fall back to StubBridge (composure on STANDBY).
    serial -- require the ESP32; raise BridgeUnavailableError if it cannot be opened.
    replay -- feed from a recorded CSV, or follow a CSV that serial_reader.py is writing.
    stub   -- no telemetry.
    """
    if mode == "stub":
        return BridgeSetup(StubBridge(), "stub", "no sensor bridge requested")
    if mode == "replay":
        if source is None:
            raise BridgeUnavailableError("--bridge replay needs --bridge-source <csv or directory>")
        path = resolve_replay_source(source)
        replay = ReplayBridge(path, follow=follow)
        replay.start()
        return BridgeSetup(replay, "replay", f"{'following' if follow else 'replaying'} {path}")
    if mode in ("auto", "serial"):
        return _serial_bridge_setup(mode == "serial", port, record_path, opener, comports)
    raise BridgeUnavailableError(f"unknown bridge mode: {mode}")
