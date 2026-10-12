#!/usr/bin/env python3
"""NPC スキンの定義（JSON）から 64×64 の Minecraft スキン PNG を作る。

使い方:
  python3 tools/npc-skin/generate.py <定義.json> <出力.png>
  python3 tools/npc-skin/generate.py --faces <出力.png>   # 面の向き確認用（面ごとに色を変える）

UV 配置は docs/npc-skin-spec.md §2 のとおり。外部ライブラリは使わない（標準の zlib と struct のみ）。
"""
import json
import struct
import sys
import zlib

SIZE = 64

# パーツ名: (u, v, 幅 w, 奥行 d, 高さ h)。docs/npc-skin-spec.md §2 の表と同じ。
PARTS = {
    "head": (0, 0, 8, 8, 8),
    "hat": (32, 0, 8, 8, 8),
    "body": (16, 16, 8, 4, 12),
    "jacket": (16, 32, 8, 4, 12),
    "rightArm": (40, 16, 4, 4, 12),
    "rightSleeve": (40, 32, 4, 4, 12),
    "leftArm": (32, 48, 4, 4, 12),
    "leftSleeve": (48, 48, 4, 4, 12),
    "rightLeg": (0, 16, 4, 4, 12),
    "rightPants": (0, 32, 4, 4, 12),
    "leftLeg": (16, 48, 4, 4, 12),
    "leftPants": (0, 48, 4, 4, 12),
}


def faces(u, v, w, d, h):
    """6 面の矩形 (x, y, 幅, 高さ) を返す。順番は 右側面・前・左側面・後・上・下。"""
    return [
        (u, v + d, d, h),
        (u + d, v + d, w, h),
        (u + d + w, v + d, d, h),
        (u + 2 * d + w, v + d, w, h),
        (u + d, v, w, d),
        (u + d + w, v, w, d),
    ]


def hex_to_rgba(color):
    """'#rrggbb' を (r, g, b, 255) にする。"""
    if not (len(color) == 7 and color[0] == "#"):
        raise ValueError(f"色は #rrggbb で書く: {color}")
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return (r, g, b, 255)


def load_definition(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    parts = data.get("parts")
    if not isinstance(parts, dict):
        raise ValueError("parts がありません")
    missing = [name for name in PARTS if name not in parts]
    if missing:
        raise ValueError(f"parts が足りません: {', '.join(missing)}")
    unknown = [name for name in parts if name not in PARTS]
    if unknown:
        raise ValueError(f"未知のパーツ名: {', '.join(unknown)}")
    return parts


def paint(parts):
    """RGBA のピクセル配列（行ごとのリスト）を作る。色なしのパーツは透明のまま。"""
    pixels = [[(0, 0, 0, 0)] * SIZE for _ in range(SIZE)]
    for name, (u, v, w, d, h) in PARTS.items():
        color = parts[name].get("color")
        if color is None:
            continue
        rgba = hex_to_rgba(color)
        for x, y, fw, fh in faces(u, v, w, d, h):
            for py in range(y, y + fh):
                for px in range(x, x + fw):
                    pixels[py][px] = rgba
    return pixels


def paint_faces():
    """面ごとに違う色を塗る。ゲーム内で面の向きを確かめるための見本。"""
    palette = [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255),
               (255, 255, 0, 255), (255, 0, 255, 255), (0, 255, 255, 255)]
    pixels = [[(0, 0, 0, 0)] * SIZE for _ in range(SIZE)]
    for name, (u, v, w, d, h) in PARTS.items():
        for i, (x, y, fw, fh) in enumerate(faces(u, v, w, d, h)):
            for py in range(y, y + fh):
                for px in range(x, x + fw):
                    pixels[py][px] = palette[i]
    return pixels


def write_png(pixels, path):
    raw = b"".join(b"\x00" + bytes(c for px in row for c in px) for row in pixels)

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)  # 8bit RGBA
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(data)


def main(argv):
    if len(argv) == 3 and argv[1] == "--faces":
        write_png(paint_faces(), argv[2])
        return 0
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        parts = load_definition(argv[1])
        write_png(paint(parts), argv[2])
    except (ValueError, OSError, KeyError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
