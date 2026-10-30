"""校验（lint）测试。"""

from __future__ import annotations

import unittest

from midiforge.builder import demo_song
from midiforge.events import ChannelEvent, MetaEvent
from midiforge.midifile import MidiFile, Track
from midiforge.validate import ERROR, INFO, WARNING, Issue, is_healthy, summarize, validate

from .helpers import simple_midi


def one_track(events):
    midi = MidiFile(format=1, division=480, tracks=[])
    track = Track()
    for ev in events:
        track.add(ev)
    midi.tracks.append(track)
    return midi


class TestIssue(unittest.TestCase):
    def test_to_dict(self):
        issue = Issue("MF001", ERROR, "缺少 end", track=0, tick=5)
        data = issue.to_dict()
        self.assertEqual(data["code"], "MF001")
        self.assertEqual(data["track"], 0)

    def test_title_lookup(self):
        self.assertIn("end_of_track", Issue("MF001", ERROR, "").title)

    def test_str_contains_code(self):
        self.assertIn("MF001", str(Issue("MF001", ERROR, "x")))

    def test_unknown_code_title_empty(self):
        self.assertEqual(Issue("MF999", ERROR, "x").title, "")


class TestRuleDetection(unittest.TestCase):
    def test_missing_end_of_track(self):
        midi = one_track([ChannelEvent(tick=0, channel=0, etype=0x9, data1=60, data2=90)])
        codes = [i.code for i in validate(midi)]
        self.assertIn("MF001", codes)

    def test_orphan_note_off(self):
        midi = one_track([
            ChannelEvent(tick=0, channel=0, etype=0x8, data1=60, data2=0),
            MetaEvent(tick=0, mtype=0x2F, data=b""),
        ])
        self.assertIn("MF004", [i.code for i in validate(midi)])

    def test_unterminated_note_on(self):
        midi = one_track([
            ChannelEvent(tick=0, channel=0, etype=0x9, data1=60, data2=90),
            MetaEvent(tick=100, mtype=0x2F, data=b""),
        ])
        self.assertIn("MF005", [i.code for i in validate(midi)])

    def test_zero_length_note(self):
        midi = one_track([
            ChannelEvent(tick=0, channel=0, etype=0x9, data1=60, data2=90),
            ChannelEvent(tick=0, channel=0, etype=0x8, data1=60, data2=0),
            MetaEvent(tick=0, mtype=0x2F, data=b""),
        ])
        self.assertIn("MF006", [i.code for i in validate(midi)])

    def test_zero_velocity_note_on(self):
        midi = one_track([
            ChannelEvent(tick=0, channel=0, etype=0x9, data1=60, data2=0),
            MetaEvent(tick=0, mtype=0x2F, data=b""),
        ])
        self.assertIn("MF007", [i.code for i in validate(midi)])

    def test_overlapping_note(self):
        midi = one_track([
            ChannelEvent(tick=0, channel=0, etype=0x9, data1=60, data2=90),
            ChannelEvent(tick=10, channel=0, etype=0x9, data1=60, data2=90),
            ChannelEvent(tick=20, channel=0, etype=0x8, data1=60, data2=0),
            ChannelEvent(tick=30, channel=0, etype=0x8, data1=60, data2=0),
            MetaEvent(tick=30, mtype=0x2F, data=b""),
        ])
        self.assertIn("MF008", [i.code for i in validate(midi)])

    def test_missing_tempo(self):
        midi = one_track([MetaEvent(tick=0, mtype=0x2F, data=b"")])
        self.assertIn("MF009", [i.code for i in validate(midi)])

    def test_missing_time_signature_is_info(self):
        midi = one_track([MetaEvent(tick=0, mtype=0x2F, data=b"")])
        codes = [i.code for i in validate(midi, strict=True)]
        self.assertIn("MF011", codes)

    def test_info_hidden_without_strict(self):
        midi = one_track([MetaEvent(tick=0, mtype=0x2F, data=b"")])
        codes = [i.code for i in validate(midi)]
        self.assertNotIn("MF011", codes)

    def test_events_after_end_of_track(self):
        midi = one_track([
            MetaEvent(tick=0, mtype=0x2F, data=b""),
            MetaEvent(tick=50, mtype=0x01, data=b"late"),
        ])
        self.assertIn("MF012", [i.code for i in validate(midi)])

    def test_duplicate_end_of_track(self):
        midi = one_track([
            MetaEvent(tick=0, mtype=0x2F, data=b""),
            MetaEvent(tick=10, mtype=0x2F, data=b""),
        ])
        self.assertIn("MF013", [i.code for i in validate(midi)])

    def test_tempo_in_non_first_track(self):
        midi = simple_midi(bpm=120)
        midi.tracks.append(Track())
        midi.tracks[1].add(MetaEvent(tick=0, mtype=0x51, data=b"\x07\xA1\x20"))
        self.assertIn("MF014", [i.code for i in validate(midi)])

    def test_no_notes_warning(self):
        midi = one_track([MetaEvent(tick=0, mtype=0x51, data=b"\x07\xA1\x20")])
        self.assertIn("MF015", [i.code for i in validate(midi)])

    def test_bad_tempo_payload(self):
        midi = one_track([MetaEvent(tick=0, mtype=0x51, data=b"\x01\x02")])
        self.assertIn("MF010", [i.code for i in validate(midi)])

    def test_extreme_tempo(self):
        midi = one_track([MetaEvent(tick=0, mtype=0x51, data=b"\x00\x00\x01")])
        self.assertIn("MF010", [i.code for i in validate(midi)])

    def test_unknown_meta_type(self):
        midi = one_track([MetaEvent(tick=0, mtype=0x77, data=b"x")])
        self.assertIn("MF020", [i.code for i in validate(midi, strict=True)])

    def test_empty_track(self):
        midi = MidiFile(format=1, division=480, tracks=[Track()])
        self.assertIn("MF003", [i.code for i in validate(midi)])

    def test_bad_format(self):
        midi = simple_midi()
        midi.format = 7
        self.assertIn("MF017", [i.code for i in validate(midi)])

    def test_zero_division(self):
        midi = simple_midi()
        midi.division = 0
        self.assertIn("MF019", [i.code for i in validate(midi)])

    def test_track_name_info(self):
        midi = MidiFile(format=1, division=480, tracks=[Track()])
        midi.tracks[0].add(MetaEvent(tick=0, mtype=0x2F, data=b""))
        self.assertIn("MF002", [i.code for i in validate(midi, strict=True)])


