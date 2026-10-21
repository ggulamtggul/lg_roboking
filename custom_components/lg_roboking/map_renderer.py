"""Rendering engine for LG Roboking AI All-in-One map snapshots using Pillow."""
from __future__ import annotations

from io import BytesIO
import math
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
    result.append(c)

    while True:
        if index > length:
            return [ord(ch) for ch in "".join(result)]

        bits = 0
        maxpower = 1 << num_bits
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

        c_code = bits
        if c_code == 0:
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
            if len(dictionary) <= dict_size:
                dictionary.extend([None] * (dict_size - len(dictionary) + 1))
            dictionary[dict_size] = chr(bits)
            dict_size += 1
            c_code = dict_size - 1
            enlarge_in -= 1
        elif c_code == 1:
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
            if len(dictionary) <= dict_size:
                dictionary.extend([None] * (dict_size - len(dictionary) + 1))
            dictionary[dict_size] = chr(bits)
            dict_size += 1
            c_code = dict_size - 1
            enlarge_in -= 1
        elif c_code == 2:
            return [ord(ch) for ch in "".join(result)]

        if enlarge_in == 0:
            enlarge_in = 1 << num_bits
            num_bits += 1

        if c_code < len(dictionary) and dictionary[c_code] is not None:
            entry = dictionary[c_code]
        else:
            if c_code == dict_size:
                entry = w + w[0]
            else:
                return [ord(ch) for ch in "".join(result)]

        result.append(entry)
        if len(dictionary) <= dict_size:
            dictionary.extend([None] * (dict_size - len(dictionary) + 1))
        dictionary[dict_size] = w + entry[0]
        dict_size += 1
        enlarge_in -= 1
        w = entry

        if enlarge_in == 0:
            enlarge_in = 1 << num_bits
            num_bits += 1


# Refined Roborock/ThinQ aesthetic pastel palette
ROOM_PALETTE = [
    (145, 175, 245, 235),  # Soft Periwinkle Blue
    (245, 195, 95, 235),   # Soft Warm Amber
    (240, 145, 140, 235),  # Soft Coral
    (95, 210, 195, 235),   # Soft Mint / Teal
    (225, 150, 215, 235),  # Soft Orchid
    (150, 220, 145, 235),  # Soft Sage Green
    (245, 170, 120, 235),  # Soft Peach
]


