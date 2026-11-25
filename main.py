"""AirGesture CLI — unified entry point for gesture system.

Commands:
    send          Send a message or gesture
    test          Run pattern/distance tests
    decode        Decode a recording file
    ack           Start the ACK server
    gestures      Manage gestures (list/add/remove/export/import)
    serve         Serve a web page

Usage:
    python main.py --help
    python main.py send --message "hello" --bit-duration 1.0
    python main.py send --gesture "wave"
    python main.py test --pattern fixed
    python main.py test --distances
    python main.py decode --file data/recordings/recording.json
    python main.py ack --start-server --port 8888
    python main.py gestures --list
    python main.py gestures --add NAME --bits 1010 --aliases hello,hi
    python main.py gestures --remove NAME
    python main.py gestures --export-profile NAME
    python main.py gestures --import-profile PATH
    python main.py serve --page receiver/web/ --port 8080
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import List, Optional

# Local imports — prefer Agent 1 / Agent 2 implementations, fall back to stubs
try:
    from shared.protocol import Protocol  # Agent 1
    from shared.constants import BIT_DURATION_DEFAULT as _BIT_DURATION_DEFAULT
    from sender.transmitter import Transmitter  # Agent 1
    from sender.cpu_load import CPULoadController  # Agent 1
except ImportError:  # pragma: no cover - fallback when Agent 1/2 modules absent
    Protocol = None  # type: ignore
    _BIT_DURATION_DEFAULT = 1.0
    Transmitter = None  # type: ignore
    CPULoadController = None  # type: ignore

try:
    from receiver.analysis.receiver import Receiver, decode_file  # Agent 2
except ImportError:  # pragma: no cover - fallback when Agent 2 module absent
    Receiver = None  # type: ignore
    decode_file = None  # type: ignore

from gestures import GestureEngine, GestureNotFoundError  # noqa: E402

# Fallback stubs if Agent 1/2 not available
if Protocol is None:
    from protocol import Protocol as _StubProtocol  # noqa: E402
    Protocol = _StubProtocol  # type: ignore

if Transmitter is None or CPULoadController is None:
    from transmitter import Transmitter as _StubTransmitter, CPULoadController as _StubCPULoadController  # noqa: E402
    if Transmitter is None:
        Transmitter = _StubTransmitter  # type: ignore
    if CPULoadController is None:
        CPULoadController = _StubCPULoadController  # type: ignore

if Receiver is None or decode_file is None:
    from receiver.receiver_stub import Receiver as _StubReceiver, decode_file as _StubDecodeFile  # noqa: E402
    if Receiver is None:
        Receiver = _StubReceiver  # type: ignore
    if decode_file is None:
        decode_file = _StubDecodeFile  # type: ignore

from crc import compute_crc, verify_crc  # noqa: E402
from sync_detector import detect_sync  # noqa: E402

logger = logging.getLogger("airgesture.cli")

DEFAULT_CONFIG = "gestures/gestures.json"


def _build_engine(config_path: str = DEFAULT_CONFIG) -> GestureEngine:
    return GestureEngine(config_path=config_path)


# ------------------------------------------------------------------ #
# Command: send
# ------------------------------------------------------------------ #
def cmd_send(args: argparse.Namespace) -> int:
    engine = _build_engine(args.config)
    protocol = Protocol()
    cpu_controller = CPULoadController()
    bit_duration = float(getattr(args, "bit_duration", None) or _BIT_DURATION_DEFAULT)
    transmitter = Transmitter(cpu_controller, protocol)

    if args.gesture:
        try:
            bits = engine.get_bits(args.gesture)
        except GestureNotFoundError as exc:
            logger.error(str(exc))
            return 1
        message = args.gesture
        # Agent 1 Transmitter.send_gesture exists; use send_bits directly for
        # full control over bit duration.
        ok = transmitter.send_bits(list(bits), bit_duration)
    elif args.message:
        message = args.message
        ok = transmitter.send_message(message, bit_duration=bit_duration)
        bits = protocol.encode_message(message) if hasattr(protocol, "encode_message") else protocol.encode(message)
    else:
        logger.error("Either --message or --gesture is required for 'send'")
        return 1

    logger.info("Sending: %s", message)
    if ok:
        logger.info("Send complete")
        return 0
    logger.error("Send failed")
    return 1


# ------------------------------------------------------------------ #
# Command: test
# ------------------------------------------------------------------ #
def cmd_test(args: argparse.Namespace) -> int:
    engine = _build_engine(args.config)

    if args.pattern == "fixed":
        # Test all default gestures encode/decode round-trip
        all_gestures = engine.list_gestures()
        failures = 0
        for name, entry in all_gestures.items():
            bits = entry["bits"]
            encoded_name = engine.get_gesture(bits)
            if encoded_name != name:
                logger.error("Round-trip failed for %s: got %s", name, encoded_name)
                failures += 1
            else:
                logger.info("PASS: %s -> bits %s -> %s", name, "".join(str(b) for b in bits), encoded_name)
        if failures:
            logger.error("%d round-trip failure(s)", failures)
            return 1
        logger.info("All %d gestures passed round-trip test", len(all_gestures))
        return 0

    if args.distances:
        # Print pairwise Hamming distances between all gesture bit patterns
        all_gestures = engine.list_gestures()
        names = sorted(all_gestures.keys())
        logger.info("Pairwise Hamming distances:")
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a = "".join(str(b) for b in all_gestures[names[i]]["bits"])
                b = "".join(str(bit) for bit in all_gestures[names[j]]["bits"])
                dist = sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))
                logger.info("  %s vs %s: %d", names[i], names[j], dist)
        return 0

    logger.error("Specify --pattern fixed or --distances for 'test'")
    return 1


# ------------------------------------------------------------------ #
# Command: decode
# ------------------------------------------------------------------ #
def cmd_decode(args: argparse.Namespace) -> int:
    try:
        record = decode_file(args.file)
    except (FileNotFoundError, ValueError) as exc:
        logger.error(str(exc))
        return 1

    bits = record.get("bits", [])
    engine = _build_engine(args.config)

    # Detect sync using Agent 2's find_sync_header if available, else stub
    sync_pos = None
    try:
        from receiver.analysis.sync_detector import find_sync_header  # noqa: E402
        from shared.constants import SYNC_HEADER as _SYNC_HEADER  # noqa: E402
        sync_pos = find_sync_header(bits, list(_SYNC_HEADER))
        if sync_pos < 0:
            sync_pos = None
    except ImportError:
        sync_pos = detect_sync(bits)

    if sync_pos is not None:
        logger.info("Sync detected at position %d", sync_pos)

    # Decode message
    message = record.get("message", "")
    if not message and bits:
        try:
            protocol = Protocol()
            message = protocol.decode_bits(bits) if hasattr(protocol, "decode_bits") else protocol.decode(bits)
        except Exception:  # noqa: BLE001
            message = ""
    logger.info("Decoded message: %s", message)

    # Try to match gesture names from the bit stream (greedy prefix-free match)
    pos = 0
    recognized: List[str] = []
    while pos < len(bits):
        matched = False
        for length in range(1, len(bits) - pos + 1):
            chunk = bits[pos:pos + length]
            name = engine.get_gesture(chunk)
            if name is not None:
                recognized.append(name)
                pos += length
                matched = True
                break
        if not matched:
            pos += 1

    if recognized:
        logger.info("Recognized gestures: %s", " -> ".join(recognized))

    logger.info("Decode complete: bits=%d, gestures=%d, sync=%s",
                len(bits), len(record.get("gestures", []) or []), sync_pos is not None)
    return 0


# ------------------------------------------------------------------ #
# Command: ack
# ------------------------------------------------------------------ #
def cmd_ack(args: argparse.Namespace) -> int:
    if args.start_server:
        from ack.ack_server import run_server  # noqa: E402
        run_server(host="0.0.0.0", port=args.port)
        return 0
    logger.error("Use --start-server to launch the ACK server")
    return 1


# ------------------------------------------------------------------ #
# Command: gestures
# ------------------------------------------------------------------ #
def cmd_gestures(args: argparse.Namespace) -> int:
    engine = _build_engine(args.config)

    if args.list:
        gestures = engine.list_gestures()
        if not gestures:
            logger.info("No gestures configured")
            return 0
        for name, entry in sorted(gestures.items()):
            bits = "".join(str(b) for b in entry["bits"])
            aliases = ", ".join(entry["aliases"])
            logger.info(
                "  %s | bits=%s | aliases=[%s] | cat=%s | prio=%d",
                name, bits, aliases, entry["category"], entry["priority"],
            )
        return 0

    if args.add:
        name = args.add
        if not args.bits:
            logger.error("--bits is required with --add")
            return 1
        try:
            bits = [int(c) for c in args.bits if c in ("0", "1")]
        except ValueError:
            logger.error("Invalid bits string: %s", args.bits)
            return 1
        aliases = [a.strip() for a in args.aliases.split(",")] if args.aliases else []
        ok = engine.add_gesture(name, bits, aliases=aliases)
        if ok:
            logger.info("Added gesture %s with bits %s", name, args.bits)
            return 0
        logger.error("Failed to add gesture %s (validation failed)", name)
        return 1

    if args.remove:
        name = args.remove
        if engine.remove_gesture(name):
            logger.info("Removed gesture %s", name)
            return 0
        logger.error("Gesture %s not found", name)
        return 1

    if args.export_profile:
        profile = engine.export_profile(args.export_profile)
        import json
        print(json.dumps(profile, indent=2, ensure_ascii=False))
        return 0

    if args.import_profile:
        ok = engine.import_profile(args.import_profile)
        if ok:
            logger.info("Imported profile from %s", args.import_profile)
            return 0
        logger.error("Failed to import profile from %s", args.import_profile)
        return 1

    logger.error("Specify one of: --list, --add, --remove, --export-profile, --import-profile")
    return 1


# ------------------------------------------------------------------ #
# Command: serve
# ------------------------------------------------------------------ #
def cmd_serve(args: argparse.Namespace) -> int:
    try:
        from http.server import HTTPServer, SimpleHTTPRequestHandler
        import os
    except ImportError as exc:
        logger.error("Failed to import http.server: %s", exc)
        return 1

    page_dir = os.path.abspath(args.page)
    if not os.path.isdir(page_dir):
        logger.error("Page directory not found: %s", page_dir)
        return 1

    os.chdir(page_dir)
    server = HTTPServer(("0.0.0.0", args.port), SimpleHTTPRequestHandler)
    logger.info("Serving %s on port %d", page_dir, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped")
        server.server_close()
    return 0


# ------------------------------------------------------------------ #
# Argument parser
# ------------------------------------------------------------------ #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AirGesture CLI — gesture system unified entry point",
    )
    parser.add_argument(
        "--config", default=DEFAULT_CONFIG,
        help="Path to gestures JSON config (default: gestures/gestures.json)",
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # send
    p_send = sub.add_parser("send", help="Send a message or gesture")
    p_send.add_argument("--message", type=str, help="Text message to send")
    p_send.add_argument("--gesture", type=str, help="Gesture name to send")
    p_send.add_argument("--bit-duration", type=float, default=1.0, help="Bit duration in seconds")
    p_send.set_defaults(func=cmd_send)

    # test
    p_test = sub.add_parser("test", help="Run pattern/distance tests")
    p_test.add_argument("--pattern", type=str, choices=["fixed"], help="Test pattern type")
    p_test.add_argument("--distances", action="store_true", help="Show pairwise Hamming distances")
    p_test.set_defaults(func=cmd_test)

    # decode
    p_decode = sub.add_parser("decode", help="Decode a recording file")
    p_decode.add_argument("--file", type=str, required=True, help="Path to recording JSON file")
    p_decode.set_defaults(func=cmd_decode)

    # ack
    p_ack = sub.add_parser("ack", help="ACK server operations")
    p_ack.add_argument("--start-server", action="store_true", help="Start the ACK server")
    p_ack.add_argument("--port", type=int, default=8888, help="ACK server port (default: 8888)")
    p_ack.set_defaults(func=cmd_ack)

    # gestures
    p_gest = sub.add_parser("gestures", help="Manage gestures")
    p_gest.add_argument("--list", action="store_true", help="List all gestures")
    p_gest.add_argument("--add", type=str, metavar="NAME", help="Add a gesture by name")
    p_gest.add_argument("--bits", type=str, help="Bit string (e.g. 1010) for --add")
    p_gest.add_argument("--aliases", type=str, help="Comma-separated aliases for --add")
    p_gest.add_argument("--remove", type=str, metavar="NAME", help="Remove a gesture by name")
    p_gest.add_argument("--export-profile", type=str, metavar="NAME", help="Export a profile")
    p_gest.add_argument("--import-profile", type=str, metavar="PATH", help="Import a profile from JSON")
    p_gest.set_defaults(func=cmd_gestures)

    # serve
    p_serve = sub.add_parser("serve", help="Serve a web page")
    p_serve.add_argument("--page", type=str, default="receiver/web/", help="Directory to serve")
    p_serve.add_argument("--port", type=int, default=8080, help="HTTP port (default: 8080)")
    p_serve.set_defaults(func=cmd_serve)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
