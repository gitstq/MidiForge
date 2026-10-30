"""变换模块测试。"""

from __future__ import annotations

import unittest

from midiforge.builder import demo_song
from midiforge.events import ChannelEvent, MetaEvent, SysExEvent
from midiforge.gm import DRUM_CHANNEL
from midiforge.midifile import MidiFile, Track
from midiforge.notes import extract_notes
from midiforge.reader import parse
from midiforge.tempo import TempoMap
from midiforge.transform import (
    clean,
    humanize,
    merge_tracks,
    quantize,
    remove_duplicate_notes,
    scale_tempo,
    scale_ticks,
    set_bpm,
    split_by_channel,
    strip,
    to_format,
    transpose,
    trim,
    velocity,
)
from midiforge.writer import serialize

from .helpers import simple_midi


class TestTranspose(unittest.TestCase):
    def test_up(self):
        midi = simple_midi([(60, 0, 100, 90)])
        self.assertEqual(
            [n.pitch for n in extract_notes(transpose(midi, 2))], [62]
        )

    def test_down(self):
        midi = simple_midi([(60, 0, 100, 90)])
        self.assertEqual([n.pitch for n in extract_notes(transpose(midi, -12))], [48])

    def test_original_unchanged(self):
        midi = simple_midi([(60, 0, 100, 90)])
        transpose(midi, 5)
        self.assertEqual([n.pitch for n in extract_notes(midi)], [60])

    def test_inplace(self):
        midi = simple_midi([(60, 0, 100, 90)])
        transpose(midi, 5, inplace=True)
        self.assertEqual([n.pitch for n in extract_notes(midi)], [65])

    def test_out_of_range_raises(self):
        from midiforge.errors import MidiValueError

        midi = simple_midi([(126, 0, 100, 90)])
        with self.assertRaises(MidiValueError):
            transpose(midi, 5)

    def test_channel_filter(self):
        midi = MidiFile(format=1, division=480, tracks=[])
        track = Track()
        track.add(ChannelEvent(tick=0, channel=0, etype=0x9, data1=60, data2=90))
        track.add(ChannelEvent(tick=100, channel=0, etype=0x8, data1=60, data2=0))
        track.add(ChannelEvent(tick=0, channel=1, etype=0x9, data1=60, data2=90))
        track.add(ChannelEvent(tick=100, channel=1, etype=0x8, data1=60, data2=0))
        midi.tracks.append(track)
        out = transpose(midi, 2, channels=[0])
        pitches = sorted(n.pitch for n in extract_notes(out))
        self.assertEqual(pitches, [60, 62])

    def test_drums_skipped_by_default(self):
        midi = simple_midi([(36, 0, 100, 90)])
        midi.tracks[0].events[1].channel = DRUM_CHANNEL
        midi.tracks[0].events[2].channel = DRUM_CHANNEL
        out = transpose(midi, 3)
        self.assertEqual([n.pitch for n in extract_notes(out)], [36])

    def test_drums_included_when_asked(self):
        midi = MidiFile(format=1, division=480, tracks=[])
        track = Track()
        track.add(ChannelEvent(tick=0, channel=DRUM_CHANNEL, etype=0x9, data1=36, data2=90))
        track.add(ChannelEvent(tick=100, channel=DRUM_CHANNEL, etype=0x8, data1=36, data2=0))
        midi.tracks.append(track)
        out = transpose(midi, 3, include_drums=True)
        self.assertEqual([n.pitch for n in extract_notes(out)], [39])


class TestQuantize(unittest.TestCase):
    def test_snap_to_grid(self):
        # 130 距离 240 更近（110）而距离 0 更远（130），因此吸附到 240
        midi = simple_midi([(60, 130, 100, 90)])
        out = quantize(midi, 240, strength=1.0)
        self.assertEqual([n.start for n in extract_notes(out)], [240])

    def test_snap_down_to_zero(self):
        midi = simple_midi([(60, 100, 100, 90)])
        out = quantize(midi, 240, strength=1.0)
        self.assertEqual([n.start for n in extract_notes(out)], [0])

    def test_duration_preserved(self):
        midi = simple_midi([(60, 130, 100, 90)])
        out = quantize(midi, 240, strength=1.0)
        self.assertEqual([n.duration for n in extract_notes(out)], [100])

    def test_strength_zero_keeps_position(self):
        midi = simple_midi([(60, 130, 100, 90)])
        out = quantize(midi, 240, strength=0.0)
        self.assertEqual([n.start for n in extract_notes(out)], [130])

    def test_swing_delays_offbeat(self):
        midi = simple_midi([(60, 240, 100, 90)])
        out = quantize(midi, 240, strength=1.0, swing=0.25)
        self.assertEqual([n.start for n in extract_notes(out)], [300])

    def test_invalid_grid_raises(self):
        from midiforge.errors import MidiValueError

        with self.assertRaises(MidiValueError):
            quantize(simple_midi(), 0)

    def test_invalid_strength_raises(self):
        from midiforge.errors import MidiValueError

        with self.assertRaises(MidiValueError):
            quantize(simple_midi(), 240, strength=1.5)

    def test_invalid_swing_raises(self):
        from midiforge.errors import MidiValueError

        with self.assertRaises(MidiValueError):
            quantize(simple_midi(), 240, swing=0.9)

    def test_channel_filter(self):
        midi = simple_midi([(60, 130, 100, 90)])
        out = quantize(midi, 240, channels=[1])
        self.assertEqual([n.start for n in extract_notes(out)], [130])


