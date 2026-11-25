"""GestureEngine — flexible, thread-safe, prefix-free gesture bit-pattern manager.

All gestures are defined in JSON configuration. Adding a gesture requires only
a JSON entry — zero code changes. The engine enforces the prefix-free property
so no gesture's bit pattern is a prefix of another, enabling unambiguous
streaming decoding.

Thread safety: all public mutating methods acquire a threading.Lock.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class GestureEngineError(Exception):
    """Base exception for GestureEngine errors."""


class GestureNotFoundError(GestureEngineError):
    """Raised when a gesture name or alias is not found."""

    def __init__(self, identifier: str, available: List[str]) -> None:
        self.identifier = identifier
        self.available = available
        message = (
            f"Gesture '{identifier}' not found. "
            f"Available gestures: {', '.join(sorted(available))}"
        )
        super().__init__(message)


class DuplicateBitsError(GestureEngineError):
    """Raised when a bit pattern collides with an existing gesture."""


class PrefixFreeViolationError(GestureEngineError):
    """Raised when adding a pattern would break the prefix-free property."""


def _bits_to_key(bits: List[int]) -> str:
    """Convert a bit list to a stable string key."""
    return "".join(str(b) for b in bits)


def _key_to_bits(key: str) -> List[int]:
    """Convert a string key back to a bit list."""
    return [int(c) for c in key]


def _is_prefix(shorter: str, longer: str) -> bool:
    """Return True if `shorter` is a prefix of `longer`."""
    return longer.startswith(shorter) and len(shorter) < len(longer)


def _hamming_distance(a: str, b: str) -> int:
    """Hamming distance between two equal-length bit strings."""
    if len(a) != len(b):
        return max(len(a), len(b))  # treat length mismatch as max distance
    return sum(1 for x, y in zip(a, b) if x != y)


class GestureEngine:
    """Manages gesture bit patterns with prefix-free enforcement.

    Parameters
    ----------
    config_path : str
        Path to the gestures JSON configuration file.
    """

    def __init__(self, config_path: str = "gestures/gestures.json") -> None:
        self.config_path = os.path.abspath(config_path)
        self._lock = threading.RLock()
        self._version: str = "1.0"
        self._encoding: str = "prefix-free"
        self._fuzzy_tolerance: int = 0
        self._bit_duration_default: float = 1.0
        self._gestures: Dict[str, Dict[str, Any]] = {}
        self._bits_to_name: Dict[str, str] = {}
        self._alias_to_name: Dict[str, str] = {}
        self._name_to_bits: Dict[str, List[int]] = {}
        self._reserved: Dict[str, str] = {}
        self._profiles: Dict[str, str] = {}
        self._dirty: bool = False
        self._last_mtime: Optional[float] = None
        self._watch_interval: float = 1.0
        self._load_config()

    # ------------------------------------------------------------------ #
    # Configuration loading
    # ------------------------------------------------------------------ #
    def _load_config(self) -> None:
        """Load and validate the gestures JSON config file."""
        if not os.path.exists(self.config_path):
            logger.warning(
                "Config file not found: %s. Starting with empty gesture set.",
                self.config_path,
            )
            self._reset_state()
            return

        mtime = os.path.getmtime(self.config_path)
        if self._last_mtime is not None and mtime == self._last_mtime:
            return  # no change since last load

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load gesture config %s: %s", self.config_path, exc)
            raise

        self._version = data.get("version", "1.0")
        self._encoding = data.get("encoding", "prefix-free")
        self._fuzzy_tolerance = int(data.get("fuzzy_tolerance", 0))
        self._bit_duration_default = float(data.get("bit_duration_default", 1.0))
        self._reserved = data.get("reserved", {})
        self._profiles = data.get("profiles", {})

        raw_gestures = data.get("gestures", {})
        self._gestures = {}
        for name, entry in raw_gestures.items():
            self._gestures[name] = {
                "bits": [int(b) for b in entry.get("bits", [])],
                "aliases": list(entry.get("aliases", [])),
                "description": entry.get("description", ""),
                "category": entry.get("category", ""),
                "priority": int(entry.get("priority", 1)),
                "metadata": dict(entry.get("metadata", {})),
            }

        self._rebuild_indexes()
        self._last_mtime = mtime
        self._dirty = False
        logger.info(
            "Loaded %d gestures from %s (version=%s, tolerance=%d)",
            len(self._gestures),
            self.config_path,
            self._version,
            self._fuzzy_tolerance,
        )

    def _reset_state(self) -> None:
        """Reset all in-memory state to empty."""
        self._gestures = {}
        self._bits_to_name = {}
        self._alias_to_name = {}
        self._name_to_bits = {}
        self._reserved = {}
        self._profiles = {}
        self._dirty = False

    def _rebuild_indexes(self) -> None:
        """Rebuild bits-to-name and alias-to-name indexes from _gestures."""
        self._bits_to_name = {}
        self._alias_to_name = {}
        self._name_to_bits = {}
        for name, entry in self._gestures.items():
            bits = entry["bits"]
            key = _bits_to_key(bits)
            self._bits_to_name[key] = name
            self._name_to_bits[name] = list(bits)
            for alias in entry.get("aliases", []):
                self._alias_to_name[alias] = name

    # ------------------------------------------------------------------ #
    # Hot-reload / file watching
    # ------------------------------------------------------------------ #
    def reload(self) -> None:
        """Hot-reload the configuration from disk (forces re-read)."""
        with self._lock:
            self._last_mtime = None  # force re-read
            self._load_config()

    def _check_file_changed(self) -> bool:
        """Return True if the config file has been modified on disk."""
        if not os.path.exists(self.config_path):
            return False
        mtime = os.path.getmtime(self.config_path)
        return self._last_mtime is not None and mtime != self._last_mtime

    # ------------------------------------------------------------------ #
    # Lookup API
    # ------------------------------------------------------------------ #
    def get_bits(self, gesture_name: str) -> List[int]:
        """Return the bit pattern for a gesture name or alias.

        Parameters
        ----------
        gesture_name : str
            Canonical gesture name or any registered alias.

        Returns
        -------
        List[int]
            The bit pattern (list of 0/1 ints).

        Raises
        ------
        GestureNotFoundError
            If neither the name nor any alias matches.
        """
        with self._lock:
            name = self._resolve_name_locked(gesture_name)
            if name is None:
                available = sorted(list(self._gestures.keys()) + list(self._alias_to_name.keys()))
                raise GestureNotFoundError(gesture_name, available)
            return list(self._name_to_bits[name])

    def _resolve_name_locked(self, identifier: str) -> Optional[str]:
        """Resolve a name or alias to its canonical gesture name (caller holds lock)."""
        if identifier in self._gestures:
            return identifier
        if identifier in self._alias_to_name:
            return self._alias_to_name[identifier]
        return None

    def resolve_alias(self, alias: str) -> Optional[str]:
        """Return the canonical gesture name for an alias, or None if not found."""
        with self._lock:
            return self._alias_to_name.get(alias)

    def get_all_aliases(self) -> Dict[str, List[str]]:
        """Return a mapping of gesture name -> list of aliases."""
        with self._lock:
            return {
                name: list(entry.get("aliases", []))
                for name, entry in self._gestures.items()
            }

    def get_gesture(self, bits: List[int]) -> Optional[str]:
        """Look up a gesture by its bit pattern.

        Exact match first. If none, attempts a fuzzy match within
        ``fuzzy_tolerance`` (Hamming distance for equal-length patterns;
        length-difference penalty for unequal lengths). Returns None if no
        match is found.

        Parameters
        ----------
        bits : List[int]
            Bit pattern to look up.

        Returns
        -------
        Optional[str]
            Canonical gesture name, or None.
        """
        key = _bits_to_key(bits)
        with self._lock:
            # Exact match
            if key in self._bits_to_name:
                return self._bits_to_name[key]

            # Fuzzy match
            if self._fuzzy_tolerance > 0:
                best_name: Optional[str] = None
                best_dist: Optional[int] = None
                for existing_key, name in self._bits_to_name.items():
                    dist = _hamming_distance(key, existing_key)
                    if dist <= self._fuzzy_tolerance:
                        if best_dist is None or dist < best_dist:
                            best_dist = dist
                            best_name = name
                if best_name is not None:
                    logger.debug(
                        "Fuzzy matched bits %s -> %s (distance=%d)",
                        key, best_name, best_dist,
                    )
                    return best_name

            return None

    def validate_gesture(
        self, name: str, bits: List[int], exclude_name: Optional[str] = None
    ) -> bool:
        """Validate a gesture without adding it.

        Checks:
        - name not already used (unless exclude_name matches)
        - bits pattern not duplicated
        - prefix-free property maintained against all existing gestures

        Parameters
        ----------
        name : str
            Proposed gesture name.
        bits : List[int]
            Proposed bit pattern.
        exclude_name : Optional[str]
            If updating an existing gesture, its own name to skip in the
            duplicate-name check.

        Returns
        -------
        bool
            True if valid, False otherwise.
        """
        key = _bits_to_key(bits)
        with self._lock:
            # Name conflict
            if name in self._gestures and name != exclude_name:
                logger.warning("Gesture name already exists: %s", name)
                return False

            # Duplicate bits
            if key in self._bits_to_name:
                existing = self._bits_to_name[key]
                if existing != exclude_name:
                    logger.warning(
                        "Bits %s already used by gesture %s", key, existing
                    )
                    return False

            # Prefix-free: new pattern must not be a prefix of any existing,
            # and no existing pattern may be a prefix of the new one.
            for existing_key, existing_name in self._bits_to_name.items():
                if existing_name == exclude_name:
                    continue
                if _is_prefix(key, existing_key):
                    logger.warning(
                        "Prefix violation: %s is prefix of %s (%s)",
                        key, existing_key, existing_name,
                    )
                    return False
                if _is_prefix(existing_key, key):
                    logger.warning(
                        "Prefix violation: %s (%s) is prefix of %s",
                        existing_key, existing_name, key,
                    )
                    return False

            return True

    # ------------------------------------------------------------------ #
    # Mutation API
    # ------------------------------------------------------------------ #
    def add_gesture(
        self,
        name: str,
        bits: List[int],
        aliases: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        description: str = "",
        category: str = "",
        priority: int = 1,
    ) -> bool:
        """Add a new gesture.

        Validates name uniqueness, bit-pattern uniqueness, and the
        prefix-free property. Saves to the config file immediately.

        Returns True on success, False if validation fails.
        """
        if aliases is None:
            aliases = []
        if metadata is None:
            metadata = {}

        # Validate bits are 0/1
        if not all(b in (0, 1) for b in bits):
            logger.error("Invalid bits (must be 0/1): %s", bits)
            return False

        with self._lock:
            if not self.validate_gesture(name, bits):
                return False

            # Also check alias conflicts
            for alias in aliases:
                if alias in self._alias_to_name:
                    logger.warning("Alias '%s' already in use", alias)
                    return False

            entry = {
                "bits": list(bits),
                "aliases": list(aliases),
                "description": description,
                "category": category,
                "priority": int(priority),
                "metadata": dict(metadata),
            }
            self._gestures[name] = entry
            self._rebuild_indexes()
            self._dirty = True
            self._persist()
            logger.info("Added gesture %s with bits %s", name, bits)
            return True

    def remove_gesture(self, name: str) -> bool:
        """Remove a gesture by name. Returns True if removed, False if not found."""
        with self._lock:
            if name not in self._gestures:
                return False
            del self._gestures[name]
            self._rebuild_indexes()
            self._dirty = True
            self._persist()
            logger.info("Removed gesture %s", name)
            return True

    def update_gesture(
        self,
        name: str,
        new_bits: Optional[List[int]] = None,
        new_aliases: Optional[List[str]] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update an existing gesture's bits, aliases, or metadata.

        Returns True on success, False if the gesture doesn't exist or
        validation fails.
        """
        with self._lock:
            if name not in self._gestures:
                return False

            current = self._gestures[name]
            bits = list(current["bits"]) if new_bits is None else [int(b) for b in new_bits]
            aliases = list(current["aliases"]) if new_aliases is None else list(new_aliases)
            desc = current["description"] if description is None else description
            cat = current["category"] if category is None else category
            prio = current["priority"] if priority is None else int(priority)
            meta = dict(current["metadata"]) if metadata is None else dict(metadata)

            if not all(b in (0, 1) for b in bits):
                logger.error("Invalid bits (must be 0/1): %s", bits)
                return False

            if not self.validate_gesture(name, bits, exclude_name=name):
                return False

            for alias in aliases:
                if alias in self._alias_to_name and self._alias_to_name[alias] != name:
                    logger.warning("Alias '%s' already in use by another gesture", alias)
                    return False

            self._gestures[name] = {
                "bits": bits,
                "aliases": aliases,
                "description": desc,
                "category": cat,
                "priority": prio,
                "metadata": meta,
            }
            self._rebuild_indexes()
            self._dirty = True
            self._persist()
            logger.info("Updated gesture %s", name)
            return True

    # ------------------------------------------------------------------ #
    # Listing / introspection
    # ------------------------------------------------------------------ #
    def list_gestures(self) -> Dict[str, Dict[str, Any]]:
        """Return a deep copy of all gestures."""
        with self._lock:
            import copy
            return copy.deepcopy(self._gestures)

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def _persist(self) -> None:
        """Write the current in-memory state back to the config file."""
        data = {
            "version": self._version,
            "encoding": self._encoding,
            "fuzzy_tolerance": self._fuzzy_tolerance,
            "bit_duration_default": self._bit_duration_default,
            "gestures": {
                name: {
                    "bits": entry["bits"],
                    "aliases": entry["aliases"],
                    "description": entry["description"],
                    "category": entry["category"],
                    "priority": entry["priority"],
                    "metadata": entry["metadata"],
                }
                for name, entry in self._gestures.items()
            },
            "reserved": self._reserved,
            "profiles": self._profiles,
        }
        tmp_path = self.config_path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.config_path)
            self._last_mtime = os.path.getmtime(self.config_path)
            self._dirty = False
        except OSError as exc:
            logger.error("Failed to persist gesture config: %s", exc)
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    # ------------------------------------------------------------------ #
    # Profiles
    # ------------------------------------------------------------------ #
    def export_profile(self, profile_name: str) -> Dict[str, Any]:
        """Export the current gesture set as a profile dictionary.

        Parameters
        ----------
        profile_name : str
            Name of the profile (used as the top-level key).

        Returns
        -------
        Dict[str, Any]
            Profile dictionary suitable for saving as JSON.
        """
        with self._lock:
            return {
                "profile_name": profile_name,
                "version": self._version,
                "encoding": self._encoding,
                "fuzzy_tolerance": self._fuzzy_tolerance,
                "bit_duration_default": self._bit_duration_default,
                "gestures": {
                    name: {
                        "bits": entry["bits"],
                        "aliases": entry["aliases"],
                        "description": entry["description"],
                        "category": entry["category"],
                        "priority": entry["priority"],
                        "metadata": entry["metadata"],
                    }
                    for name, entry in self._gestures.items()
                },
                "reserved": self._reserved,
            }

    def import_profile(self, profile_path: str) -> bool:
        """Import gestures from a profile JSON file, merging into the current set.

        Existing gestures with the same name are overwritten. New gestures are
        validated for prefix-free compliance before being added.

        Parameters
        ----------
        profile_path : str
            Path to the profile JSON file.

        Returns
        -------
        bool
            True if import succeeded.
        """
        if not os.path.exists(profile_path):
            logger.error("Profile file not found: %s", profile_path)
            return False

        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to read profile %s: %s", profile_path, exc)
            return False

        gestures = data.get("gestures", {})
        with self._lock:
            # Validate all first, then apply
            for name, entry in gestures.items():
                bits = [int(b) for b in entry.get("bits", [])]
                if not self.validate_gesture(name, bits):
                    logger.error(
                        "Import aborted: gesture %s fails validation", name
                    )
                    return False

            # Apply
            for name, entry in gestures.items():
                bits = [int(b) for b in entry.get("bits", [])]
                aliases = list(entry.get("aliases", []))
                self._gestures[name] = {
                    "bits": bits,
                    "aliases": aliases,
                    "description": entry.get("description", ""),
                    "category": entry.get("category", ""),
                    "priority": int(entry.get("priority", 1)),
                    "metadata": dict(entry.get("metadata", {})),
                }

            # Update tolerances if present
            if "fuzzy_tolerance" in data:
                self._fuzzy_tolerance = int(data["fuzzy_tolerance"])
            if "bit_duration_default" in data:
                self._bit_duration_default = float(data["bit_duration_default"])

            self._rebuild_indexes()
            self._dirty = True
            self._persist()
            logger.info("Imported %d gestures from profile %s", len(gestures), profile_path)
            return True

    # ------------------------------------------------------------------ #
    # Reserved patterns
    # ------------------------------------------------------------------ #
    def is_reserved(self, bits: List[int]) -> bool:
        """Return True if the bit pattern matches a reserved pattern."""
        key = _bits_to_key(bits)
        return key in self._reserved

    def get_reserved_name(self, bits: List[int]) -> Optional[str]:
        """Return the reserved pattern's name, or None if not reserved."""
        key = _bits_to_key(bits)
        return self._reserved.get(key)
