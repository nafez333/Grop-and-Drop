# AirGesture — Touchless Gesture Control System

AirGesture is a touchless gesture recognition and control system that translates
hand gestures into bit-pattern commands, transmits them, and decodes them on the
receiving side. It includes a flexible gesture engine, an ACK acknowledgment
channel for phone feedback, a unified CLI, and a full test suite.

## Architecture

```text
+---------------------+      bits      +---------------------+
|   Phone / Client    | <------------> |   AirGesture PC     |
|  (ACK via HTTP)     |   ACK channel  |  (Gesture Engine)   |
+---------------------+                +---------------------+
                                             |
                                             | bits
                                             v
                                    +------------------+
                                    |  Transmitter   |
                                    |  (Agent 1)     |
                                    +------------------+
                                             |
                                             | bits
                                             v
                                    +------------------+
                                    |   Receiver     |
                                    |  (Agent 2)     |
                                    +------------------+
                                             |
                                             | decoded
                                             v
                                    +------------------+
                                    |   Decoder      |
                                    +------------------+
```

### Components

| Component | Owner | Responsibility |
|-----------|-------|----------------|
| `gestures/gesture_engine.py` | Agent 3 (You) | Gesture bit-pattern management, prefix-free codes, aliases |
| `ack/ack_server.py` | Agent 3 (You) | HTTP ACK endpoint for phone feedback |
| `ack/ack_client.js` | Agent 3 (You) | JavaScript client for sending ACKs from phone |
| `main.py` | Agent 3 (You) | Unified CLI: send, test, decode, ack, gestures, serve |
| `protocol.py` | Agent 1 | Transmitter, CPULoadController, Protocol, constants |
| `receiver.py` | Agent 2 | Receiver class, decode_file, JSON recording format |

## Installation

```bash
# Clone or navigate to the project
cd "C:\Users\CMC\Desktop\Grop and Drop"

# Create a virtual environment (recommended)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
pip install -r ack/requirements.txt
```

### Dependencies

- `flask==3.1.0` — ACK server web framework
- `flask-cors==5.0.0` — CORS support for phone access
- `numpy>=1.24` — Numerical operations (declared, available)
- Python 3.8+

## Usage

### CLI Commands

```bash
python main.py --help
```

#### `send` — Send a message or gesture

```bash
# Send a text message (encoded to bits via Protocol)
python main.py send --message "hello" --bit-duration 1.0

# Send a predefined gesture by name
python main.py send --gesture "wave"

# Send a gesture by alias
python main.py send --gesture "hi"
```

#### `test` — Run pattern/distance tests

```bash
# Test all default gestures encode/decode round-trip
python main.py test --pattern fixed

# Show pairwise Hamming distances between all gestures
python main.py test --distances
```

#### `decode` — Decode a recording file

```bash
python main.py decode --file data/recordings/recording.json
```

#### `ack` — Start the ACK server

```bash
# Start ACK server on port 8888
python main.py ack --start-server --port 8888
```

The server exposes:
- `POST /ack` — receive ACK from phone
- `GET /status` — return last ACK
- `GET /health` — health check

#### `gestures` — Manage gestures

```bash
# List all gestures
python main.py gestures --list

# Add a new gesture
python main.py gestures --add peace_sign --bits 1010 --aliases victory,two

# Remove a gesture
python main.py gestures --remove peace_sign

# Export current gesture set as a profile
python main.py gestures --export-profile my_profile

# Import a profile from JSON
python main.py gestures --import-profile path/to/profile.json
```

#### `serve` — Serve a web page

```bash
# Serve receiver web page on port 8080
python main.py serve --page receiver/web/ --port 8080
```

## Running the 30cm Experiment

The 30cm experiment validates gesture transmission at a 30cm distance
between the transmitting and receiving devices.

1. Start the receiver: `python main.py serve --page receiver/web/ --port 8080`
2. Start the ACK server: `python main.py ack --start-server --port 8888`
3. Position the transmitter 30cm from the receiver
4. Send a gesture: `python main.py send --gesture "wave" --bit-duration 1.0`
5. Verify the receiver decodes the correct gesture
6. Check ACK: `curl http://localhost:8888/status`

## Adding Custom Gestures

All gestures are defined in `gestures/gestures.json`. To add a new gesture:

1. Edit `gestures/gestures.json` and add a new entry under `"gestures"`:
   ```json
   "peace_sign": {
     "bits": [1, 0, 1, 0],
     "aliases": ["victory", "two"],
     "description": "Peace sign gesture",
     "category": "action",
     "priority": 1
   }
   ```
2. The bit pattern must be **prefix-free** (no existing gesture's bits may be a
   prefix of yours, and yours may not be a prefix of another's).
3. No code changes required — the engine reads from JSON.

Alternatively, use the CLI:
```bash
python main.py gestures --add peace_sign --bits 1010 --aliases victory,two
```

## Running Tests

```bash
python tests/run_all_tests.py
```

Exit code 0 = all passed, 1 = any failure.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `GestureNotFoundError` | Check the gesture name/alias exists in gestures.json |
| Prefix-free violation | Choose a bit pattern that isn't a prefix of any existing gesture |
| ACK server not reachable | Ensure Flask is installed and server is running on 0.0.0.0 |
| CORS errors from phone | `flask-cors` is enabled on the ACK server |
| Tests fail | Run `python tests/run_all_tests.py` and check output |

## Agent Responsibilities

| Agent | Responsibility | Files |
|-------|---------------|-------|
| Agent 1 | Transmitter, CPULoadController, Protocol, constants | `protocol.py`, `transmitter.py` |
| Agent 2 | Receiver, decode_file, JSON recording format | `receiver/` |
| Agent 3 (You) | Gesture engine, ACK channel, CLI, integration | `gestures/`, `ack/`, `main.py`, `tests/` |

## License

Internal project.