class TestSummary(unittest.TestCase):
    def test_demo_song_is_clean(self):
        self.assertEqual([i for i in validate(demo_song()) if i.level == ERROR], [])

    def test_is_healthy(self):
        self.assertTrue(is_healthy(demo_song()))

    def test_is_unhealthy(self):
        midi = one_track([ChannelEvent(tick=0, channel=0, etype=0x9, data1=60, data2=90)])
        self.assertFalse(is_healthy(midi))

    def test_summarize_counts(self):
        issues = [Issue("MF001", ERROR, ""), Issue("MF009", WARNING, "")]
        summary = summarize(issues)
        self.assertEqual(summary["errors"], 1)
        self.assertEqual(summary["warnings"], 1)
        self.assertEqual(summary["total"], 2)

    def test_sorted_by_level(self):
        issues = validate(one_track([MetaEvent(tick=0, mtype=0x2F, data=b"")]), strict=True)
        levels = [i.level for i in issues]
        rank = {ERROR: 0, WARNING: 1, INFO: 2}
        self.assertEqual(levels, sorted(levels, key=lambda x: rank[x]))

    def test_no_tracks_shortcut(self):
        midi = MidiFile(format=1, division=480, tracks=[])
        self.assertTrue(any(i.code == "MF003" for i in validate(midi)))


if __name__ == "__main__":
    unittest.main()
