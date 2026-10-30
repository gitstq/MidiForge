"""GM 名称表与工具函数测试。"""

from __future__ import annotations

import unittest

from midiforge.gm import (
    DRUM_CHANNEL,
    DRUM_MAP,
    GM_PROGRAMS,
    drum_name,
    key_name,
    note_name,
    pitch_label,
    program_name,
    ticks_to_note_name,
)


class TestNoteNames(unittest.TestCase):
    def test_middle_c(self):
        self.assertEqual(note_name(60), "C4")

    def test_a440(self):
        self.assertEqual(note_name(69), "A4")

    def test_lowest(self):
        self.assertEqual(note_name(0), "C-1")

    def test_highest(self):
        self.assertEqual(note_name(127), "G9")

    def test_flat_preference(self):
        self.assertEqual(note_name(61, prefer_flat=True), "Db4")

    def test_sharp_default(self):
        self.assertEqual(note_name(61), "C#4")

    def test_all_octaves_unique(self):
        names = {note_name(p) for p in range(128)}
        self.assertEqual(len(names), 128)


class TestPrograms(unittest.TestCase):
    def test_table_size(self):
        self.assertEqual(len(GM_PROGRAMS), 128)

    def test_first_program(self):
        self.assertEqual(program_name(0), "Acoustic Grand Piano")

    def test_last_program(self):
        self.assertEqual(program_name(127), "Gunshot")

    def test_out_of_range(self):
        self.assertTrue(program_name(200).startswith("program_"))

    def test_negative(self):
        self.assertTrue(program_name(-1).startswith("program_"))


class TestDrums(unittest.TestCase):
    def test_kick(self):
        self.assertEqual(drum_name(36), "Bass Drum 1")

    def test_snare(self):
        self.assertEqual(drum_name(38), "Acoustic Snare")

    def test_unknown_drum(self):
        self.assertTrue(drum_name(10).startswith("drum_"))

    def test_pitch_label_uses_drum(self):
        self.assertEqual(pitch_label(38, DRUM_CHANNEL), "Acoustic Snare")

    def test_pitch_label_uses_note(self):
        self.assertEqual(pitch_label(60, 0), "C4")

    def test_map_size(self):
        self.assertGreaterEqual(len(DRUM_MAP), 40)


class TestKeyNames(unittest.TestCase):
    def test_c_major(self):
        self.assertEqual(key_name(0, False), "C")

    def test_g_major(self):
        self.assertEqual(key_name(1, False), "G")

    def test_f_major(self):
        self.assertEqual(key_name(-1, False), "F")

    def test_a_minor(self):
        self.assertEqual(key_name(0, True), "Am")

    def test_flat_preference_same_key(self):
        self.assertEqual(key_name(2, False, prefer_flat=True), "D")

    def test_flat_preference_converts(self):
        self.assertEqual(key_name(6, False, prefer_flat=True), "Gb")

    def test_fifths_of_pitch_class(self):
        from midiforge.gm import fifths_of_pitch_class

        self.assertEqual(fifths_of_pitch_class(0), 0)
        self.assertEqual(fifths_of_pitch_class(7), 1)
        self.assertEqual(fifths_of_pitch_class(5), -1)


class TestDurationNames(unittest.TestCase):
    def test_whole_note(self):
        # 全音符 = 4 拍 = 4 × division
        self.assertEqual(ticks_to_note_name(1920, 480), "1/1")

    def test_quarter(self):
        self.assertEqual(ticks_to_note_name(480, 480), "1/4")

    def test_eighth(self):
        self.assertEqual(ticks_to_note_name(240, 480), "1/8")

    def test_sixteenth(self):
        self.assertEqual(ticks_to_note_name(120, 480), "1/16")

    def test_double_whole(self):
        self.assertEqual(ticks_to_note_name(3840, 480), "2/1")

    def test_zero(self):
        self.assertEqual(ticks_to_note_name(0, 480), "0")

    def test_long_note(self):
        self.assertTrue(ticks_to_note_name(4800, 480).endswith("/1"))

    def test_odd_value(self):
        self.assertTrue(ticks_to_note_name(37, 480).startswith("~"))


if __name__ == "__main__":
    unittest.main()
