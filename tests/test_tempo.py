"""速度映射与 tick / 秒换算测试。"""

from __future__ import annotations

import unittest

from midiforge.builder import demo_song
from midiforge.events import MetaEvent, bpm_to_tempo_bytes
from midiforge.midifile import MidiFile, Track
from midiforge.tempo import TempoChange, TempoMap, apply_tempo_changes


def midi_with_tempos(changes, division=480):
    midi = MidiFile(format=1, division=division, tracks=[])
    track = Track()
    for tick, bpm in changes:
        track.add(MetaEvent(tick=tick, mtype=0x51, data=bpm_to_tempo_bytes(bpm)))
    track.sort()
    midi.tracks.append(track)
    return midi


class TestTempoMapBasics(unittest.TestCase):
    def test_default_tempo_is_120(self):
        tm = TempoMap([], 480)
        self.assertAlmostEqual(tm.initial_bpm, 120.0, places=3)

    def test_from_bpm(self):
        tm = TempoMap.from_bpm(60, 480)
        self.assertAlmostEqual(tm.initial_bpm, 60.0, places=3)

    def test_bpm_at_tick_zero(self):
        tm = TempoMap([TempoChange(0, 500000), TempoChange(480, 250000)], 480)
        self.assertAlmostEqual(tm.bpm_at(0), 120.0, places=3)

    def test_bpm_at_later_tick(self):
        tm = TempoMap([TempoChange(0, 500000), TempoChange(480, 250000)], 480)
        self.assertAlmostEqual(tm.bpm_at(480), 240.0, places=3)

    def test_missing_zero_change_is_inserted(self):
        tm = TempoMap([TempoChange(480, 250000)], 480)
        self.assertEqual(tm.changes[0].tick, 0)

    def test_changes_sorted(self):
        tm = TempoMap([TempoChange(960, 250000), TempoChange(0, 500000)], 480)
        self.assertEqual([c.tick for c in tm.changes], [0, 960])

    def test_len(self):
        self.assertEqual(len(TempoMap([TempoChange(0, 500000)], 480)), 1)

    def test_repr(self):
        self.assertIn("TempoMap", repr(TempoMap([], 480)))


class TestConversions(unittest.TestCase):
    def test_one_beat_at_120bpm(self):
        tm = TempoMap.from_bpm(120, 480)
        self.assertAlmostEqual(tm.tick_to_seconds(480), 0.5, places=6)

    def test_zero_tick_is_zero_seconds(self):
        tm = TempoMap.from_bpm(120, 480)
        self.assertEqual(tm.tick_to_seconds(0), 0.0)

    def test_seconds_to_tick_roundtrip(self):
        tm = TempoMap.from_bpm(120, 480)
        self.assertEqual(tm.seconds_to_tick(tm.tick_to_seconds(1234)), 1234)

    def test_negative_seconds(self):
        tm = TempoMap.from_bpm(120, 480)
        self.assertEqual(tm.seconds_to_tick(-5), 0)

    def test_two_tempo_segments(self):
        tm = TempoMap([TempoChange(0, 500000), TempoChange(480, 250000)], 480)
        # 第一段 480 tick = 0.5s，第二段 480 tick = 0.25s
        self.assertAlmostEqual(tm.tick_to_seconds(480), 0.5, places=6)
        self.assertAlmostEqual(tm.tick_to_seconds(960), 0.75, places=6)

    def test_seconds_to_tick_across_segments(self):
        tm = TempoMap([TempoChange(0, 500000), TempoChange(480, 250000)], 480)
        self.assertEqual(tm.seconds_to_tick(0.75), 960)

    def test_beats_conversion(self):
        tm = TempoMap.from_bpm(120, 480)
        self.assertAlmostEqual(tm.tick_to_beats(960), 2.0, places=6)

    def test_beats_to_tick(self):
        tm = TempoMap.from_bpm(120, 480)
        self.assertEqual(tm.beats_to_tick(2.0), 960)

    def test_bars(self):
        tm = TempoMap.from_bpm(120, 480)
        self.assertAlmostEqual(tm.tick_to_bars(1920), 1.0, places=6)

    def test_mbt(self):
        tm = TempoMap.from_bpm(120, 480)
        self.assertEqual(tm.tick_to_mbt(480), (1, 2, 0))

    def test_mbt_bar_boundary(self):
        tm = TempoMap.from_bpm(120, 480)
        self.assertEqual(tm.tick_to_mbt(1920), (2, 1, 0))

    def test_smpte_mode(self):
        tm = TempoMap([], -0x2728, smpte=True, fps=25, ticks_per_frame=40)
        self.assertAlmostEqual(tm.tick_to_seconds(1000), 1.0, places=6)

    def test_smpte_seconds_to_tick(self):
        tm = TempoMap([], -0x2728, smpte=True, fps=25, ticks_per_frame=40)
        self.assertEqual(tm.seconds_to_tick(1.0), 1000)

    def test_smpte_bpm_fallback(self):
        tm = TempoMap([], -0x2728, smpte=True, fps=25, ticks_per_frame=40)
        self.assertAlmostEqual(tm.bpm_at(100), 120.0, places=3)

    def test_from_midi(self):
        tm = TempoMap.from_midi(midi_with_tempos([(0, 90), (960, 180)]))
        self.assertAlmostEqual(tm.initial_bpm, 90.0, places=2)

    def test_from_midi_smpte(self):
        midi = MidiFile(format=1, division=-0x2728, tracks=[Track()])
        tm = TempoMap.from_midi(midi)
        self.assertTrue(tm.smpte)

    def test_to_list(self):
        tm = TempoMap([TempoChange(0, 500000)], 480)
        self.assertEqual(tm.to_list()[0]["bpm"], 120.0)

    def test_tpq_smpte_fallback(self):
        tm = TempoMap([], -0x2728, smpte=True, fps=25, ticks_per_frame=40)
        self.assertEqual(tm.tpq, 480)

    def test_demo_duration(self):
        midi = demo_song(bpm=120, bars=1)
        tm = TempoMap.from_midi(midi)
        # 1 小节 4/4 @120BPM = 2 秒
        self.assertAlmostEqual(tm.tick_to_seconds(1920), 2.0, places=6)


class TestApplyTempoChanges(unittest.TestCase):
    def test_replaces_existing(self):
        midi = midi_with_tempos([(0, 120), (480, 140)])
        apply_tempo_changes(midi, [(0, 100)])
        self.assertEqual(len(midi.tempo_events()), 1)

    def test_new_bpm_value(self):
        midi = midi_with_tempos([(0, 120)])
        apply_tempo_changes(midi, [(0, 60)])
        self.assertAlmostEqual(midi.tempo_events()[0].bpm, 60.0, places=2)

    def test_sorted_output(self):
        midi = midi_with_tempos([(0, 120)])
        apply_tempo_changes(midi, [(480, 90), (0, 80)])
        self.assertEqual([e.tick for e in midi.tempo_events()], [0, 480])


if __name__ == "__main__":
    unittest.main()
