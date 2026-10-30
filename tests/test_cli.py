"""命令行端到端测试。"""

from __future__ import annotations

import contextlib
import io
import json
import os
import unittest

from midiforge.cli import build_parser, main
from midiforge.writer import write_file

from .helpers import tmp_path, write_temp


def run(*argv):
    """执行 CLI 并返回 ``(退出码, stdout, stderr)``。"""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class TestCLIBasics(unittest.TestCase):
    def test_no_command_prints_help(self):
        code, out, _ = run()
        self.assertEqual(code, 1)
        self.assertIn("usage", out.lower())

    def test_version_flag(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["--version"])

    def test_unknown_file_returns_2(self):
        code, _, err = run("info", "/nonexistent/nope.mid")
        self.assertEqual(code, 2)
        self.assertIn("错误", err)

    def test_parser_has_all_commands(self):
        text = build_parser().format_help()
        for cmd in ("info", "stats", "notes", "validate", "transpose", "quantize",
                    "trim", "merge", "split", "convert", "strip", "clean", "roll",
                    "diff", "demo", "velocity", "humanize", "tempo"):
            self.assertIn(cmd, text)


class TestInfoAndStats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from midiforge.builder import demo_song

        cls.path = write_temp("cli_demo.mid", demo_song(bars=2))

    def test_info_text(self):
        code, out, _ = run("info", self.path)
        self.assertEqual(code, 0)
        self.assertIn("MIDI 格式", out)

    def test_info_json(self):
        code, out, _ = run("info", self.path, "--json")
        self.assertEqual(code, 0)
        self.assertIn("ticks_per_quarter", json.loads(out))

    def test_stats_text(self):
        code, out, _ = run("stats", self.path)
        self.assertEqual(code, 0)
        self.assertIn("调性猜测", out)

    def test_stats_json(self):
        code, out, _ = run("stats", self.path, "--json")
        self.assertIn("rhythm_histogram", json.loads(out))

    def test_alias_analyze(self):
        code, _, _ = run("analyze", self.path)
        self.assertEqual(code, 0)

    def test_notes_text(self):
        code, out, _ = run("notes", self.path)
        self.assertIn("个音符", out)

    def test_notes_json(self):
        code, out, _ = run("notes", self.path, "--json", "--limit", "3")
        self.assertEqual(len(json.loads(out)), 3)

    def test_notes_csv_to_file(self):
        target = tmp_path("notes.csv")
        code, out, _ = run("notes", self.path, "--csv", "-o", target)
        self.assertEqual(code, 0)
        self.assertTrue(os.path.getsize(target) > 0)

    def test_notes_md(self):
        code, out, _ = run("notes", self.path, "--md")
        self.assertIn("| # |", out)

    def test_notes_no_drums(self):
        code, out, _ = run("notes", self.path, "--json", "--no-drums")
        self.assertTrue(all(not n["drum"] for n in json.loads(out)))

    def test_roll(self):
        code, out, _ = run("roll", self.path, "--width", "40", "--rows", "6")
        self.assertIn("█", out)

    def test_validate_clean_file(self):
        code, out, _ = run("validate", self.path)
        self.assertEqual(code, 0)

    def test_validate_json(self):
        code, out, _ = run("validate", self.path, "--json")
        self.assertIn("summary", json.loads(out))

    def test_validate_strict(self):
        code, _, _ = run("validate", self.path, "--strict")
        self.assertIn(code, (0, 1))

    def test_lint_alias(self):
        code, _, _ = run("lint", self.path)
        self.assertEqual(code, 0)