class TestVelocity(unittest.TestCase):
    def test_scale(self):
        midi = simple_midi([(60, 0, 100, 100)])
        out = velocity(midi, scale=0.5)
        self.assertEqual([n.velocity for n in extract_notes(out)], [50])

    def test_offset(self):
        midi = simple_midi([(60, 0, 100, 100)])
        out = velocity(midi, offset=10)
        self.assertEqual([n.velocity for n in extract_notes(out)], [110])

    def test_compression(self):
        midi = simple_midi([(60, 0, 100, 127)])
        out = velocity(midi, ratio=2.0)
        self.assertEqual([n.velocity for n in extract_notes(out)], [96])

    def test_clamped_high(self):
        midi = simple_midi([(60, 0, 100, 127)])
        out = velocity(midi, offset=100)
        self.assertEqual([n.velocity for n in extract_notes(out)], [127])

    def test_clamped_low(self):
        midi = simple_midi([(60, 0, 100, 10)])
        out = velocity(midi, offset=-100)
        note_ons = [e for e in out.tracks[0].events if getattr(e, "etype", None) == 0x9]
        self.assertEqual(note_ons[0].data2, 0)

    def test_invalid_ratio_raises(self):
        from midiforge.errors import MidiValueError

        with self.assertRaises(MidiValueError):
            velocity(simple_midi(), ratio=0)

    def test_note_off_not_modified(self):
        midi = simple_midi([(60, 0, 100, 90)])
        out = velocity(midi, offset=20)
        offs = [e for e in out.tracks[0].events if getattr(e, "etype", None) == 0x8]
        self.assertTrue(all(e.data2 == 0 for e in offs))


class TestHumanize(unittest.TestCase):
    def test_deterministic_with_seed(self):
        midi = simple_midi([(60, 0, 100, 90), (62, 200, 100, 90)])
        a = humanize(midi, tick_jitter=20, velocity_jitter=10, seed=42)
        b = humanize(midi, tick_jitter=20, velocity_jitter=10, seed=42)
        self.assertEqual(
            [n.start for n in extract_notes(a)], [n.start for n in extract_notes(b)]
        )

    def test_seed_changes_result(self):
        midi = simple_midi([(60, 0, 100, 90), (62, 200, 100, 90),
                            (64, 400, 100, 90), (65, 600, 100, 90)])
        a = humanize(midi, tick_jitter=50, seed=1)
        b = humanize(midi, tick_jitter=50, seed=2)
        self.assertNotEqual(
            [n.start for n in extract_notes(a)], [n.start for n in extract_notes(b)]
        )

    def test_no_jitter_keeps_values(self):
        midi = simple_midi([(60, 100, 100, 90)])
        out = humanize(midi, tick_jitter=0, velocity_jitter=0)
        self.assertEqual([n.start for n in extract_notes(out)], [100])

    def test_tick_never_negative(self):
        midi = simple_midi([(60, 5, 100, 90)])
        out = humanize(midi, tick_jitter=50, seed=7)
        self.assertGreaterEqual(min(n.start for n in extract_notes(out)), 0)


