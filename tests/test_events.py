"""事件模型测试。"""

from __future__ import annotations

import unittest

from midiforge.events import (
    CHANNEL_TYPE_NAMES,
    CONTROL_CHANGE,
    META_TEMPO,
    NOTE_OFF,
    NOTE_ON,
    PITCH_BEND,
    ChannelEvent,
    MetaEvent,
    SysExEvent,
    bpm_to_tempo_bytes,
    decode_text,
    make_tempo,
)


class TestChannelEvent(unittest.TestCase):
    def test_status_byte(self):
        ev = ChannelEvent(tick=0, channel=3, etype=NOTE_ON, data1=60, data2=100)
        self.assertEqual(ev.status, 0x93)

    def test_type_name(self):
        ev = ChannelEvent(tick=0, channel=0, etype=CONTROL_CHANGE, data1=7, data2=100)
        self.assertEqual(ev.type_name, "control_change")

    def test_note_on_positive_velocity(self):
        ev = ChannelEvent(tick=0, channel=0, etype=NOTE_ON, data1=60, data2=64)
        self.assertTrue(ev.is_note_on)
        self.assertFalse(ev.is_note_off)

    def test_note_on_zero_velocity_is_off(self):
        ev = ChannelEvent(tick=0, channel=0, etype=NOTE_ON, data1=60, data2=0)
        self.assertFalse(ev.is_note_on)
        self.assertTrue(ev.is_note_off)

    def test_note_off_flag(self):
        ev = ChannelEvent(tick=0, channel=0, etype=NOTE_OFF, data1=60, data2=0)
        self.assertTrue(ev.is_note_off)

    def test_pitch_and_velocity(self):
        ev = ChannelEvent(tick=0, channel=0, etype=NOTE_ON, data1=72, data2=99)
        self.assertEqual(ev.pitch, 72)
        self.assertEqual(ev.velocity, 99)

    def test_controller_name_known(self):
        ev = ChannelEvent(tick=0, channel=0, etype=CONTROL_CHANGE, data1=64, data2=127)
        self.assertEqual(ev.controller_name, "sustain")

    def test_controller_name_unknown(self):
        ev = ChannelEvent(tick=0, channel=0, etype=CONTROL_CHANGE, data1=99, data2=0)
        self.assertEqual(ev.controller_name, "cc99")

    def test_pitch_bend_center(self):
        ev = ChannelEvent(tick=0, channel=0, etype=PITCH_BEND, data1=0, data2=64)
        self.assertEqual(ev.pitch_bend, 0)

    def test_pitch_bend_max(self):
        ev = ChannelEvent(tick=0, channel=0, etype=PITCH_BEND, data1=0x7F, data2=0x7F)
        self.assertEqual(ev.pitch_bend, 8191)

    def test_invalid_etype_raises(self):
        with self.assertRaises(ValueError):
            ChannelEvent(tick=0, channel=0, etype=0xF, data1=0, data2=0)

    def test_invalid_channel_raises(self):
        with self.assertRaises(ValueError):
            ChannelEvent(tick=0, channel=16, etype=NOTE_ON, data1=1, data2=1)

    def test_invalid_data_raises(self):
        with self.assertRaises(ValueError):
            ChannelEvent(tick=0, channel=0, etype=NOTE_ON, data1=128, data2=1)

    def test_with_tick_keeps_immutability(self):
        ev = ChannelEvent(tick=10, channel=0, etype=NOTE_ON, data1=60, data2=64)
        moved = ev.with_tick(99)
        self.assertEqual(ev.tick, 10)
        self.assertEqual(moved.tick, 99)

    def test_to_dict_note(self):
        ev = ChannelEvent(tick=5, channel=1, etype=NOTE_ON, data1=60, data2=70)
        data = ev.to_dict()
        self.assertEqual(data["type"], "note_on")
        self.assertEqual(data["pitch"], 60)
        self.assertEqual(data["velocity"], 70)

    def test_to_dict_pitch_bend(self):
        ev = ChannelEvent(tick=0, channel=0, etype=PITCH_BEND, data1=0, data2=64)
        self.assertIn("pitch_bend", ev.to_dict())

    def test_str_contains_pitch(self):
        ev = ChannelEvent(tick=0, channel=0, etype=NOTE_ON, data1=60, data2=64)
        self.assertIn("note=60", str(ev))

    def test_all_types_named(self):
        for etype in range(0x8, 0xF):
            self.assertIn(etype, CHANNEL_TYPE_NAMES)


class TestMetaEvent(unittest.TestCase):
    def test_tempo_value(self):
        ev = MetaEvent(tick=0, mtype=META_TEMPO, data=b"\x07\xA1\x20")
        self.assertEqual(ev.tempo, 500000)

    def test_bpm(self):
        ev = MetaEvent(tick=0, mtype=META_TEMPO, data=b"\x07\xA1\x20")
        self.assertAlmostEqual(ev.bpm, 120.0, places=3)

    def test_tempo_wrong_type_raises(self):
        ev = MetaEvent(tick=0, mtype=0x01, data=b"\x07\xA1\x20")
        with self.assertRaises(ValueError):
            ev.tempo

    def test_text_decoding(self):
        ev = MetaEvent(tick=0, mtype=0x03, data="钢琴".encode("utf-8"))
        self.assertEqual(ev.text, "钢琴")

    def test_text_fallback_latin1(self):
        ev = MetaEvent(tick=0, mtype=0x03, data=b"\xff\xfe")
        self.assertEqual(len(ev.text), 2)

    def test_time_signature(self):
        ev = MetaEvent(tick=0, mtype=0x58, data=bytes([6, 3, 24, 8]))
        self.assertEqual(ev.time_signature[:2], (6, 8))

    def test_key_signature_negative(self):
        ev = MetaEvent(tick=0, mtype=0x59, data=bytes([0xFF, 0]))
        self.assertEqual(ev.key_signature, (-1, False))

    def test_make_tempo(self):
        ev = make_tempo(0, 90.0)
        self.assertAlmostEqual(ev.bpm, 90.0, places=2)

    def test_bpm_to_bytes_range(self):
        self.assertEqual(len(bpm_to_tempo_bytes(1_000_000)), 3)

    def test_invalid_mtype_raises(self):
        with self.assertRaises(ValueError):
            MetaEvent(tick=0, mtype=200, data=b"")

    def test_to_dict_track_name(self):
        ev = MetaEvent(tick=0, mtype=0x03, data=b"lead")
        self.assertEqual(ev.to_dict()["text"], "lead")

    def test_type_name_unknown(self):
        ev = MetaEvent(tick=0, mtype=0x77, data=b"")
        self.assertTrue(ev.type_name.startswith("meta_0x"))

    def test_decode_text_helper(self):
        self.assertEqual(decode_text(b"abc"), "abc")


class TestSysExEvent(unittest.TestCase):
    def test_to_dict(self):
        ev = SysExEvent(tick=10, stype=0xF0, data=b"\x7E\x7F")
        data = ev.to_dict()
        self.assertEqual(data["length"], 2)
        self.assertEqual(data["stype"], "0xF0")

    def test_kind(self):
        self.assertEqual(SysExEvent().kind, "sysex")

    def test_str(self):
        self.assertIn("sysex", str(SysExEvent(tick=1, data=b"\x00")))


if __name__ == "__main__":
    unittest.main()
