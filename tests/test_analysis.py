"""分析模块测试：调性、和弦、直方图、统计。"""

from __future__ import annotations

import unittest

from midiforge.analysis import (
    chord_at,
    chord_progression,
    guess_key,
    pitch_class_histogram,
    repeated_patterns,
    rhythm_histogram,
    stats,
    track_summaries,
    velocity_histogram,
)
from midiforge.builder import demo_song, from_notes
from midiforge.notes import Note, extract_notes
from midiforge.tempo import TempoMap


def note(pitch, start, dur, channel=0, vel=90):
    return Note(track=0, channel=channel, pitch=pitch, velocity=vel, start=start, end=start + dur)


class TestChords(unittest.TestCase):
    def test_c_major(self):
        self.assertEqual(chord_at([60, 64, 67]), "Cmaj")

    def test_a_minor(self):
        self.assertEqual(chord_at([57, 60, 64]), "Amin")

    def test_dominant_seventh(self):
        self.assertEqual(chord_at([55, 59, 62, 65]), "Gdom7")

    def test_major_seventh(self):
        self.assertEqual(chord_at([60, 64, 67, 71]), "Cmaj7")

    def test_diminished(self):
        self.assertEqual(chord_at([59, 62, 65]), "Bdim")

    def test_augmented(self):
        self.assertEqual(chord_at([60, 64, 68]), "Caug")

    def test_power_chord(self):
        self.assertEqual(chord_at([45, 52]), "A5")

    def test_sus4(self):
        self.assertEqual(chord_at([60, 65, 67]), "Csus4")

    def test_duplicate_pitches_ignored(self):
        self.assertEqual(chord_at([60, 60, 64, 67]), "Cmaj")

    def test_octave_equivalent(self):
        self.assertEqual(chord_at([60, 72, 64, 79]), "Cmaj")

    def test_single_note_unknown(self):
        self.assertEqual(chord_at([60]), "?")

    def test_two_notes_interval(self):
        self.assertIn("+", chord_at([60, 66]))

    def test_unrecognised(self):
        self.assertEqual(chord_at([60, 61, 62]), "?")


class TestKey(unittest.TestCase):
    def test_c_major_scale(self):
        notes = [note(60 + i, i * 100, 100) for i in (0, 2, 4, 5, 7, 9, 11, 12, 7, 5, 4, 2)]
        key = guess_key(notes)
        self.assertEqual(key["key_label"], "C")
        self.assertEqual(key["scale"], "major")

    def test_a_minor_scale(self):
        # 带主音强调的自然小调乐句（更接近真实旋律的分布）
        seq = [57, 57, 60, 64, 57, 57, 59, 60, 62, 64, 65, 67,
               69, 69, 67, 65, 64, 62, 60, 59, 57, 57]
        notes = [note(p, i * 100, 100) for i, p in enumerate(seq)]
        key = guess_key(notes)
        self.assertEqual(key["key_label"], "Am")
        self.assertEqual(key["scale"], "minor")

    def test_minor_shares_relative_major_signature(self):
        seq = [57, 57, 60, 64, 57, 57, 59, 60, 62, 64, 65, 67,
               69, 69, 67, 65, 64, 62, 60, 59, 57, 57]
        notes = [note(p, i * 100, 100) for i, p in enumerate(seq)]
        self.assertEqual(guess_key(notes)["fifths"], 0)

    def test_insufficient_notes(self):
        self.assertEqual(guess_key([note(60, 0, 100)])["key"], "?")

    def test_confidence_range(self):
        notes = [note(60 + (i % 7), i * 100, 100) for i in range(20)]
        self.assertGreaterEqual(guess_key(notes)["confidence"], 0.0)
        self.assertLessEqual(guess_key(notes)["confidence"], 1.0)

    def test_drums_excluded(self):
        notes = [note(36, i * 10, 10, channel=9) for i in range(30)]
        self.assertEqual(guess_key(notes)["key"], "?")

    def test_histogram_length(self):
        self.assertEqual(len(pitch_class_histogram([note(60, 0, 100)])), 12)

    def test_histogram_weighted_by_duration(self):
        hist = pitch_class_histogram([note(60, 0, 100), note(60, 0, 300)])
        self.assertEqual(hist[0], 400.0)


