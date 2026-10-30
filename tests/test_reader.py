"""解析器测试：块结构、running status、SysEx、SMPTE 与错误处理。"""

from __future__ import annotations

import unittest

from midiforge.errors import MidiParseError
from midiforge.events import ChannelEvent, MetaEvent, SysExEvent
from midiforge.reader import parse, peek_header, read_file
from midiforge.writer import serialize

from .helpers import mthd, mtrk, write_temp


class TestHeader(unittest.TestCase):
    def test_peek_header(self):
        data = mthd(fmt=0, ntrks=2, division=96)
        self.assertEqual(peek_header(data + mtrk(b"\x00\xFF\x2F\x00")), (0, 2, 96))

    def test_peek_header_bad_magic(self):
        with self.assertRaises(MidiParseError):
            peek_header(b"XXXX" + b"\x00" * 20)

    def test_too_short_raises(self):
        with self.assertRaises(MidiParseError):
            parse(b"MThd")

    def test_bad_magic_raises(self):
        with self.assertRaises(MidiParseError):
            parse(b"RIFF" + b"\x00" * 20)

    def test_short_header_length_raises(self):
        with self.assertRaises(MidiParseError):
            parse(b"MThd" + (3).to_bytes(4, "big") + b"\x00\x01\x02")

    def test_no_tracks_raises(self):
        with self.assertRaises(MidiParseError):
            parse(mthd(fmt=1, ntrks=0))

    def test_smpte_division(self):
        data = mthd(fmt=1, ntrks=1, division=0xE728) + mtrk(b"\x00\xFF\x2F\x00")
        midi = parse(data)
        self.assertTrue(midi.is_smpte)
        fps, tpf = midi.smpte
        self.assertEqual(fps, 25)
        self.assertEqual(tpf, 40)

    def test_unknown_chunk_is_skipped(self):
        data = (
            mthd(fmt=1, ntrks=1)
            + b"XFIH" + (2).to_bytes(4, "big") + b"\x01\x02"
            + mtrk(b"\x00\xFF\x2F\x00")
        )
        midi = parse(data)
        self.assertEqual(len(midi.tracks), 1)

    def test_declared_length_overflow_raises(self):
        data = mthd(fmt=1, ntrks=1) + b"MTrk" + (999).to_bytes(4, "big") + b"\x00"
        with self.assertRaises(MidiParseError):
            parse(data)


class TestTrackParsing(unittest.TestCase):
    def test_end_of_track(self):
        midi = parse(mthd() + mtrk(b"\x00\xFF\x2F\x00"))
        self.assertTrue(midi.tracks[0].has_end_of_track())

    def test_note_events(self):
        body = (
            b"\x00\x90\x3C\x40"
            b"\x60\x80\x3C\x00"
            b"\x00\xFF\x2F\x00"
        )
        midi = parse(mthd() + mtrk(body))
        events = midi.tracks[0].events
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].tick, 0)
        self.assertEqual(events[1].tick, 0x60)
        self.assertEqual(events[1].etype, 0x8)

    def test_running_status(self):
        body = b"\x00\x90\x3C\x40" b"\x00\x3E\x40" b"\x00\xFF\x2F\x00"
        midi = parse(mthd() + mtrk(body))
        events = [e for e in midi.tracks[0].events if isinstance(e, ChannelEvent)]
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].data1, 0x3C)
        self.assertEqual(events[1].data1, 0x3E)
        self.assertEqual(events[1].channel, 0)

    def test_data_byte_without_status_raises(self):
        with self.assertRaises(MidiParseError):
            parse(mthd() + mtrk(b"\x00\x3C\x40"))

    def test_program_change_one_data_byte(self):
        body = b"\x00\xC0\x19" b"\x00\xFF\x2F\x00"
        midi = parse(mthd() + mtrk(body))
        ev = midi.tracks[0].events[0]
        self.assertEqual(ev.etype, 0xC)
        self.assertEqual(ev.data1, 0x19)
        self.assertEqual(ev.data2, 0)

    def test_meta_payload(self):
        body = b"\x00\xFF\x03\x04lead" b"\x00\xFF\x2F\x00"
        midi = parse(mthd() + mtrk(body))
        self.assertEqual(midi.tracks[0].name, "lead")

    def test_sysex_event(self):
        body = b"\x00\xF0\x03\x7E\x7F\x09" b"\x00\xFF\x2F\x00"
        midi = parse(mthd() + mtrk(body))
        ev = midi.tracks[0].events[0]
        self.assertIsInstance(ev, SysExEvent)
        self.assertEqual(ev.data, b"\x7E\x7F\x09")

    def test_sysex_escape_f7(self):
        body = b"\x00\xF7\x02\x01\x02" b"\x00\xFF\x2F\x00"
        midi = parse(mthd() + mtrk(body))
        self.assertEqual(midi.tracks[0].events[0].stype, 0xF7)

    def test_truncated_meta_raises(self):
        with self.assertRaises(MidiParseError):
            parse(mthd() + mtrk(b"\x00\xFF\x03\x10ab"))

    def test_truncated_channel_event_raises(self):
        with self.assertRaises(MidiParseError):
            parse(mthd() + mtrk(b"\x00\x90\x3C"))

    def test_msb_data_byte_raises(self):
        with self.assertRaises(MidiParseError):
            parse(mthd() + mtrk(b"\x00\x90\xF0\x40"))

    def test_invalid_system_status_raises(self):
        with self.assertRaises(MidiParseError):
            parse(mthd() + mtrk(b"\x00\xF8\x00"))

    def test_multiple_tracks(self):
        data = mthd(fmt=1, ntrks=2) + mtrk(b"\x00\xFF\x2F\x00") + mtrk(b"\x00\xFF\x2F\x00")
        self.assertEqual(len(parse(data).tracks), 2)

    def test_read_file(self):
        from midiforge.builder import demo_song

        path = write_temp("read_file.mid", demo_song())
        midi = read_file(path)
        self.assertGreater(len(midi.tracks), 1)

    def test_roundtrip_demo(self):
        from midiforge.builder import demo_song

        midi = demo_song(bars=2)
        again = parse(serialize(midi))
        self.assertEqual(len(again.tracks), len(midi.tracks))
        self.assertEqual(
            sum(len(t.events) for t in again.tracks),
            sum(len(t.events) for t in midi.tracks),
        )

    def test_meta_event_types(self):
        body = b"\x00\xFF\x01\x03abc" b"\x00\xFF\x2F\x00"
        midi = parse(mthd() + mtrk(body))
        self.assertEqual(midi.tracks[0].events[0].text, "abc")

    def test_delta_accumulates(self):
        body = b"\x00\x90\x3C\x40" b"\x81\x00\x80\x3C\x00" b"\x00\xFF\x2F\x00"
        midi = parse(mthd() + mtrk(body))
        self.assertEqual(midi.tracks[0].events[1].tick, 128)


if __name__ == "__main__":
    unittest.main()