class TestTime(unittest.TestCase):
    def test_scale_ticks(self):
        midi = simple_midi([(60, 100, 100, 90)])
        out = scale_ticks(midi, 2.0)
        self.assertEqual([n.start for n in extract_notes(out)], [200])

    def test_scale_ticks_invalid(self):
        from midiforge.errors import MidiValueError

        with self.assertRaises(MidiValueError):
            scale_ticks(simple_midi(), 0)

    def test_scale_tempo_faster(self):
        midi = simple_midi([], bpm=120)
        out = scale_tempo(midi, 2.0)
        self.assertAlmostEqual(TempoMap.from_midi(out).initial_bpm, 240.0, places=1)

    def test_scale_tempo_inserts_when_missing(self):
        midi = MidiFile(format=1, division=480, tracks=[Track()])
        out = scale_tempo(midi, 2.0)
        self.assertEqual(len(out.tempo_events()), 1)

    def test_scale_tempo_invalid(self):
        from midiforge.errors import MidiValueError

        with self.assertRaises(MidiValueError):
            scale_tempo(simple_midi(), -1)

    def test_set_bpm(self):
        midi = simple_midi([], bpm=120)
        out = set_bpm(midi, 90)
        self.assertEqual(len(out.tempo_events()), 1)
        self.assertAlmostEqual(out.tempo_events()[0].bpm, 90.0, places=2)

    def test_set_bpm_invalid(self):
        from midiforge.errors import MidiValueError

        with self.assertRaises(MidiValueError):
            set_bpm(simple_midi(), 0)

    def test_trim_shift(self):
        midi = simple_midi([(60, 500, 100, 90)])
        out = trim(midi, start=400)
        self.assertEqual([n.start for n in extract_notes(out)], [100])

    def test_trim_closes_open_notes(self):
        midi = simple_midi([(60, 0, 1000, 90)])
        out = trim(midi, start=0, end=500)
        notes = extract_notes(out)
        self.assertEqual(notes[0].end, 500)

    def test_trim_keeps_tempo(self):
        midi = simple_midi([(60, 0, 100, 90)], bpm=100)
        out = trim(midi, start=90)
        self.assertEqual(len(out.tempo_events()), 1)
        self.assertEqual(out.tempo_events()[0].tick, 0)

    def test_trim_beyond_end_raises(self):
        from midiforge.errors import MidiValueError

        with self.assertRaises(MidiValueError):
            trim(simple_midi(), start=99999)

    def test_trim_invalid_range(self):
        from midiforge.errors import MidiValueError

        with self.assertRaises(MidiValueError):
            trim(simple_midi(), start=500, end=100)


class TestStructure(unittest.TestCase):
    def test_merge_tracks(self):
        midi = demo_song(bars=1)
        out = merge_tracks(midi)
        self.assertEqual(len(out.tracks), 1)

    def test_merge_keeps_notes(self):
        midi = demo_song(bars=1)
        before = len(extract_notes(midi))
        self.assertEqual(len(extract_notes(merge_tracks(midi))), before)

    def test_split_by_channel(self):
        midi = demo_song(bars=1)
        out = split_by_channel(midi)
        self.assertGreater(len(out.tracks), 1)

    def test_split_format_becomes_1(self):
        midi = demo_song(bars=1)
        midi.format = 0
        self.assertEqual(split_by_channel(midi).format, 1)

    def test_split_no_channel_events(self):
        midi = MidiFile(format=1, division=480, tracks=[Track()])
        self.assertEqual(len(split_by_channel(midi).tracks), 1)

    def test_to_format_zero_merges(self):
        midi = demo_song(bars=1)
        self.assertEqual(len(to_format(midi, 0).tracks), 1)

    def test_to_format_invalid(self):
        from midiforge.errors import MidiValueError

        with self.assertRaises(MidiValueError):
            to_format(simple_midi(), 3)

    def test_to_format_one(self):
        self.assertEqual(to_format(simple_midi(), 1).format, 1)


