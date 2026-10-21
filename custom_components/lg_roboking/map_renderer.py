"""LG Roboking map snapshot to 1:1 official LG app aesthetic PNG renderer.

Implements official LG GKM-20 map algorithm:
- Pure-Python LZ-String decompression
- LG official room color palette (#A2386E, #5C6BC0, #4D908E, #E09F3E, etc.)
- 2-Pass clean path rendering (Pass 1: corridor sweep #85B8FF, Pass 2: center line #FFFFFF)
- Alpha-composited restricted areas (VW) with crisp orange border (#EB4B1E)
- Dock at HOME_POS and docked robot hide logic matching official app
- Solid RGB canvas export to prevent Home Assistant theme background bleed-through
"""
from __future__ import annotations

import io
import math
import re
from io import BytesIO
from typing import Any

from PIL import Image, ImageDraw, ImageFont

_KEY_STR_BASE64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
_BASE64_INDEX = {c: i for i, c in enumerate(_KEY_STR_BASE64)}


def decompress_from_base64(input_str: str) -> list[int]:
    """Pure-Python implementation of LZ-String decompressFromBase64."""
    if not input_str:
        return []
    length = len(input_str)
    reset_val = 32

    def get_next_val(index: int) -> int:
        if index < length:
            return _BASE64_INDEX.get(input_str[index], 0)
        return 0

    dictionary = [0, 1, 2]
    enlarge_in = 4
    dict_size = 4
    num_bits = 3
    result = []

    val = get_next_val(0)
    position = reset_val
    index = 1

    bits = 0
    maxpower = 4
    power = 1
    while power != maxpower:
        res_b = val & position
        position >>= 1
        if position == 0:
            position = reset_val
            val = get_next_val(index)
            index += 1
        bits |= (1 if res_b > 0 else 0) * power
        power <<= 1

    next_c = bits
    if next_c == 0:
        bits = 0
        maxpower = 256
        power = 1
        while power != maxpower:
            res_b = val & position
            position >>= 1
            if position == 0:
                position = reset_val
                val = get_next_val(index)
                index += 1
            bits |= (1 if res_b > 0 else 0) * power
            power <<= 1
        c = chr(bits)
    elif next_c == 1:
        bits = 0
        maxpower = 65536
        power = 1
        while power != maxpower:
            res_b = val & position
            position >>= 1
            if position == 0:
                position = reset_val
                val = get_next_val(index)
                index += 1
            bits |= (1 if res_b > 0 else 0) * power
            power <<= 1
        c = chr(bits)
    elif next_c == 2:
        return []

    dictionary.append(c)
    w = c
    result.append(ord(c))

    while True:
        if index > length:
            return []

        bits = 0
        maxpower = 2 ** num_bits
        power = 1
        while power != maxpower:
            res_b = val & position
            position >>= 1
            if position == 0:
                position = reset_val
                val = get_next_val(index)
                index += 1
            bits |= (1 if res_b > 0 else 0) * power
            power <<= 1

        c = bits
        if c == 0:
            bits = 0
            maxpower = 256
            power = 1
            while power != maxpower:
                res_b = val & position
                position >>= 1
                if position == 0:
                    position = reset_val
                    val = get_next_val(index)
                    index += 1
                bits |= (1 if res_b > 0 else 0) * power
                power <<= 1
            dictionary.append(chr(bits))
            c = dict_size
            dict_size += 1
            enlarge_in -= 1
        elif c == 1:
            bits = 0
            maxpower = 65536
            power = 1
            while power != maxpower:
                res_b = val & position
                position >>= 1
                if position == 0:
                    position = reset_val
                    val = get_next_val(index)
                    index += 1
                bits |= (1 if res_b > 0 else 0) * power
                power <<= 1
            dictionary.append(chr(bits))
            c = dict_size
            dict_size += 1
            enlarge_in -= 1
        elif c == 2:
            return result

        if enlarge_in == 0:
            enlarge_in = 2 ** num_bits
            num_bits += 1

        if c < len(dictionary) and dictionary[c] is not None:
            entry = dictionary[c]
        else:
            if c == dict_size:
                entry = w + w[0]
            else:
                return []

        for ch in entry:
            result.append(ord(ch))

        dictionary.append(w + entry[0])
        dict_size += 1
        enlarge_in -= 1
        w = entry

        if enlarge_in == 0:
            enlarge_in = 2 ** num_bits
            num_bits += 1