class TestHistograms(unittest.TestCase):
    def test_velocity_histogram(self):
        notes = [note(60, 0, 10, vel=1), note(60, 20, 10, vel=127)]
        hist = velocity_histogram(notes, bins=8)
        self.assertEqual(sum(hist.values()), 2)

    def test_velocity_bins_count(self):
        hist = velocity_histogram([note(60, 0, 10, vel=v) for v in range(0, 128)], bins=8)
        self.assertEqual(len(hist), 8)

    def test_rhythm_histogram_names(self):
        notes = [note(60, 0, 480)]
        self.assertIn("1/4", rhythm_histogram(notes, 480))

    def test_rhythm_eighth(self):
        notes = [note(60, 0, 240)]
        self.assertIn("1/8", rhythm_histogram(notes, 480))

    def test_rhythm_long_note(self):
        notes = [note(60, 0, 4800)]
        self.assertIn("~2/1", rhythm_histogram(notes, 480))

    def test_zero_duration_handled(self):
        self.assertIn("0", rhythm_histogram([note(60, 0, 0)], 480))


class TestPatterns(unittest.TestCase):
    def test_repeated_pattern_found(self):
        seq = [60, 62, 64, 65, 60, 62, 64, 65]
        notes = [note(p, i * 100, 100) for i, p in enumerate(seq)]
        found = repeated_patterns(notes, n=3, top=3)
        self.assertTrue(found)
        self.assertGreater(found[0]["count"], 1)

    def test_no_repeat(self):
        notes = [note(60 + i, i * 100, 100) for i in range(6)]
        self.assertEqual(repeated_patterns(notes, n=4), [])

    def test_short_input(self):
        self.assertEqual(repeated_patterns([note(60, 0, 10)], n=4), [])


class TestStats(unittest.TestCase):
    def setUp(self):
        self.midi = demo_song(bars=2)
        self.tempo_map = TempoMap.from_midi(self.midi)
        self.notes = extract_notes(self.midi, tempo_map=self.tempo_map)

    def test_notes_count(self):
        report = stats(self.midi, self.notes, self.tempo_map)
        self.assertEqual(report["notes"], len(self.notes))

    def test_drum_notes_separated(self):
        report = stats(self.midi, self.notes, self.tempo_map)
        self.assertEqual(report["drum_notes"] + report["melodic_notes"], report["notes"])

    def test_pitch_range(self):
        report = stats(self.midi, self.notes, self.tempo_map)
        self.assertEqual(len(report["pitch_range"]), 2)

    def test_key_guess_present(self):
        report = stats(self.midi, self.notes, self.tempo_map)
        self.assertIn("confidence", report["key"])

    def test_tracks_length(self):
        report = stats(self.midi, self.notes, self.tempo_map)
        self.assertEqual(len(report["tracks"]), len(self.midi.tracks))

    def test_chord_progression_non_empty(self):
        report = stats(self.midi, self.notes, self.tempo_map)
        self.assertTrue(report["chords"])

    def test_notes_per_second_positive(self):
        report = stats(self.midi, self.notes, self.tempo_map)
        self.assertGreater(report["notes_per_second"], 0)

    def test_default_arguments(self):
        report = stats(self.midi)
        self.assertIn("notes", report)

    def test_empty_midi(self):
        midi = from_notes([])
        report = stats(midi)
        self.assertEqual(report["notes"], 0)
        self.assertEqual(report["max_polyphony"], 0)

    def test_track_summaries_names(self):
        summaries = track_summaries(self.midi, self.notes)
        self.assertEqual(summaries[0]["name"], "conductor")

    def test_track_summaries_empty_track(self):
        summaries = track_summaries(self.midi, self.notes)
        self.assertIsNone(summaries[0]["pitch_low"])

    def test_progression_collapses(self):
        notes = [note(p, 0, 960) for p in (60, 64, 67)]
        prog = chord_progression(notes, grid=480)
        self.assertEqual(len(prog), 1)
        self.assertEqual(prog[0]["chord"], "Cmaj")

    def test_progression_invalid_grid(self):
        with self.assertRaises(ValueError):
            chord_progression([note(60, 0, 100)], grid=0)

    def test_progression_empty(self):
        self.assertEqual(chord_progression([]), [])


if __name__ == "__main__":
    unittest.main()
