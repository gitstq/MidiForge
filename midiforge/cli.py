"""MidiForge 命令行接口。

全部子命令都支持 ``--json`` / ``--quiet`` 等通用开关，
输出稳定可解析，方便被脚本或 AI Agent 直接消费。
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional, Sequence

from . import __version__
from .analysis import stats
from .diff import diff_midi, format_diff
from .errors import MidiForgeError, MidiValueError
from .export import (
    midi_to_json,
    notes_to_csv,
    notes_to_json,
    notes_to_markdown,
    piano_roll,
    write_text,
)
from .notes import extract_notes
from .reader import read_file
from .tempo import TempoMap
from .validate import summarize, validate
from .writer import write_file

NOTE_TYPES = (0x8, 0x9)


# ---------------------------------------------------------------- 构建


def build_parser() -> argparse.ArgumentParser:
    """构造命令行解析器。"""
    parser = argparse.ArgumentParser(
        prog="midiforge",
        description="MidiForge —— 零依赖 MIDI 文件处理与分析工具箱",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  midiforge info song.mid\n"
            "  midiforge stats song.mid --json\n"
            "  midiforge notes song.mid --csv -o notes.csv\n"
            "  midiforge transpose song.mid -s 3 -o out.mid\n"
            "  midiforge quantize song.mid --grid 16 --swing 0.2 -o out.mid\n"
        ),
    )
    parser.add_argument("--version", action="version", version="MidiForge %s" % __version__)
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    def add(name: str, help_text: str, aliases: Sequence[str] = ()):
        return sub.add_parser(name, help=help_text, aliases=list(aliases))

    # info
    p = add("info", "显示 MIDI 文件概览")
    p.add_argument("file")
    p.add_argument("--json", action="store_true", help="以 JSON 输出")

    # validate
    p = add("validate", "校验结构并给出问题清单", aliases=["lint"])
    p.add_argument("file")
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true", help="同时输出 info 级问题")

    # notes
    p = add("notes", "列出所有音符")
    p.add_argument("file")
    p.add_argument("--json", action="store_true")
    p.add_argument("--csv", action="store_true", help="以 CSV 输出")
    p.add_argument("--md", action="store_true", help="以 Markdown 表格输出")
    p.add_argument("--no-drums", action="store_true", help="排除打击乐通道")
    p.add_argument("--limit", type=int, default=0, help="只显示前 N 个音符")
    p.add_argument("-o", "--output", help="写入文件（默认 stdout）")

    # stats
    p = add("stats", "音乐内容分析：调性、和弦、节奏与力度分布", aliases=["analyze"])
    p.add_argument("file")
    p.add_argument("--json", action="store_true")

    # roll
    p = add("roll", "终端 ASCII 钢琴卷帘")
    p.add_argument("file")
    p.add_argument("--width", type=int, default=72)
    p.add_argument("--rows", type=int, default=24)

    # diff
    p = add("diff", "对比两个 MIDI 文件的音符差异")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--json", action="store_true")
    p.add_argument("--tolerance", type=int, default=0, help="起始时间容差（tick）")

    # demo
    p = add("demo", "生成内置示例曲（无需外部素材）")
    p.add_argument("--bpm", type=float, default=108.0)
    p.add_argument("--bars", type=int, default=4)
    p.add_argument("-o", "--output", default="demo.mid")

    # transpose
    p = add("transpose", "整体移调")
    p.add_argument("file")
    p.add_argument("-s", "--semitones", type=int, required=True)
    p.add_argument("--channels", help="只处理这些通道，如 0,1,2")
    p.add_argument("--include-drums", action="store_true")
    p.add_argument("-o", "--output", required=True)

    # quantize
    p = add("quantize", "量化音符起始位置")
    p.add_argument("file")
    p.add_argument("-g", "--grid", default="16", help="网格：tick 数或 4/8/16 等音符分母")
    p.add_argument("--strength", type=float, default=1.0)
    p.add_argument("--swing", type=float, default=0.0)
    p.add_argument("--channels", help="只处理这些通道")
    p.add_argument("-o", "--output", required=True)

    # velocity
    p = add("velocity", "调整力度（缩放 / 平移 / 动态压缩）")
    p.add_argument("file")
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--ratio", type=float, default=1.0, help="动态压缩比，>1 压缩")
    p.add_argument("--channels", help="只处理这些通道")
    p.add_argument("-o", "--output", required=True)

    # humanize
    p = add("humanize", "加入可控随机扰动（固定种子可复现）")
    p.add_argument("file")
    p.add_argument("--tick-jitter", type=int, default=8)
    p.add_argument("--velocity-jitter", type=int, default=6)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("-o", "--output", required=True)

    # tempo
    p = add("tempo", "设置或缩放速度（BPM）")
    p.add_argument("file")
    p.add_argument("--set", type=float, dest="set_bpm", help="设为固定 BPM")
    p.add_argument("--scale", type=float, help="按倍率缩放 BPM（>1 更快）")
    p.add_argument("--stretch", type=float, help="按倍率缩放时间轴（>1 更长）")
    p.add_argument("-o", "--output", required=True)

    # trim
    p = add("trim", "裁剪到指定区间")
    p.add_argument("file")
    p.add_argument("--start", type=int, default=0, help="起始 tick")
    p.add_argument("--end", type=int, help="结束 tick（缺省到结尾）")
    p.add_argument("-o", "--output", required=True)

    # merge / split / convert
    p = add("merge", "把所有轨道合并为一条")
    p.add_argument("file")
    p.add_argument("-o", "--output", required=True)

    p = add("split", "按通道拆分为多条轨道")
    p.add_argument("file")
    p.add_argument("-o", "--output", required=True)

    p = add("convert", "转换格式 / 导出为 CSV、JSON、Markdown")
    p.add_argument("file")
    p.add_argument("--format", type=int, choices=[0, 1, 2], help="目标 MIDI 格式")
    p.add_argument("--to", choices=["csv", "json", "md"], help="导出为文本格式")
    p.add_argument("-o", "--output", required=True)

    # strip
    p = add("strip", "按类别移除事件")
    p.add_argument("file")
    p.add_argument("--sysex", action="store_true")
    p.add_argument("--cc", action="store_true", help="移除控制器事件")
    p.add_argument("--keep-cc", help="保留的控制器编号，如 7,10,64")
    p.add_argument("--program", action="store_true")
    p.add_argument("--pitch-bend", action="store_true")
    p.add_argument("--aftertouch", action="store_true")
    p.add_argument("--lyrics", action="store_true")
    p.add_argument("--markers", action="store_true")
    p.add_argument("-o", "--output", required=True)

    # clean
    p = add("clean", "修复孤儿音符关 / 未闭合音符 / 重复事件")
    p.add_argument("file")
    p.add_argument("--dedupe", action="store_true", help="同时移除完全重叠的重复音符")
    p.add_argument("-o", "--output", required=True)

    return parser


# ---------------------------------------------------------------- 分发


def main(argv: Optional[Sequence[str]] = None) -> int:
    """命令行入口。返回进程退出码。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 1
    handler = _HANDLERS.get(args.command)
    if handler is None:  # pragma: no cover
        parser.print_help()
        return 1
    try:
        return handler(args)
    except MidiForgeError as exc:
        print("错误: %s" % exc, file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print("错误: %s" % exc, file=sys.stderr)
        return 2


def _emit(text: str, path: Optional[str]) -> int:
    if path:
        write_text(path, text)
        print("已写入 %s" % path)
    else:
        print(text)
    return 0


def _channels(value: Optional[str]):
    if not value:
        return None
    return [int(x) for x in value.replace(" ", "").split(",") if x != ""]


def _grid(value: str, division: int) -> int:
    """把 ``16`` / ``1/16`` / ``240`` 之类的写法换算成 tick。"""
    text = str(value).strip()
    if "/" in text:
        _, _, denom = text.partition("/")
        return max(1, division // int(denom))
    try:
        number = int(text)
    except ValueError:
        raise MidiValueError("无法解析网格值: %r" % value)
    # 4/8/16/32 视作音符分母；大于等于 64 视作 tick 原值
    return number if number >= 64 else max(1, division // number)


# -- handlers ------------------------------------------------------


def _cmd_info(args) -> int:
    midi = read_file(args.file)
    data = midi.summary()
    if args.json:
        return _emit(json.dumps(data, ensure_ascii=False, indent=2), None)
    lines = [
        "文件        : %s" % args.file,
        "MIDI 格式   : %d" % data["format"],
        "时基        : %d ticks/四分音符" % data["ticks_per_quarter"],
        "轨道数      : %d  事件数: %d  音符事件: %d" % (
            data["tracks"],
            data["events"],
            data["note_events"],
        ),
        "时长        : %.2f 秒（%d tick）" % (data["duration_seconds"], data["end_tick"]),
        "起始速度    : %.2f BPM   速度变化: %d" % (data["initial_bpm"], data["tempo_changes"]),
        "拍号        : %s" % data["time_signature"],
        "使用通道    : %s" % (", ".join(str(c) for c in data["channels"]) or "-"),
        "轨道名      : %s" % ", ".join(data["track_names"]) or "-",
    ]
    return _emit("\n".join(lines), None)


def _cmd_validate(args) -> int:
    midi = read_file(args.file)
    issues = validate(midi, strict=args.strict)
    summary = summarize(issues)
    if args.json:
        payload = {
            "file": args.file,
            "summary": summary,
            "issues": [i.to_dict() for i in issues],
        }
        return _emit(json.dumps(payload, ensure_ascii=False, indent=2), None)
    lines = ["文件: %s" % args.file]
    if not issues:
        lines.append("✅ 未发现问题")
    for issue in issues:
        lines.append(str(issue))
    lines.append(
        "── 合计 %d 条（error %d / warning %d / info %d）"
        % (summary["total"], summary["errors"], summary["warnings"], summary["infos"])
    )
    return _emit("\n".join(lines), None) if summary["errors"] == 0 else _emit_lines_error(lines)


def _emit_lines_error(lines: List[str]) -> int:
    print("\n".join(lines))
    return 1


def _cmd_notes(args) -> int:
    midi = read_file(args.file)
    tempo_map = TempoMap.from_midi(midi)
    notes = extract_notes(midi, tempo_map=tempo_map, include_drums=not args.no_drums)
    if args.limit:
        notes = notes[: args.limit]
    if args.json:
        return _emit(notes_to_json(notes), args.output)
    if args.csv:
        return _emit(notes_to_csv(notes), args.output)
    if args.md:
        return _emit(notes_to_markdown(notes, limit=args.limit or 100), args.output)
    lines = ["共 %d 个音符" % len(notes)]
    for n in notes:
        lines.append(
            "  track=%d ch=%-2d %-5s vel=%-3d tick %d→%d (%.3fs, %d ticks)"
            % (
                n.track,
                n.channel,
                n.label,
                n.velocity,
                n.start,
                n.end,
                n.start_sec,
                n.duration,
            )
        )
    return _emit("\n".join(lines), args.output)


def _cmd_stats(args) -> int:
    midi = read_file(args.file)
    tempo_map = TempoMap.from_midi(midi)
    notes = extract_notes(midi, tempo_map=tempo_map)
    report = stats(midi, notes, tempo_map)
    if args.json:
        return _emit(json.dumps(report, ensure_ascii=False, indent=2), None)
    key = report["key"]
    lines = [
        "音符总数    : %d（旋律 %d / 打击乐 %d）" % (
            report["notes"],
            report["melodic_notes"],
            report["drum_notes"],
        ),
        "音域        : %s" % ("%s → %s" % tuple(report["pitch_range"]) if report["pitch_range"] else "-"),
        "时长        : %.2f 秒  密度 %.2f 音符/秒" % (
            report["duration_seconds"],
            report["notes_per_second"],
        ),
        "力度        : 平均 %.1f（%d - %d）" % (
            report["avg_velocity"],
            report["min_velocity"],
            report["max_velocity"],
        ),
        "最大同时发声: %d" % report["max_polyphony"],
        "调性猜测    : %s %s（置信度 %.2f）" % (
            key["key_label"],
            key["scale"],
            key["confidence"],
        ),
        "时值分布    : %s" % _fmt_dict(report["rhythm_histogram"], 6),
        "力度分布    : %s" % _fmt_dict(report["velocity_histogram"], 4),
        "和弦进行    : %s" % (
            " ".join(c["chord"] for c in report["chords"][:12]) or "-"
        ),
    ]
    if report["repeated_patterns"]:
        lines.append(
            "重复乐句    : %s"
            % "; ".join(
                "%s ×%d" % (p["pattern"], p["count"])
                for p in report["repeated_patterns"][:3]
            )
        )
    lines.append("轨道概览:")
    for t in report["tracks"]:
        lines.append(
            "  #%d %-12s notes=%-5d ch=%s %s"
            % (
                t["index"],
                t["name"][:12],
                t["notes"],
                ",".join(str(c) for c in t["channels"]) or "-",
                ", ".join(t["programs"].values()) or "-",
            )
        )
    return _emit("\n".join(lines), None)


def _fmt_dict(mapping: dict, limit: int) -> str:
    items = list(mapping.items())[:limit]
    return ", ".join("%s:%d" % (k, v) for k, v in items) or "-"


def _cmd_roll(args) -> int:
    midi = read_file(args.file)
    tempo_map = TempoMap.from_midi(midi)
    notes = extract_notes(midi, tempo_map=tempo_map)
    return _emit(piano_roll(notes, width=args.width, max_rows=args.rows), None)


def _cmd_diff(args) -> int:
    a = read_file(args.a)
    b = read_file(args.b)
    result = diff_midi(a, b, tolerance=args.tolerance)
    if args.json:
        return _emit(json.dumps(result, ensure_ascii=False, indent=2), None)
    return _emit(format_diff(result), None)


def _cmd_demo(args) -> int:
    from .builder import demo_song

    midi = demo_song(bpm=args.bpm, bars=args.bars)
    write_file(midi, args.output)
    print("已生成示例曲: %s（%.1f BPM，%d 小节，%d 轨道）" % (
        args.output, args.bpm, args.bars, len(midi.tracks)
    ))
    return 0


def _cmd_transpose(args) -> int:
    from .transform import transpose

    midi = read_file(args.file)
    out = transpose(
        midi,
        args.semitones,
        channels=_channels(args.channels),
        include_drums=args.include_drums,
    )
    write_file(out, args.output)
    print("已移调 %+d 半音 → %s" % (args.semitones, args.output))
    return 0


def _cmd_quantize(args) -> int:
    from .transform import quantize

    midi = read_file(args.file)
    grid = _grid(args.grid, midi.ticks_per_quarter)
    out = quantize(
        midi, grid, strength=args.strength, swing=args.swing, channels=_channels(args.channels)
    )
    write_file(out, args.output)
    print("已按 %d tick 网格量化（强度 %.2f，摇摆 %.2f）→ %s" % (
        grid, args.strength, args.swing, args.output
    ))
    return 0


def _cmd_velocity(args) -> int:
    from .transform import velocity

    midi = read_file(args.file)
    out = velocity(
        midi,
        scale=args.scale,
        offset=args.offset,
        ratio=args.ratio,
        channels=_channels(args.channels),
    )
    write_file(out, args.output)
    print("已调整力度（×%.2f, %+d, 压缩比 %.2f）→ %s" % (
        args.scale, args.offset, args.ratio, args.output
    ))
    return 0


def _cmd_humanize(args) -> int:
    from .transform import humanize

    midi = read_file(args.file)
    out = humanize(
        midi,
        tick_jitter=args.tick_jitter,
        velocity_jitter=args.velocity_jitter,
        seed=args.seed,
    )
    write_file(out, args.output)
    print("已加入人性化扰动（tick ±%d，力度 ±%d，seed=%d）→ %s" % (
        args.tick_jitter, args.velocity_jitter, args.seed, args.output
    ))
    return 0


def _cmd_tempo(args) -> int:
    from .transform import scale_tempo, scale_ticks, set_bpm

    if not (args.set_bpm or args.scale or args.stretch):
        raise MidiValueError("请指定 --set / --scale / --stretch 之一")
    midi = read_file(args.file)
    if args.set_bpm:
        out = set_bpm(midi, args.set_bpm)
        msg = "已设为 %.2f BPM" % args.set_bpm
    elif args.scale:
        out = scale_tempo(midi, args.scale)
        msg = "速度 ×%.3f" % args.scale
    else:
        out = scale_ticks(midi, args.stretch)
        msg = "时间轴 ×%.3f" % args.stretch
    write_file(out, args.output)
    print("%s → %s" % (msg, args.output))
    return 0


def _cmd_trim(args) -> int:
    from .transform import trim

    midi = read_file(args.file)
    out = trim(midi, start=args.start, end=args.end)
    write_file(out, args.output)
    print("已裁剪 [%d, %s) → %s" % (args.start, args.end or "结尾", args.output))
    return 0


def _cmd_merge(args) -> int:
    from .transform import merge_tracks

    midi = read_file(args.file)
    out = merge_tracks(midi)
    write_file(out, args.output)
    print("已合并 %d 条轨道 → %s" % (len(midi.tracks), args.output))
    return 0


def _cmd_split(args) -> int:
    from .transform import split_by_channel

    midi = read_file(args.file)
    out = split_by_channel(midi)
    write_file(out, args.output)
    print("已按通道拆分为 %d 条轨道 → %s" % (len(out.tracks), args.output))
    return 0


def _cmd_convert(args) -> int:
    from .transform import to_format

    midi = read_file(args.file)
    if args.to:
        tempo_map = TempoMap.from_midi(midi)
        notes = extract_notes(midi, tempo_map=tempo_map)
        if args.to == "csv":
            return _emit(notes_to_csv(notes), args.output)
        if args.to == "json":
            return _emit(midi_to_json(midi, tempo_map, notes), args.output)
        return _emit(notes_to_markdown(notes), args.output)
    if args.format is None:
        raise MidiValueError("请指定 --format 或 --to")
    out = to_format(midi, args.format)
    write_file(out, args.output)
    print("已转为 Format %d → %s" % (args.format, args.output))
    return 0


def _cmd_strip(args) -> int:
    from .transform import strip

    midi = read_file(args.file)
    out = strip(
        midi,
        sysex=args.sysex,
        controllers=args.cc,
        keep_controllers=_channels(args.keep_cc),
        program_change=args.program,
        pitch_bend=args.pitch_bend,
        aftertouch=args.aftertouch,
        lyrics=args.lyrics,
        markers=args.markers,
    )
    write_file(out, args.output)
    print("已清理 → %s" % args.output)
    return 0


def _cmd_clean(args) -> int:
    from .transform import clean, remove_duplicate_notes

    midi = read_file(args.file)
    out = clean(midi)
    if args.dedupe:
        out = remove_duplicate_notes(out)
    write_file(out, args.output)
    print("已修复 → %s" % args.output)
    return 0


_HANDLERS = {
    "info": _cmd_info,
    "validate": _cmd_validate,
    "lint": _cmd_validate,
    "notes": _cmd_notes,
    "stats": _cmd_stats,
    "analyze": _cmd_stats,
    "roll": _cmd_roll,
    "diff": _cmd_diff,
    "demo": _cmd_demo,
    "transpose": _cmd_transpose,
    "quantize": _cmd_quantize,
    "velocity": _cmd_velocity,
    "humanize": _cmd_humanize,
    "tempo": _cmd_tempo,
    "trim": _cmd_trim,
    "merge": _cmd_merge,
    "split": _cmd_split,
    "convert": _cmd_convert,
    "strip": _cmd_strip,
    "clean": _cmd_clean,
}


__all__ = ["main", "build_parser"]
