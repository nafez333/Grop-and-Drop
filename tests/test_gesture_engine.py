"""Tests for GestureEngine."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

# Ensure the workspace root is on sys.path so `gestures` is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gestures import GestureEngine, GestureNotFoundError  # noqa: E402


class TestGestureEngine(unittest.TestCase):
    """Test the GestureEngine class against an isolated temp config."""

    def setUp(self) -> None:
        # Copy default config to a temp file so tests don't interfere
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".json")
        with open("gestures/gestures.json", "r", encoding="utf-8") as src:
            config_data = src.read()
        with os.fdopen(self._tmp_fd, "w", encoding="utf-8") as dst:
            dst.write(config_data)
        self.engine = GestureEngine(config_path=self._tmp_path)

    def tearDown(self) -> None:
        try:
            os.unlink(self._tmp_path)
        except OSError:
            pass

    def test_get_bits_all_default_gestures(self):
        """get_bits returns correct bits for all default gestures."""
        expected = {
            "wave": [0, 0, 0, 1],
            "tap": [0, 0, 1, 0],
            "circle": [0, 0, 1, 1],
            "shake": [0, 1, 0, 0],
            "nod": [0, 1, 0, 1],
            "swipe_left": [0, 1, 1, 0],
            "swipe_right": [0, 1, 1, 1],
            "fist": [1, 0, 0, 0],
            "open_palm": [1, 0, 0, 1],
        }
        for name, bits in expected.items():
            with self.subTest(gesture=name):
                self.assertEqual(self.engine.get_bits(name), bits)

    def test_get_bits_by_alias(self):
        """get_bits works with aliases."""
        self.assertEqual(self.engine.get_bits("hi"), [0, 0, 0, 1])   # wave alias
        self.assertEqual(self.engine.get_bits("click"), [0, 0, 1, 0])  # tap alias
        self.assertEqual(self.engine.get_bits("yes"), [0, 1, 0, 1])   # nod alias
        self.assertEqual(self.engine.get_bits("stop"), [1, 0, 0, 0])  # fist alias

    def test_get_bits_not_found(self):
        """get_bits raises GestureNotFoundError for unknown names."""
        with self.assertRaises(GestureNotFoundError) as ctx:
            self.engine.get_bits("nonexistent_gesture")
        self.assertIn("nonexistent_gesture", str(ctx.exception))
        self.assertIn("wave", str(ctx.exception))  # lists available gestures

    def test_get_gesture_reverse_lookup(self):
        """get_gesture returns the canonical name for exact bit matches."""
        self.assertEqual(self.engine.get_gesture([0, 0, 0, 1]), "wave")
        self.assertEqual(self.engine.get_gesture([1, 0, 0, 0]), "fist")
        self.assertEqual(self.engine.get_gesture([0, 1, 1, 1]), "swipe_right")

    def test_get_gesture_no_match(self):
        """get_gesture returns None for unmatched bits."""
        self.assertIsNone(self.engine.get_gesture([1, 1, 1, 1]))  # reserved
        self.assertIsNone(self.engine.get_gesture([0, 0, 0, 0]))  # not defined

    def test_resolve_alias(self):
        """resolve_alias returns the canonical gesture name."""
        self.assertEqual(self.engine.resolve_alias("hello"), "wave")
        self.assertEqual(self.engine.resolve_alias("no"), "shake")
        self.assertEqual(self.engine.resolve_alias("pause"), "open_palm")
        self.assertIsNone(self.engine.resolve_alias("not_an_alias"))

    def test_get_all_aliases(self):
        """get_all_aliases returns name -> aliases mapping."""
        aliases = self.engine.get_all_aliases()
        self.assertIn("wave", aliases)
        self.assertIn("hello", aliases["wave"])
        self.assertIn("hi", aliases["wave"])

    def test_add_gesture(self):
        """add_gesture adds a new gesture and persists it."""
        ok = self.engine.add_gesture(
            "peace_sign",
            bits=[1, 0, 1, 0],
            aliases=["victory", "two"],
            category="action",
            priority=1,
        )
        self.assertTrue(ok)
        self.assertEqual(self.engine.get_bits("peace_sign"), [1, 0, 1, 0])
        self.assertEqual(self.engine.get_bits("victory"), [1, 0, 1, 0])
        self.assertEqual(self.engine.get_gesture([1, 0, 1, 0]), "peace_sign")

    def test_add_gesture_duplicate_name(self):
        """add_gesture rejects duplicate gesture names."""
        ok = self.engine.add_gesture("wave", bits=[1, 1, 0, 0])
        self.assertFalse(ok)

    def test_add_gesture_duplicate_bits(self):
        """add_gesture rejects duplicate bit patterns."""
        ok = self.engine.add_gesture("new_gesture", bits=[0, 0, 0, 1])
        self.assertFalse(ok)

    def test_add_gesture_prefix_violation(self):
        """add_gesture rejects patterns that violate prefix-free property."""
        # [0,0] is a prefix of [0,0,0,1] (wave)
        ok = self.engine.add_gesture("shorty", bits=[0, 0])
        self.assertFalse(ok)

        # [0,0,0,1,1] has wave [0,0,0,1] as prefix
        ok = self.engine.add_gesture("longer", bits=[0, 0, 0, 1, 1])
        self.assertFalse(ok)

    def test_remove_gesture(self):
        """remove_gesture removes an existing gesture."""
        self.engine.add_gesture("temp_gesture", bits=[1, 1, 0, 1])
        self.assertEqual(self.engine.get_bits("temp_gesture"), [1, 1, 0, 1])
        ok = self.engine.remove_gesture("temp_gesture")
        self.assertTrue(ok)
        with self.assertRaises(GestureNotFoundError):
            self.engine.get_bits("temp_gesture")

    def test_remove_gesture_not_found(self):
        """remove_gesture returns False for unknown gesture."""
        self.assertFalse(self.engine.remove_gesture("nonexistent"))

    def test_validate_gesture(self):
        """validate_gesture checks correctness without side effects."""
        self.assertTrue(self.engine.validate_gesture("new_one", [1, 1, 0, 1]))
        self.assertFalse(self.engine.validate_gesture("wave", [1, 1, 0, 1]))  # name exists
        self.assertFalse(self.engine.validate_gesture("new_one", [0, 0, 0, 1]))  # bits exist

    def test_validate_gesture_prefix_free(self):
        """validate_gesture enforces prefix-free property."""
        self.assertFalse(self.engine.validate_gesture("x", [0, 0]))  # prefix of wave

    def test_fuzzy_matching(self):
        """get_gesture uses fuzzy matching when tolerance > 0."""
        engine = GestureEngine(config_path=self._tmp_path)
        engine._fuzzy_tolerance = 1
        engine._rebuild_indexes()
        # [0,0,0,0] is 1 bit away from wave [0,0,0,1]
        result = engine.get_gesture([0, 0, 0, 0])
        self.assertEqual(result, "wave")

    def test_fuzzy_tolerance_zero(self):
        """With tolerance 0, only exact matches succeed."""
        self.assertIsNone(self.engine.get_gesture([0, 0, 0, 0]))

    def test_hot_reload(self):
        """reload() re-reads config from disk."""
        # Add a gesture via direct file manipulation, then reload
        config_path = self.engine.config_path
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["gestures"]["temp_reload"] = {
            "bits": [1, 1, 0, 1],
            "aliases": ["temp"],
            "description": "temp",
            "category": "test",
            "priority": 1,
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        try:
            self.engine.reload()
            self.assertEqual(self.engine.get_bits("temp_reload"), [1, 1, 0, 1])
            self.assertEqual(self.engine.get_gesture([1, 1, 0, 1]), "temp_reload")
        finally:
            # Restore original
            del data["gestures"]["temp_reload"]
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.engine.reload()

    def test_list_gestures(self):
        """list_gestures returns all gestures as a dict."""
        gestures = self.engine.list_gestures()
        self.assertEqual(len(gestures), 9)
        self.assertIn("wave", gestures)
        self.assertIn("fist", gestures)

    def test_is_reserved(self):
        """is_reserved identifies reserved patterns."""
        self.assertTrue(self.engine.is_reserved([1, 1, 1, 1]))
        self.assertTrue(self.engine.is_reserved([1, 1, 1, 0]))
        self.assertFalse(self.engine.is_reserved([0, 0, 0, 1]))

    def test_get_reserved_name(self):
        """get_reserved_name returns the name of a reserved pattern."""
        self.assertEqual(self.engine.get_reserved_name([1, 1, 1, 1]), "end_of_message")
        self.assertEqual(self.engine.get_reserved_name([1, 1, 1, 0]), "future_use")
        self.assertIsNone(self.engine.get_reserved_name([0, 0, 0, 1]))

    def test_export_import_profile(self):
        """export_profile and import_profile round-trip."""
        profile = self.engine.export_profile("test_profile")
        self.assertEqual(profile["profile_name"], "test_profile")
        self.assertEqual(len(profile["gestures"]), 9)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(profile, f)
            tmp_path = f.name
        try:
            # Create a fresh engine with a temp config and import
            tmp_fd, tmp_cfg = tempfile.mkstemp(suffix=".json")
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as cfg_f:
                cfg_f.write(open("gestures/gestures.json", encoding="utf-8").read())
            engine2 = GestureEngine(config_path=tmp_cfg)
            engine2._gestures = {}  # clear
            engine2._rebuild_indexes()
            ok = engine2.import_profile(tmp_path)
            self.assertTrue(ok)
            self.assertEqual(engine2.get_bits("wave"), [0, 0, 0, 1])
            try:
                os.unlink(tmp_cfg)
            except OSError:
                pass
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
