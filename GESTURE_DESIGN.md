# Gesture Design

## Philosophy

The gesture system is built around **maximum flexibility** and **zero code
changes** for adding new gestures. All gesture definitions live in JSON
configuration files. The `GestureEngine` class reads from these files and
provides a complete API for lookup, addition, removal, validation, and
profile import/export.

Key design goals:

1. **Plugin architecture** — Adding a gesture = adding a JSON entry. No Python
   code changes required.
2. **Prefix-free codes** — Guarantees unambiguous decoding of streaming bit
   sequences.
3. **Thread safety** — All mutations protected by `threading.Lock` for safe
   concurrent access.
4. **Variable-length patterns** — Gestures can have different bit lengths.
5. **Hot reload** — Configuration changes on disk are picked up via `reload()`.
6. **Alias support** — Multiple names can map to the same gesture.
7. **Fuzzy matching** — Configurable tolerance for noisy sensor readings.
8. **Reserved patterns** — Special bit patterns reserved for control purposes.

## Why Prefix-Free Codes

A prefix-free code ensures that no valid bit pattern is a prefix of another
valid pattern. This is critical for **streaming decoding**: as bits arrive
one at a time, the decoder can recognize a complete gesture the moment its
full pattern has been received, without needing to wait for more bits or
worry about ambiguity.

### Example

Given gestures:
- `wave` = `0001`
- `tap`  = `0010`

These are prefix-free: neither `0001` nor `0010` is a prefix of the other.

### Violation Example

If we had:
- `short` = `00`
- `wave`  = `0001`

Then `00` is a prefix of `0001`. When the decoder sees `0001`, it can't tell
whether it's `short` followed by `01`, or `wave`. The `GestureEngine`
rejects such configurations at `add_gesture()` time.

### How Prefix-Free is Enforced

When adding a gesture with bits `B`:
1. For every existing gesture with bits `E`:
   - Reject if `B` is a prefix of `E` (i.e., `E.startswith(B)` and `len(B) < len(E)`)
   - Reject if `E` is a prefix of `B` (i.e., `B.startswith(E)` and `len(E) < len(B)`)
2. Reject if `B` exactly matches an existing pattern (duplicate).

## How to Extend

### Adding a New Gesture

**Option A — Edit JSON directly:**

Edit `gestures/gestures.json`:

```json
"peace_sign": {
  "bits": [1, 0, 1, 0],
  "aliases": ["victory", "two"],
  "description": "Peace sign",
  "category": "action",
  "priority": 1
}
```

**Option B — Use the CLI:**

```bash
python main.py gestures --add peace_sign --bits 1010 --aliases victory,two
```

**Option C — Use the Python API:**

```python
from gestures import GestureEngine
engine = GestureEngine()
engine.add_gesture("peace_sign", [1, 0, 1, 0], aliases=["victory", "two"])
```

### Creating a Custom Profile

1. Export the current gesture set:
   ```bash
   python main.py gestures --export-profile my_profile > my_profile.json
   ```
2. Edit `my_profile.json` to add/remove/modify gestures.
3. Import it:
   ```bash
   python main.py gestures --import-profile my_profile.json
   ```
4. Or save it to `gestures/gesture_profiles/my_profile.json` and reference it.

### Using Aliases

Aliases let you refer to a gesture by multiple names:

```python
engine.get_bits("wave")     # [0, 0, 0, 1]
engine.get_bits("hi")       # [0, 0, 0, 1] (alias for wave)
engine.get_bits("hello")    # [0, 0, 0, 1] (alias for wave)

engine.resolve_alias("hi")  # "wave" (returns canonical name)
```

### How Fuzzy Matching Works

When `fuzzy_tolerance > 0`, `get_gesture()` performs a fuzzy match using
Hamming distance:

- For equal-length patterns: Hamming distance = number of differing bits
- For unequal-length patterns: distance = Hamming + length difference

If a pattern is within `fuzzy_tolerance` of a known gesture, that gesture
is returned. This provides noise tolerance for sensor readings.

```python
engine._fuzzy_tolerance = 1
engine.get_gesture([0, 0, 0, 0])  # "wave" — 1 bit away from [0,0,0,1]
```

### Reserved Patterns

Reserved patterns are excluded from normal gesture matching and serve as
control markers:

| Pattern | Name | Purpose |
|---------|------|---------|
| `1110` | `future_use` | Reserved for future protocol extensions |
| `1111` | `end_of_message` | Marks the end of a message frame |

## Future: Sensor-Based Gesture Detection Integration

The `GestureEngine` is designed to be the bridge between raw sensor data and
gesture commands. Future integration points:

1. **Sensor → bits**: A sensor-based classifier (e.g., MediaPipe hand
   landmarks) produces bit patterns that are passed to
   `engine.get_gesture(bits)` for recognition.
2. **Calibration**: The `bit_duration_default` config field allows tuning
   the timing of bit transmission for different sensor hardware.
3. **Profiles**: Different sensor setups can use different gesture profiles
   loaded via `import_profile()`.
4. **Stabilization**: Future work can add temporal smoothing (e.g., requiring
   N consecutive frames of the same gesture before emitting).
