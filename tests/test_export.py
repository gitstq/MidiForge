"""导出与 diff 测试。"""

from __future__ import annotations

import json
import unittest

from midiforge.builder import demo_song, from_notes
from midiforge.diff import diff_midi, diff_notes, format_diff
from midiforge.export import (
    CSV_HEADER,
    midi_to_json,
    notes_to_csv,
    notes_to_json,
    notes_to_markdown,
    piano_roll,
    write_text,
)
from midiforge.notes import Note, extract_notes
from midiforge.tempo import TempoMap

from .helpers import tmp_path


class TestExport(unittest.TestCase):
    def setUp(self):
        self.midi = demo_song(bars=2)
        self.tempo_map = TempoMap.from_midi(self.midi)
        self.notes = extract_notes(self.midi, tempo_map=self.tempo_map)

    def test_csv_header(self):
        csv_text = notes_to_csv(self.notes)
        self.assertTrue(csv_text.startswith(",".join(CSV_HEADER)))

    def test_csv_row_count(self):
        csv_text = notes_to_csv(self.notes)
        self.assertEqual(len(csv_text.strip().split("\n")), len(self.notes) + 1)

    def test_csv_empty(self):
        self.assertTrue(notes_to_csv([]).startswith("track"))

    def test_json_parses(self):
        data = json.loads(notes_to_json(self.notes))
        self.assertEqual(len(data), len(self.notes))

    def test_json_fields(self):
        data = json.loads(notes_to_json(self.notes))
        self.assertIn("start_sec", data[0])

    def test_json_compact(self):
        self.assertNotIn("\n", notes_to_json(self.notes[:1], indent=None))

    def test_markdown_table(self):
        md = notes_to_markdown(self.notes, limit=5)
        self.assertIn("| # |", md)
        self.assertIn("仅列出前 5 个", md)

    def test_markdown_limit(self):
        import re

        md = notes_to_markdown(self.notes, limit=2)
        rows = [l for l in md.split("\n") if re.match(r"^\| \d+ \|", l)]
        self.assertEqual(len(rows), 2)

    def test_piano_roll_contains_bars(self):
        roll = piano_roll(self.notes, width=40, max_rows=8)
        self.assertIn("█", roll)

    def test_piano_roll_rows_respected(self):
        roll = piano_roll(self.notes, width=40, max_rows=5)
        body = [l for l in roll.split("\n") if "│" in l]
        self.assertLessEqual(len(body), 5)

    def test_piano_roll_empty(self):
        self.assertIn("没有音符", piano_roll([]))

    def test_piano_roll_narrow_range(self):
        notes = [Note(0, 0, 60, 90, 0, 100), Note(0, 0, 62, 90, 0, 100)]
        self.assertIn("C4", piano_roll(notes, width=20))

    def test_midi_json_structure(self):
        payload = json.loads(midi_to_json(self.midi))
        for key in ("summary", "tempo_map", "tracks", "notes"):
            self.assertIn(key, payload)

    def test_midi_json_default_args(self):
        payload = json.loads(midi_to_json(self.midi))
        self.assertEqual(payload["summary"]["tracks"], len(self.midi.tracks))

    def test_write_text(self):
        path = tmp_path("out.csv")
        write_text(path, "a,b\n1,2\n")
        with open(path, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "a,b\n1,2\n")


class TestDiff(unittest.TestCase):
    def setUp(self):
        self.base = from_notes([(60, 0, 240, 90), (62, 240, 240, 90)])

    def test_identical(self):
        result = diff_midi(self.base, self.base)
        self.assertEqual(result["similarity"], 1.0)
        self.assertEqual(result["counts"]["unchanged"], 2)

    def test_added_note(self):
        other = from_notes([(60, 0, 240, 90), (62, 240, 240, 90), (64, 480, 240, 90)])
        result = diff_midi(self.base, other)
        self.assertEqual(result["counts"]["added"], 1)

    def test_removed_note(self):
        other = from_notes([(60, 0, 240, 90)])
        result = diff_midi(self.base, other)
        self.assertEqual(result["counts"]["removed"], 1)

    def test_modified_velocity(self):
        other = from_notes([(60, 0, 240, 40), (62, 240, 240, 90)])
        result = diff_midi(self.base, other)
        self.assertEqual(result["counts"]["modified"], 1)

    def test_tolerance_matches(self):
        a = from_notes([(60, 0, 240, 90)])
        b = from_notes([(60, 8, 240, 90)])
        self.assertEqual(diff_midi(a, b, tolerance=0)["counts"]["added"], 1)
        self.assertEqual(diff_midi(a, b, tolerance=16)["counts"]["unchanged"], 1)

    def test_empty_similarity(self):
        self.assertEqual(diff_notes([], [])["similarity"], 1.0)

    def test_metadata_sections(self):
        result = diff_midi(self.base, self.base)
        self.assertIn("before", result)
        self.assertIn("after", result)

    def test_format_diff_text(self):
        other = from_notes([(60, 0, 240, 90)])
        text = format_diff(diff_midi(self.base, other))
        self.assertIn("相似度", text)
        self.assertIn("删除", text)

    def test_format_diff_truncates(self):
        notes = [(60 + i % 12, i * 100, 100, 90) for i in range(60)]
        text = format_diff(diff_midi(from_notes([]), from_notes(notes)), limit=3)
        self.assertIn("已省略", text)

    def test_track_change_detected(self):
        a = from_notes([(60, 0, 240, 90)])
        b = from_notes([(60, 0, 240, 90)])
        b.tracks.append(b.tracks[0])
        result = diff_midi(a, b)
        self.assertEqual(result["counts"]["unchanged"], 1)


if __name__ == "__main__":
    unittest.main()
