# Gestures Module

This directory contains the gesture system configuration and engine for the
AirGesture project. All gestures are defined in JSON — adding a new gesture
requires zero code changes.

## Files

- `gesture_engine.py` — `GestureEngine` class: flexible, thread-safe,
  prefix-free gesture bit-pattern manager.
- `gestures.json` — Default gesture configuration (9 gestures + 2 reserved
  patterns).
- `gesture_profiles/default.json` — Default profile copy for customization.

## GestureEngine API

```python
from gestures import GestureEngine

engine = GestureEngine()

# Look up bits by name or alias
bits = engine.get_bits("wave")          # [0, 0, 0, 1]
bits = engine.get_bits("hi")            # [0, 0, 0, 1] (alias)

# Reverse lookup: bits -> gesture name
name = engine.get_gesture([0, 0, 0, 1]) # "wave"

# Add a new gesture (JSON-driven, zero code changes)
engine.add_gesture(
    "peace_sign",
    bits=[1, 0, 1, 0],
    aliases=["victory", "two"],
    category="action",
    priority=1,
)

# List all gestures
all_gestures = engine.list_gestures()

# Validate prefix-free property
valid = engine.validate_gesture("new_gesture", [1, 1, 1, 0])

# Hot-reload from disk
engine.reload()
```

## Prefix-Free Codes

No gesture's bit pattern may be a prefix of another's. This guarantees
unambiguous decoding of a streaming bit sequence: once a complete pattern is
matched, it cannot be confused with the start of a longer pattern.

For example, `0001` (wave) and `00011` would violate prefix-free because
`0001` is a prefix of `00011`.

## Reserved Patterns

Reserved patterns are excluded from normal gesture matching and can be used
as frame delimiters or control markers:

- `1110` — `future_use`
- `1111` — `end_of_message`

## Aliases

Each gesture can have multiple aliases. `get_bits()` accepts either the
canonical name or any alias. `resolve_alias()` returns the canonical name
for an alias.

## Fuzzy Matching

When `fuzzy_tolerance > 0`, `get_gesture()` performs a fuzzy match using
Hamming distance on equal-length patterns (with a length-difference penalty
for unequal lengths). This provides noise tolerance for sensor readings.