# Official LG Roboking palette directly sampled from LG ThinQ app
LG_OFFICIAL_ROOM_COLORS = {
    3: (126, 99, 168, 255),   # Muted Purple (Room 3)
    5: (162, 56, 110, 255),   # Deep Berry Magenta (Living room 5)
    7: (183, 125, 66, 255),   # Warm Mustard Gold (Room 7)
    8: (136, 123, 176, 255),  # Soft Lavender / Periwinkle (Hallway 8)
    10: (72, 155, 184, 255),  # Teal Cyan (Room 10)
}

FALLBACK_PALETTE = [
    (189, 90, 56, 255),   # Terracotta Red-Orange
    (162, 56, 110, 255),  # Berry Magenta
    (126, 99, 168, 255),  # Purple
    (72, 155, 184, 255),  # Teal Cyan
    (183, 125, 66, 255),  # Warm Mustard
    (136, 123, 176, 255), # Lavender
]


def render_roboking_map(snapshot: dict[str, Any]) -> bytes:
    """Render LG Roboking map snapshot to 1:1 official LG app aesthetic PNG."""
    rt_map = snapshot.get("RT_MAP") or {}
    rt_map_l = rt_map.get("RT_MAP_L")
    if not rt_map_l:
        img = Image.new("RGB", (400, 300), (0, 0, 0))
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    width = int(rt_map.get("WIDTH", 200))
    height = int(rt_map.get("HEIGHT", 200))
    resolution = float(rt_map.get("RESOLUTION", 0.05))
    x_min = float(rt_map.get("X_MIN", 0.0))
    y_min = float(rt_map.get("Y_MIN", 0.0))

    grid = decompress_from_base64(rt_map_l)
    if len(grid) != width * height:
        if len(grid) < width * height:
            grid.extend([0] * (width * height - len(grid)))
        else:
            grid = grid[:width * height]

    SCALE = 3
    canvas_w = width * SCALE
    canvas_h = height * SCALE

    # Pitch black background matching LG official app (solid 100% opaque)
    base_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 255))

    grid_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = grid_img.load()

    min_gx, max_gx = width, 0
    min_gy, max_gy = height, 0
    has_content = False

    palette_idx = 0
    assigned_rooms: dict[int, tuple[int, int, int, int]] = {}

    for idx, val in enumerate(grid):
        x = idx % width
        y = idx // width
        draw_y = height - 1 - y

        if val == 0:
            pixels[x, draw_y] = (0, 0, 0, 0)
        elif val == 255:
            # Wall boundary (#2D2F36)
            pixels[x, draw_y] = (45, 47, 54, 255)
            if x < min_gx: min_gx = x
            if x > max_gx: max_gx = x
            if draw_y < min_gy: min_gy = draw_y
            if draw_y > max_gy: max_gy = draw_y
            has_content = True
        else:
            room_id = val - 50 if val > 50 else val
            if room_id in LG_OFFICIAL_ROOM_COLORS:
                c = LG_OFFICIAL_ROOM_COLORS[room_id]
            else:
                if room_id not in assigned_rooms:
                    assigned_rooms[room_id] = FALLBACK_PALETTE[palette_idx % len(FALLBACK_PALETTE)]
                    palette_idx += 1
                c = assigned_rooms[room_id]
            pixels[x, draw_y] = c
            if x < min_gx: min_gx = x
            if x > max_gx: max_gx = x
            if draw_y < min_gy: min_gy = draw_y
            if draw_y > max_gy: max_gy = draw_y
            has_content = True

    grid_scaled = grid_img.resize((canvas_w, canvas_h), Image.Resampling.NEAREST)
    base_img.alpha_composite(grid_scaled)

    def mm_to_canvas(pos_x_mm: float, pos_y_mm: float) -> tuple[float, float]:
        px = ((pos_x_mm / 1000.0) - x_min) / resolution * SCALE
        py = (height - (((pos_y_mm / 1000.0) - y_min) / resolution)) * SCALE
        return px, py

    # 1. Cleaning Trajectory Lines (Official LG Thinq Algorithm: GKM-20.bundle.js)
    rtw_keys: list[tuple[int, str]] = []
    for k in snapshot.keys():
        if k == "RTW" and isinstance(snapshot[k], list):
            rtw_keys.append((0, k))
        elif k.startswith("RTW"):
            m = re.match(r"^RTW(\d+)$", k)
            if m:
                rtw_keys.append((int(m.group(1)), k))
    rtw_keys.sort(key=lambda item: item[0])

    all_path_points: list[Any] = []
    for _, key in rtw_keys:
        chunk = snapshot[key]
        if isinstance(chunk, list):
            all_path_points.extend(chunk)

    segments: list[list[tuple[float, float]]] = []
    current_segment: list[tuple[float, float]] = []
    prev_screen_pos: tuple[float, float] | None = None
    prev_raw_pt: tuple[float, float, float] | None = None

    for pt in all_path_points:
        if not isinstance(pt, (list, tuple)) or len(pt) < 2:
            continue

        m = float(pt[0])
        f = float(pt[1])
        p = float(pt[2]) if len(pt) > 2 else 1.0

        E = float(prev_raw_pt[0]) if prev_raw_pt else None
        h = float(prev_raw_pt[1]) if prev_raw_pt else None
        T = float(prev_raw_pt[2]) if prev_raw_pt and len(prev_raw_pt) > 2 else 1.0

        is_clean = (p == 1.0)
        was_clean = (T == 1.0)
        is_nav = (p in (2.0, 3.0, 4.0))
        was_nav = (T in (2.0, 3.0, 4.0))

        # A is True when transitioning between clean path and navigation/homing/escape
        A = (is_clean and was_nav) or (is_nav and was_clean)

        # In cleanPath mode, skip navigation/homing/escape points
        if not is_clean:
            if len(current_segment) >= 2:
                segments.append(current_segment)
            current_segment = []
            prev_raw_pt = (m, f, p)
            continue

        cx, cy = mm_to_canvas(m, f)
        # Center of cell (0.5 * cell size) matching LG official webapp
        cx += SCALE / 2.0
        cy += SCALE / 2.0

        if prev_screen_pos is None:
            current_segment = [(cx, cy)]
        else:
            if A:
                # Mode transition: lift pen, start new segment
                if len(current_segment) >= 2:
                    segments.append(current_segment)
                current_segment = [(cx, cy)]
                prev_screen_pos = (cx, cy)
                prev_raw_pt = (m, f, p)
                continue

            dist = math.hypot(cx - prev_screen_pos[0], cy - prev_screen_pos[1])
            if dist > 60.0:
                # LG official threshold: if dist > 60px, only connect if moving along same X or Y axis
                if E is not None and h is not None and (m == E or f == h):
                    current_segment.append((cx, cy))
                else:
                    if len(current_segment) >= 2:
                        segments.append(current_segment)
                    current_segment = [(cx, cy)]
            else:
                current_segment.append((cx, cy))

        prev_screen_pos = (cx, cy)
        prev_raw_pt = (m, f, p)

    if len(current_segment) >= 2:
        segments.append(current_segment)

    # -------------------------------------------------------------------------
    # 🌟 ALPHA OVERLAY LAYER: True Alpha Compositing for Semi-transparent Elements
    # Prevents PIL ImageDraw from overwriting base_img's alpha channel with low values,
    # which would otherwise bleed Home Assistant's theme white background through.
    # -------------------------------------------------------------------------
    overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay, "RGBA")

    # Pass 1: Translucent sweep corridor (4.5 * cellSize, #85B8FF) matching official LG GKM-20 webapp
    sweep_width = int(4.5 * SCALE)
    for seg in segments:
        overlay_draw.line(seg, fill=(133, 184, 255, 60), width=sweep_width)

    # 2. Virtual Walls & Restricted Areas (VW) Semi-transparent Fill
    # Official LG specification: 15% tint (#FF3B30 + 15% opacity).
    # Rendered onto overlay then alpha-composited so rooms and sweep lines remain visible beneath.
    vw = snapshot.get("VW") or {}
    for poly in vw.get("VERTX") or []:
        if len(poly) >= 3:
            pts = [mm_to_canvas(pt[0], pt[1]) for pt in poly]
            overlay_draw.polygon(pts, fill=(255, 59, 48, 45))
            for p in pts:
                if p[0] / SCALE < min_gx:
                    min_gx = max(0, int(p[0] / SCALE))
                if p[0] / SCALE > max_gx:
                    max_gx = min(width - 1, int(p[0] / SCALE))
                if p[1] / SCALE < min_gy:
                    min_gy = max(0, int(p[1] / SCALE))
                if p[1] / SCALE > max_gy:
                    max_gy = min(height - 1, int(p[1] / SCALE))

    # Composite translucent overlay onto base_img: preserves base_img's 100% solid opacity!
    base_img = Image.alpha_composite(base_img, overlay)

    # Now draw crisp solid elements on base_img
    draw = ImageDraw.Draw(base_img, "RGBA")

    # Pass 2: Crisp white center trajectory (0.5 * cellSize, #FFFFFF)
    for seg in segments:
        draw.line(seg, fill=(255, 255, 255, 240), width=1)

    # Restricted Area Crisp Orange-Red Borders & Virtual Lines (width=2)
    for poly in vw.get("VERTX") or []:
        if len(poly) >= 3:
            pts = [mm_to_canvas(pt[0], pt[1]) for pt in poly]
            draw.polygon(pts, outline=(235, 75, 30, 255), width=2)

    for line in vw.get("VLINE") or []:
        if len(line) >= 2:
            p1 = mm_to_canvas(line[0][0], line[0][1])
            p2 = mm_to_canvas(line[1][0], line[1][1])
            draw.line([p1, p2], fill=(235, 75, 30, 255), width=2)

    # 3. Sofa / Furniture Icons from FLOORMAP.AREA (Official app aesthetic)
    floormap = snapshot.get("FLOORMAP") or {}
    for area in floormap.get("AREA") or []:
        pos = area.get("ICON_POS")
        if pos and len(pos) >= 2:
            ax, ay = mm_to_canvas(pos[0], pos[1])
            if 0 <= ax < canvas_w and 0 <= ay < canvas_h:
                sw, sh = 20, 14
                # Pill background with translucent dark fill for high contrast over rooms
                draw.rounded_rectangle(
                    [ax - sw / 2 - 2, ay - sh / 2 - 2, ax + sw / 2 + 2, ay + sh / 2 + 2],
                    radius=4,
                    fill=(30, 32, 38, 200),
                    outline=(255, 255, 255, 220),
                    width=1,
                )
                # Inner sofa frame
                draw.rounded_rectangle(
                    [ax - sw / 2 + 2, ay - sh / 2 + 2, ax + sw / 2 - 2, ay + sh / 2 - 2],
                    radius=2,
                    outline=(255, 255, 255, 220),
                    width=1,
                )
                # Sofa armrests
                draw.line(
                    [ax - sw / 2 + 5, ay - sh / 2 + 2, ax - sw / 2 + 5, ay + sh / 2 - 2],
                    fill=(255, 255, 255, 220),
                    width=1,
                )
                draw.line(
                    [ax + sw / 2 - 5, ay - sh / 2 + 2, ax + sw / 2 - 5, ay + sh / 2 - 2],
                    fill=(255, 255, 255, 220),
                    width=1,
                )

    # 4. Dock Position (HOME_POS) - High-visibility Cyan Dock Icon
    home_pos = rt_map.get("HOME_POS") or snapshot.get("HOME_POS")
    if home_pos and len(home_pos) >= 2:
        hx, hy = mm_to_canvas(home_pos[0], home_pos[1])
        dock_r = 11
        # Dark outline shadow for universal contrast
        draw.ellipse(
            [hx - dock_r - 2, hy - dock_r - 2, hx + dock_r + 2, hy + dock_r + 2],
            fill=(20, 20, 25, 180),
        )
        # Cyan circular base
        draw.ellipse(
            [hx - dock_r, hy - dock_r, hx + dock_r, hy + dock_r],
            fill=(0, 165, 196, 255),
            outline=(255, 255, 255, 255),
            width=2,
        )
        # Crisp white home icon inside
        draw.polygon([(hx, hy - 6), (hx - 6, hy), (hx + 6, hy)], fill=(255, 255, 255, 255))
        draw.rectangle([hx - 4, hy, hx + 4, hy + 5], fill=(255, 255, 255, 255))

    # 5. Robot Current Pose (RT_POSE) - Official style robot marker
    # In official LG ThinQ app, when the robot is docked/charging/standby, the robot
    # is docked at HOME_POS and the separate robot icon is hidden (only the dock is shown).
    # This prevents showing a stale robot position in the last-cleaned room when it is actually charging.
    robot_state = str(snapshot.get("ROBOT_STATE", "")).upper().strip()
    show_robot = robot_state not in ("STANDBY", "CHARGING", "SLEEP", "POWER_OFF", "")

    rt_pose = snapshot.get("RT_POSE") or {}
    cur_pos = rt_pose.get("CUR_POS")
    if show_robot and cur_pos and len(cur_pos) >= 2:
        rx, ry = mm_to_canvas(cur_pos[0], cur_pos[1])
        bot_r = 11
        draw.ellipse([rx - bot_r - 3, ry - bot_r - 3, rx + bot_r + 3, ry + bot_r + 3], fill=(0, 160, 255, 70))
        draw.ellipse([rx - bot_r, ry - bot_r, rx + bot_r, ry + bot_r], fill=(245, 245, 250, 255), outline=(0, 140, 255, 255), width=2)
        draw.ellipse([rx - 3, ry - 3, rx + 3, ry + 3], fill=(0, 140, 255, 255))

        theta_raw = cur_pos[2] if len(cur_pos) > 2 else 0.0
        deg = theta_raw if abs(theta_raw) <= 360 else (theta_raw / 1000.0) * (180.0 / math.pi)
        rad = math.radians(-deg)

        tip_x = rx + (bot_r + 6) * math.cos(rad)
        tip_y = ry + (bot_r + 6) * math.sin(rad)
        draw.line([rx, ry, tip_x, tip_y], fill=(0, 140, 255, 255), width=2)
        draw.ellipse([tip_x - 2, tip_y - 2, tip_x + 2, tip_y + 2], fill=(255, 200, 0, 255))

    # Auto-crop with 20px padding around content
    if has_content and max_gx > min_gx and max_gy > min_gy:
        crop_pad = 20
        cx1 = max(0, min_gx * SCALE - crop_pad)
        cy1 = max(0, min_gy * SCALE - crop_pad)
        cx2 = min(canvas_w, (max_gx + 1) * SCALE + crop_pad)
        cy2 = min(canvas_h, (max_gy + 1) * SCALE + crop_pad)
        base_img = base_img.crop((cx1, cy1, cx2, cy2))

    buf = BytesIO()
    # Save as 100% solid RGB PNG: Prevents HA theme white/grey background bleed-through
    base_img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()