class TestTransformCommands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from midiforge.builder import demo_song

        cls.path = write_temp("cli_src.mid", demo_song(bars=2))

    def _out(self, name):
        return tmp_path(name)

    def test_transpose(self):
        target = self._out("t.mid")
        code, out, _ = run("transpose", self.path, "-s", "3", "-o", target)
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(target))

    def test_transpose_out_of_range(self):
        code, _, err = run("transpose", self.path, "-s", "100", "-o", self._out("x.mid"))
        self.assertEqual(code, 2)
        self.assertIn("错误", err)

    def test_quantize(self):
        target = self._out("q.mid")
        code, _, _ = run("quantize", self.path, "-g", "16", "--swing", "0.2", "-o", target)
        self.assertEqual(code, 0)

    def test_quantize_grid_fraction(self):
        code, _, _ = run("quantize", self.path, "-g", "1/8", "-o", self._out("q2.mid"))
        self.assertEqual(code, 0)

    def test_quantize_bad_grid(self):
        code, _, _ = run("quantize", self.path, "-g", "abc", "-o", self._out("q3.mid"))
        self.assertEqual(code, 2)

    def test_velocity(self):
        code, _, _ = run("velocity", self.path, "--scale", "0.8", "--offset", "5",
                         "-o", self._out("v.mid"))
        self.assertEqual(code, 0)

    def test_humanize(self):
        code, _, _ = run("humanize", self.path, "--seed", "7", "-o", self._out("h.mid"))
        self.assertEqual(code, 0)

    def test_tempo_set(self):
        code, _, _ = run("tempo", self.path, "--set", "140", "-o", self._out("bpm.mid"))
        self.assertEqual(code, 0)

    def test_tempo_scale(self):
        code, _, _ = run("tempo", self.path, "--scale", "1.5", "-o", self._out("bpm2.mid"))
        self.assertEqual(code, 0)

    def test_tempo_stretch(self):
        code, _, _ = run("tempo", self.path, "--stretch", "2", "-o", self._out("bpm3.mid"))
        self.assertEqual(code, 0)

    def test_tempo_requires_option(self):
        code, _, _ = run("tempo", self.path, "-o", self._out("bpm4.mid"))
        self.assertEqual(code, 2)

    def test_trim(self):
        code, _, _ = run("trim", self.path, "--start", "0", "--end", "960",
                         "-o", self._out("trim.mid"))
        self.assertEqual(code, 0)

    def test_merge(self):
        code, _, _ = run("merge", self.path, "-o", self._out("merge.mid"))
        self.assertEqual(code, 0)

    def test_split(self):
        code, _, _ = run("split", self.path, "-o", self._out("split.mid"))
        self.assertEqual(code, 0)

    def test_convert_format(self):
        code, _, _ = run("convert", self.path, "--format", "0", "-o", self._out("f0.mid"))
        self.assertEqual(code, 0)

    def test_convert_to_csv(self):
        code, _, _ = run("convert", self.path, "--to", "csv", "-o", self._out("c.csv"))
        self.assertEqual(code, 0)

    def test_convert_requires_target(self):
        code, _, _ = run("convert", self.path, "-o", self._out("none.mid"))
        self.assertEqual(code, 2)

    def test_strip(self):
        code, _, _ = run("strip", self.path, "--cc", "--keep-cc", "7,64",
                         "-o", self._out("s.mid"))
        self.assertEqual(code, 0)

    def test_clean(self):
        code, _, _ = run("clean", self.path, "--dedupe", "-o", self._out("cl.mid"))
        self.assertEqual(code, 0)

    def test_demo(self):
        target = self._out("demo.mid")
        code, out, _ = run("demo", "--bpm", "90", "--bars", "2", "-o", target)
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(target))

    def test_diff_same_file(self):
        code, out, _ = run("diff", self.path, self.path)
        self.assertEqual(code, 0)
        self.assertIn("100.0%", out)

    def test_diff_json(self):
        code, out, _ = run("diff", self.path, self.path, "--json")
        self.assertIn("similarity", json.loads(out))


class TestRoundTripThroughCLI(unittest.TestCase):
    def test_demo_then_read_then_transform(self):
        from midiforge.reader import read_file

        src = tmp_path("rt.mid")
        self.assertEqual(run("demo", "-o", src)[0], 0)
        dst = tmp_path("rt_out.mid")
        self.assertEqual(run("transpose", src, "-s", "-2", "-o", dst)[0], 0)
        midi = read_file(dst)
        from midiforge.notes import extract_notes

        self.assertTrue(len(extract_notes(midi)) > 0)

    def test_output_revalidates(self):
        src = tmp_path("rv.mid")
        run("demo", "-o", src)
        dst = tmp_path("rv_clean.mid")
        run("clean", src, "-o", dst)
        code, _, _ = run("validate", dst)
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
