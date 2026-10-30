"""可变长度数量（Variable Length Quantity）编解码。

SMF 用它编码 delta time 与部分长度字段：每字节低 7 位为数据，
最高位为 continuation bit，最多 4 字节。
"""

from __future__ import annotations

from .errors import MidiParseError

MAX_VLQ_BYTES = 4
MAX_VLQ_VALUE = 0x0FFFFFFF


def read_vlq(data: bytes, pos: int):
    """从 ``data[pos:]`` 读取一个 VLQ。

    Returns:
        ``(value, new_pos)``。

    Raises:
        MidiParseError: 超过 4 字节或数据被截断。
    """
    value = 0
    start = pos
    for _ in range(MAX_VLQ_BYTES):
        if pos >= len(data):
            raise MidiParseError("VLQ 数据被截断", start)
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, pos
    raise MidiParseError("VLQ 超过 4 字节", start)


def write_vlq(value: int) -> bytes:
    """把非负整数编码成 VLQ 字节串。

    Raises:
        ValueError: ``value`` 为负或超过 0x0FFFFFFF。
    """
    if value < 0:
        raise ValueError("VLQ 不支持负数: %r" % value)
    if value > MAX_VLQ_VALUE:
        raise ValueError("VLQ 超出范围: %r" % value)
    if value == 0:
        return b"\x00"
    chunks = []
    while value > 0:
        chunks.append(value & 0x7F)
        value >>= 7
    chunks.reverse()
    out = bytearray()
    for i, chunk in enumerate(chunks):
        out.append(chunk | (0x80 if i < len(chunks) - 1 else 0x00))
    return bytes(out)


def vlq_size(value: int) -> int:
    """返回该值编码后占用的字节数。"""
    return len(write_vlq(value))
