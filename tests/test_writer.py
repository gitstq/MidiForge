"""序列化测试。"""

from __future__ import annotations

import unittest

from midiforge.events import MetaEvent
from midiforge.midifile import MidiFile, Track, new_midi
from midiforge.reader import parse
from midiforge.writer import serialize, write_file

from .helpers import tmp_path


class TestSerialize(unittest.TestCase):
    def test_magic_and_header(self):
        data = serialize(new_midi(tracks=1))
        self.assertEqual(data[:4], b"MThd")
        self.assertEqual(int.from_bytes(data[4:8], "big"), 6)

    def test_track_count_written(self):
        data = serialize(new_midi(tracks=3))
        self.assertEqual(int.from_bytes(data[10:12], "big"), 3)

    def test_mtrk_chunk_present(self):
        data = serialize(new_midi(tracks=1))
        self.assertIn(b"MTrk", data)

    def test_end_of_track_auto_added(self):
        midi = new_midi(tracks=1)
        again = parse(serialize(midi))
        self.assertTrue(again.tracks[0].has_end_of_track())

    def test_chunk_length_is_correct(self):
        midi = new_midi(tracks=1)
        data = serialize(midi)
        declared = int.from_bytes(data[18:22], "big")
        self.assertEqual(declared, len(data) - 22)

    def test_smpte_division_roundtrip(self):
        midi = new_midi(tracks=1)
        midi.division = -0x2728
        again = parse(serialize(midi))
        self.assertTrue(again.is_smpte)

    def test_running_status_compresses(self):
        midi = new_midi(tracks=1)
        for i in range(4):
            midi.tracks[0].add(
                MetaEvent(tick=0, mtype=0x01, data=b"x")
            )
        compressed = serialize(midi, use_running_status=True)
        plain = serialize(midi, use_running_status=False)
        self.assertLessEqual(len(compressed), len(plain))

    def test_running_status_preserves_channel(self):
        from midiforge.events import ChannelEvent

        midi = new_midi(tracks=1)
        for pitch in (60, 62, 64):
            midi.tracks[0].add(
                ChannelEvent(tick=pitch, channel=2, etype=0x9, data1=pitch, data2=90)
            )
        again = parse(serialize(midi))
        channels = {e.channel for e in again.tracks[0].events if hasattr(e, "channel")}
        self.assertEqual(channels, {2})

    def test_write_file_creates_bytes(self):
        midi = new_midi(tracks=1)
        path = tmp_path("writer.mid")
        write_file(midi, path)
        with open(path, "rb") as fh:
            self.assertGreater(len(fh.read()), 14)

    def test_events_sorted_on_write(self):
        from midiforge.events import ChannelEvent

        midi = new_midi(tracks=1)
        midi.tracks[0].add(ChannelEvent(tick=500, channel=0, etype=0x9, data1=60, data2=1))
        midi.tracks[0].add(ChannelEvent(tick=10, channel=0, etype=0x9, data1=61, data2=1))
        again = parse(serialize(midi))
        ticks = [e.tick for e in again.tracks[0].events]
        self.assertEqual(ticks, sorted(ticks))

    def test_program_change_single_data_byte(self):
        from midiforge.events import ChannelEvent

        midi = new_midi(tracks=1)
        midi.tracks[0].add(ChannelEvent(tick=0, channel=0, etype=0xC, data1=25, data2=0))
        again = parse(serialize(midi))
        ev = again.tracks[0].events[0]
        self.assertEqual(ev.etype, 0xC)
        self.assertEqual(ev.data1, 25)

    def test_sysex_roundtrip(self):
        from midiforge.events import SysExEvent

        midi = new_midi(tracks=1)
        midi.tracks[0].add(SysExEvent(tick=0, stype=0xF0, data=b"\x7E\x00"))
        again = parse(serialize(midi))
        self.assertEqual(again.tracks[0].events[0].data, b"\x7E\x00")

    def test_too_many_tracks_raises(self):
        from midiforge.errors import MidiWriteError

        midi = MidiFile(format=1, division=480, tracks=[])
        midi.tracks = [Track() for _ in range(65536)]
        with self.assertRaises(MidiWriteError):
            serialize(midi)


if __name__ == "__main__":
    unittest.main()
