"""音符抽取测试。"""

from __future__ import annotations

import unittest

from midiforge.events import ChannelEvent
from midiforge.gm import DRUM_CHANNEL
from midiforge.midifile import MidiFile, Track
from midiforge.notes import (
    Note,
    extract_notes,
    max_polyphony,
    note_density,
    polyphony_profile,
)
from midiforge.tempo import TempoMap


def build(events, division=480, tracks=1):
    midi = MidiFile(format=1, division=division, tracks=[])
    track = Track()
    for ev in events:
        track.add(ev)
    track.sort()
    midi.tracks.append(track)
    for _ in range(tracks - 1):
        midi.tracks.append(Track())
    return midi


def note_on(tick, pitch=60, channel=0, vel=90):
    return ChannelEvent(tick=tick, channel=channel, etype=0x9, data1=pitch, data2=vel)


def note_off(tick, pitch=60, channel=0):
    return ChannelEvent(tick=tick, channel=channel, etype=0x8, data1=pitch, data2=0)


class TestExtraction(unittest.TestCase):
    def test_single_note(self):
        midi = build([note_on(0), note_off(240)])
        notes = extract_notes(midi)
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].duration, 240)

    def test_note_on_zero_velocity_closes(self):
        midi = build([note_on(0), ChannelEvent(tick=120, channel=0, etype=0x9, data1=60, data2=0)])
        notes = extract_notes(midi)
        self.assertEqual(notes[0].duration, 120)

    def test_unterminated_closed_at_track_end(self):
        midi = build([note_on(0), note_off(480)])
        notes = extract_notes(midi)
        self.assertFalse(notes[0].unterminated)

    def test_unterminated_flag(self):
        midi = build([note_on(0)])
        notes = extract_notes(midi)
        self.assertEqual(len(notes), 1)
        self.assertTrue(notes[0].unterminated)

    def test_unterminated_can_be_disabled(self):
        midi = build([note_on(0)])
        self.assertEqual(len(extract_notes(midi, close_unterminated=False)), 0)

    def test_orphan_note_off_ignored(self):
        midi = build([note_off(100)])
        self.assertEqual(len(extract_notes(midi)), 0)

    def test_fifo_pairing(self):
        midi = build([note_on(0), note_on(100), note_off(200), note_off(300)])
        notes = extract_notes(midi)
        self.assertEqual([n.start for n in notes], [0, 100])
        self.assertEqual([n.duration for n in notes], [200, 200])

    def test_sorted_by_start(self):
        midi = build([note_on(480, 64), note_off(600, 64), note_on(0, 60), note_off(120, 60)])
        notes = extract_notes(midi)
        self.assertEqual([n.start for n in notes], [0, 480])

    def test_drum_excluded(self):
        midi = build([note_on(0, 36, DRUM_CHANNEL), note_off(120, 36, DRUM_CHANNEL)])
        self.assertEqual(len(extract_notes(midi, include_drums=False)), 0)

    def test_drum_included(self):
        midi = build([note_on(0, 36, DRUM_CHANNEL), note_off(120, 36, DRUM_CHANNEL)])
        self.assertEqual(len(extract_notes(midi)), 1)

    def test_is_drum_flag(self):
        midi = build([note_on(0, 36, DRUM_CHANNEL), note_off(120, 36, DRUM_CHANNEL)])
        self.assertTrue(extract_notes(midi)[0].is_drum)

    def test_channels_distinguished(self):
        midi = build([note_on(0, 60, 0), note_off(100, 60, 0),
                      note_on(0, 60, 1), note_off(100, 60, 1)])
        self.assertEqual(len(extract_notes(midi)), 2)

    def test_track_index_recorded(self):
        midi = build([note_on(0), note_off(100)], tracks=1)
        midi.tracks.append(Track())
        midi.tracks[1].add(note_on(0, 72))
        midi.tracks[1].add(note_off(200, 72))
        tracks = {n.track for n in extract_notes(midi)}
        self.assertEqual(tracks, {0, 1})

    def test_seconds_require_tempo_map(self):
        midi = build([note_on(0), note_off(480)])
        notes = extract_notes(midi, tempo_map=TempoMap.from_bpm(120, 480))
        self.assertAlmostEqual(notes[0].duration_sec, 0.5, places=6)

    def test_seconds_zero_without_map(self):
        midi = build([note_on(0), note_off(480)])
        self.assertEqual(extract_notes(midi)[0].duration_sec, 0.0)

    def test_label(self):
        midi = build([note_on(0, 60), note_off(100, 60)])
        self.assertEqual(extract_notes(midi)[0].label, "C4")

    def test_to_dict_keys(self):
        midi = build([note_on(0), note_off(100)])
        data = extract_notes(midi, tempo_map=TempoMap.from_bpm(120, 480))[0].to_dict()
        for key in ("pitch", "velocity", "start_tick", "duration_ticks", "start_sec"):
            self.assertIn(key, data)

    def test_str(self):
        midi = build([note_on(0), note_off(100)])
        self.assertIn("C4", str(extract_notes(midi)[0]))

    def test_negative_duration_clamped(self):
        midi = build([note_on(500, 60), note_off(100, 60)])
        # 解析时按顺序：note_off 出现在 note_on 之前 → 视为孤儿
        self.assertEqual(len(extract_notes(midi)), 1)
        self.assertEqual(extract_notes(midi)[0].duration, 0)


class TestPolyphony(unittest.TestCase):
    def test_chord_of_three(self):
        midi = build([
            note_on(0, 60), note_on(0, 64), note_on(0, 67),
            note_off(240, 60), note_off(240, 64), note_off(240, 67),
        ])
        self.assertEqual(max_polyphony(extract_notes(midi)), 3)

    def test_sequential_is_one(self):
        midi = build([note_on(0), note_off(100), note_on(100), note_off(200)])
        self.assertEqual(max_polyphony(extract_notes(midi)), 1)

    def test_empty(self):
        self.assertEqual(max_polyphony([]), 0)

    def test_profile_counts(self):
        notes = [
            Note(track=0, channel=0, pitch=60, velocity=90, start=0, end=100),
            Note(track=0, channel=0, pitch=64, velocity=90, start=0, end=100),
        ]
        self.assertEqual(polyphony_profile(notes).get(2), 1)

    def test_density_buckets(self):
        notes = [
            Note(track=0, channel=0, pitch=60, velocity=90, start=0, end=10),
            Note(track=0, channel=0, pitch=60, velocity=90, start=500, end=510),
        ]
        density = note_density(notes, 100, 600)
        self.assertEqual(density[0], 1)
        self.assertEqual(density[5], 1)

    def test_density_invalid_window(self):
        with self.assertRaises(ValueError):
            note_density([], 0, 100)


if __name__ == "__main__":
    unittest.main()
