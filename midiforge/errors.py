"""MidiForge 异常类型定义。

所有异常都继承自 :class:`MidiForgeError`，方便调用方统一捕获。
"""

from __future__ import annotations


class MidiForgeError(Exception):
    """MidiForge 的异常基类。"""


class MidiParseError(MidiForgeError):
    """MIDI 字节流不符合 Standard MIDI File 规范时抛出。

    属性 ``offset`` 记录出错的字节偏移，便于定位损坏文件。
    """

    def __init__(self, message: str, offset: int = -1) -> None:
        self.offset = offset
        if offset >= 0:
            message = "%s (offset=%d)" % (message, offset)
        super().__init__(message)


class MidiWriteError(MidiForgeError):
    """序列化 MIDI 文件失败时抛出（通常是事件数据越界）。"""


class MidiValueError(MidiForgeError):
    """用户输入的参数不合法时抛出（移调超出范围、网格值非法等）。"""
