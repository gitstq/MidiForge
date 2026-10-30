"""VLQ 编解码测试。"""

from __future__ import annotations

import unittest

from midiforge.errors import MidiParseError
from midiforge.vlq import read_vlq, vlq_size, write_vlq


class TestWriteVLQ(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(write_vlq(0), b"\x00")

    def test_small_value_single_byte(self):
        self.assertEqual(write_vlq(127), b"\x7F")

    def test_boundary_128_needs_two_bytes(self):
        self.assertEqual(write_vlq(128), b"\x81\x00")

    def test_two_bytes(self):
        self.assertEqual(write_vlq(0x2000), b"\xC0\x00")

    def test_three_bytes(self):
        self.assertEqual(write_vlq(0x100000 >> 0), b"\xC0\x80\x00")

    def test_max_value(self):
        self.assertEqual(write_vlq(0x0FFFFFFF), b"\xFF\xFF\xFF\x7F")

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            write_vlq(-1)

    def test_overflow_raises(self):
        with self.assertRaises(ValueError):
            write_vlq(0x10000000)

    def test_size_matches(self):
        for value in (0, 1, 127, 128, 16383, 16384, 0x0FFFFFFF):
            self.assertEqual(vlq_size(value), len(write_vlq(value)))


class TestReadVLQ(unittest.TestCase):
    def test_read_zero(self):
        self.assertEqual(read_vlq(b"\x00", 0), (0, 1))

    def test_read_offset(self):
        self.assertEqual(read_vlq(b"\xAA\x81\x00", 1), (128, 3))

    def test_read_multibyte(self):
        self.assertEqual(read_vlq(b"\xFF\xFF\xFF\x7F", 0), (0x0FFFFFFF, 4))

    def test_truncated_raises(self):
        with self.assertRaises(MidiParseError):
            read_vlq(b"\x81", 0)

    def test_too_long_raises(self):
        with self.assertRaises(MidiParseError):
            read_vlq(b"\x80\x80\x80\x80\x00", 0)

    def test_roundtrip(self):
        for value in (0, 5, 127, 128, 255, 4096, 1000000, 0x0FFFFFFF):
            self.assertEqual(read_vlq(write_vlq(value), 0), (value, len(write_vlq(value))))


if __name__ == "__main__":
    unittest.main()