def _get_font(size: int) -> ImageFont.ImageFont:
    """Safely obtain a clean TrueType font across Windows and Linux."""
    font_paths = [
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def render_roboking_map(snapshot: dict[str, Any]) -> bytes:
    """Render LG Roboking map snapshot to clean, proportional PNG bytes."""
    rt_map = snapshot.get("RT_MAP") or {}
    rt_map_l = rt_map.get("RT_MAP_L")
    if not rt_map_l:
        img = Image.new("RGBA", (400, 300), (22, 23, 27, 255))
        draw = ImageDraw.Draw(img)
        font = _get_font(14)
        draw.text((145, 135), "No Map Data", fill=(180, 180, 180, 255), font=font)
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

    # Calculate bounding box of rooms and walls to crop blank margins
    min_gx, max_gx = width, 0
    min_gy, max_gy = height, 0
    has_content = False

    for idx, val in enumerate(grid):
        if val != 0:
            gx = idx % width
            gy = idx // width
            draw_y = height - 1 - gy
            if gx < min_gx:
                min_gx = gx
            if gx > max_gx:
                max_gx = gx
            if draw_y < min_gy:
                min_gy = draw_y
            if draw_y > max_gy:
                max_gy = draw_y
            has_content = True

    SCALE = 3
    canvas_w = width * SCALE
    canvas_h = height * SCALE

    # Clean dark modern background (#1A1B20)
    base_img = Image.new("RGBA", (canvas_w, canvas_h), (26, 27, 32, 255))

    room_map: dict[int, tuple[int, int, int, int]] = {}
    palette_idx = 0

    grid_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = grid_img.load()

    for idx, val in enumerate(grid):
        x = idx % width
        y = idx // width
        draw_y = height - 1 - y

        if val == 0:
            pixels[x, draw_y] = (0, 0, 0, 0)
        elif val == 255:
            # Wall boundary (#383A42)
            pixels[x, draw_y] = (56, 58, 66, 255)
        elif val == 127:
            # Passed area
            pixels[x, draw_y] = (255, 255, 255, 140)
        elif val == 177:
            # Passed area carpet
            pixels[x, draw_y] = (235, 220, 180, 160)
        else:
            room_id = val - 50 if val > 50 else val
            if room_id not in room_map:
                room_map[room_id] = ROOM_PALETTE[palette_idx % len(ROOM_PALETTE)]
                palette_idx += 1
            pixels[x, draw_y] = room_map[room_id]

    grid_scaled = grid_img.resize((canvas_w, canvas_h), Image.Resampling.NEAREST)
    base_img.alpha_composite(grid_scaled)

    draw = ImageDraw.Draw(base_img, "RGBA")

    def mm_to_canvas(pos_x_mm: float, pos_y_mm: float) -> tuple[float, float]:
        px = ((pos_x_mm / 1000.0) - x_min) / resolution * SCALE
        py = (height - (((pos_y_mm / 1000.0) - y_min) / resolution)) * SCALE
        return px, py

    # 1. Virtual Walls and Restricted Areas (VW)
    vw = snapshot.get("VW") or {}
    for poly in vw.get("VERTX") or []:
        if len(poly) >= 3:
            pts = [mm_to_canvas(pt[0], pt[1]) for pt in poly]
            # Soft red transparent tint with thin boundary line
            draw.polygon(pts, fill=(235, 50, 50, 38), outline=(235, 60, 60, 180), width=1)
            min_px = min(p[0] for p in pts)
            max_px = max(p[0] for p in pts)
            min_py = min(p[1] for p in pts)
            max_py = max(p[1] for p in pts)
            if min_px / SCALE < min_gx:
                min_gx = max(0, int(min_px / SCALE))
            if max_px / SCALE > max_gx:
                max_gx = min(width - 1, int(max_px / SCALE))
            if min_py / SCALE < min_gy:
                min_gy = max(0, int(min_py / SCALE))
            if max_py / SCALE > max_gy:
                max_gy = min(height - 1, int(max_py / SCALE))

    for line in vw.get("VLINE") or []:
        if len(line) >= 2:
            p1 = mm_to_canvas(line[0][0], line[0][1])
            p2 = mm_to_canvas(line[1][0], line[1][1])
            draw.line([p1, p2], fill=(240, 50, 50, 220), width=2)

    # 2. Cleaning Trajectory (RTW)
    rtw = snapshot.get("RTW")
    if rtw and isinstance(rtw, list) and len(rtw) > 1:
        line_pts = []
        for pt in rtw:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                line_pts.append(mm_to_canvas(pt[0], pt[1]))
        if len(line_pts) >= 2:
            draw.line(line_pts, fill=(255, 255, 255, 180), width=1)

    # 3. Room labels / badges from FLOORMAP.AREA (Compact pill)
    floormap = snapshot.get("FLOORMAP") or {}
    badge_font = _get_font(11)
    for area in floormap.get("AREA") or []:
        pos = area.get("ICON_POS")
        area_id = int(area.get("ID", 0))
        if pos and len(pos) >= 2:
            ax, ay = mm_to_canvas(pos[0], pos[1])
            if 0 <= ax < canvas_w and 0 <= ay < canvas_h:
                br = 9
                draw.ellipse([ax - br, ay - br, ax + br, ay + br], fill=(20, 22, 28, 190), outline=(255, 255, 255, 160), width=1)
                num_str = str(area_id)
                draw.text((ax - 3, ay - 6), num_str, fill=(255, 255, 255, 230), font=badge_font)

    # 4. Dock Position (HOME_POS) - Compact stylish dock
    home_pos = rt_map.get("HOME_POS") or snapshot.get("HOME_POS")
    if home_pos and len(home_pos) >= 2:
        hx, hy = mm_to_canvas(home_pos[0], home_pos[1])
        dw, dh = 14, 10
        draw.rounded_rectangle([hx - dw/2, hy - dh/2, hx + dw/2, hy + dh/2], radius=3, fill=(40, 195, 110, 240), outline=(255, 255, 255, 230), width=1)
        draw.line([hx - 4, hy, hx + 4, hy], fill=(255, 255, 255, 255), width=2)

    # 5. Robot Current Pose (RT_POSE) - Proportional high-tech circular marker
    rt_pose = snapshot.get("RT_POSE") or {}
    cur_pos = rt_pose.get("CUR_POS")
    if cur_pos and len(cur_pos) >= 2:
        rx, ry = mm_to_canvas(cur_pos[0], cur_pos[1])
        bot_r = 10  # Crisp proportional size
        
        draw.ellipse([rx - bot_r - 4, ry - bot_r - 4, rx + bot_r + 4, ry + bot_r + 4], fill=(0, 140, 255, 60))
        draw.ellipse([rx - bot_r, ry - bot_r, rx + bot_r, ry + bot_r], fill=(0, 130, 250, 240), outline=(255, 255, 255, 255), width=2)
        draw.ellipse([rx - 3, ry - 3, rx + 3, ry + 3], fill=(255, 255, 255, 230))
        
        theta_raw = cur_pos[2] if len(cur_pos) > 2 else 0.0
        deg = theta_raw if abs(theta_raw) <= 360 else (theta_raw / 1000.0) * (180.0 / math.pi)
        rad = math.radians(-deg)
        
        tip_dist = bot_r + 7
        tip_x = rx + tip_dist * math.cos(rad)
        tip_y = ry + tip_dist * math.sin(rad)
        
        left_rad = rad + math.radians(140)
        right_rad = rad - math.radians(140)
        wing_dist = bot_r - 2
        lx = rx + wing_dist * math.cos(left_rad)
        ly = ry + wing_dist * math.sin(left_rad)
        rx_p = rx + wing_dist * math.cos(right_rad)
        ry_p = ry + wing_dist * math.sin(right_rad)
        
        draw.polygon([(tip_x, tip_y), (lx, ly), (rx, ry), (rx_p, ry_p)], fill=(255, 225, 60, 240))

    # Auto-crop with comfortable 25px padding around rooms and walls
    if has_content and max_gx > min_gx and max_gy > min_gy:
        crop_pad = 25
        cx1 = max(0, min_gx * SCALE - crop_pad)
        cy1 = max(0, min_gy * SCALE - crop_pad)
        cx2 = min(canvas_w, (max_gx + 1) * SCALE + crop_pad)
        cy2 = min(canvas_h, (max_gy + 1) * SCALE + crop_pad)
        base_img = base_img.crop((cx1, cy1, cx2, cy2))

    # Modern Top-Left Status Pill Badge
    draw_cropped = ImageDraw.Draw(base_img, "RGBA")
    status_font = _get_font(12)
    cur_room = int(rt_map.get("CUR_ROOMID", 0))
    sweep_area = rt_map.get("SWEEP_AREA", 0)
    info_text = f"Room {cur_room}  |  {sweep_area} m²"
    
    draw_cropped.rounded_rectangle([12, 12, 140, 36], radius=8, fill=(15, 17, 22, 210), outline=(255, 255, 255, 70), width=1)
    draw_cropped.text((22, 16), info_text, fill=(240, 240, 245, 240), font=status_font)

    buf = BytesIO()
    base_img.save(buf, format="PNG")
    return buf.getvalue()