class TestStripAndClean(unittest.TestCase):
    def test_strip_sysex(self):
        midi = MidiFile(format=1, division=480, tracks=[Track()])
        midi.tracks[0].add(SysExEvent(tick=0, data=b"\x7E"))
        self.assertEqual(len(strip(midi, sysex=True).tracks[0].events), 0)

    def test_strip_controllers_keeps_list(self):
        midi = MidiFile(format=1, division=480, tracks=[Track()])
        midi.tracks[0].add(ChannelEvent(tick=0, channel=0, etype=0xB, data1=7, data2=100))
        midi.tracks[0].add(ChannelEvent(tick=0, channel=0, etype=0xB, data1=64, data2=127))
        out = strip(midi, controllers=True, keep_controllers=[64])
        left = [e.data1 for e in out.tracks[0].events if getattr(e, "etype", None) == 0xB]
        self.assertEqual(left, [64])

    def test_strip_program_change(self):
        midi = MidiFile(format=1, division=480, tracks=[Track()])
        midi.tracks[0].add(ChannelEvent(tick=0, channel=0, etype=0xC, data1=1, data2=0))
        self.assertEqual(len(strip(midi, program_change=True).tracks[0].events), 0)

    def test_strip_pitch_bend(self):
        midi = MidiFile(format=1, division=480, tracks=[Track()])
        midi.tracks[0].add(ChannelEvent(tick=0, channel=0, etype=0xE, data1=0, data2=64))
        self.assertEqual(len(strip(midi, pitch_bend=True).tracks[0].events), 0)

    def test_strip_aftertouch(self):
        midi = MidiFile(format=1, division=480, tracks=[Track()])
        midi.tracks[0].add(ChannelEvent(tick=0, channel=0, etype=0xD, data1=10, data2=0))
        self.assertEqual(len(strip(midi, aftertouch=True).tracks[0].events), 0)

    def test_strip_lyrics(self):
        midi = MidiFile(format=1, division=480, tracks=[Track()])
        midi.tracks[0].add(MetaEvent(tick=0, mtype=0x05, data=b"la"))
        self.assertEqual(len(strip(midi, lyrics=True).tracks[0].events), 0)

    def test_strip_markers(self):
        midi = MidiFile(format=1, division=480, tracks=[Track()])
        midi.tracks[0].add(MetaEvent(tick=0, mtype=0x06, data=b"verse"))
        self.assertEqual(len(strip(midi, markers=True).tracks[0].events), 0)

    def test_clean_removes_orphan_off(self):
        midi = MidiFile(format=1, division=480, tracks=[Track()])
        midi.tracks[0].add(ChannelEvent(tick=0, channel=0, etype=0x8, data1=60, data2=0))
        out = clean(midi)
        # 孤立 note_off 被丢弃，轨道仅保留补齐的 end_of_track
        self.assertEqual(
            len([e for e in out.tracks[0].events if e.kind == "channel"]), 0
        )
        self.assertTrue(out.tracks[0].has_end_of_track)

    def test_clean_closes_unterminated(self):
        midi = MidiFile(format=1, division=480, tracks=[Track()])
        midi.tracks[0].add(ChannelEvent(tick=0, channel=0, etype=0x9, data1=60, data2=90))
        out = clean(midi)
        self.assertEqual(len(extract_notes(out)), 1)
        self.assertFalse(extract_notes(out)[0].unterminated)

    def test_clean_converts_zero_velocity_on(self):
        midi = MidiFile(format=1, division=480, tracks=[Track()])
        midi.tracks[0].add(ChannelEvent(tick=0, channel=0, etype=0x9, data1=60, data2=90))
        midi.tracks[0].add(ChannelEvent(tick=100, channel=0, etype=0x9, data1=60, data2=0))
        out = clean(midi)
        note_events = [e for e in out.tracks[0].events if getattr(e, "etype", None) in (0x8, 0x9)]
        self.assertEqual(note_events[-1].etype, 0x8)
        self.assertEqual(len(extract_notes(out)), 1)

    def test_clean_adds_end_of_track(self):
        midi = MidiFile(format=1, division=480, tracks=[Track()])
        midi.tracks[0].add(ChannelEvent(tick=0, channel=0, etype=0x9, data1=60, data2=90))
        self.assertTrue(clean(midi).tracks[0].has_end_of_track())

    def test_clean_dedupe_end_of_track(self):
        midi = MidiFile(format=1, division=480, tracks=[Track()])
        midi.tracks[0].add(MetaEvent(tick=0, mtype=0x2F, data=b""))
        midi.tracks[0].add(MetaEvent(tick=0, mtype=0x2F, data=b""))
        count = len([e for e in clean(midi).tracks[0].events
                     if isinstance(e, MetaEvent) and e.mtype == 0x2F])
        self.assertEqual(count, 1)

    def test_remove_duplicate_notes(self):
        midi = MidiFile(format=1, division=480, tracks=[Track()])
        for _ in range(2):
            midi.tracks[0].add(ChannelEvent(tick=0, channel=0, etype=0x9, data1=60, data2=90))
            midi.tracks[0].add(ChannelEvent(tick=100, channel=0, etype=0x8, data1=60, data2=0))
        out = remove_duplicate_notes(midi)
        self.assertEqual(len(extract_notes(out)), 1)

    def test_output_is_serializable(self):
        out = clean(demo_song(bars=1))
        self.assertEqual(len(parse(serialize(out)).tracks), len(out.tracks))


if __name__ == "__main__":
    unittest.main()
