import json
import math
from io import BytesIO
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


ROOM_PALETTE = [
    (177, 158, 254, 230),  # violet
    (255, 202, 40, 230),   # yellow
    (255, 180, 169, 230),  # red-brown / orange
    (80, 219, 207, 230),   # teal green
    (255, 177, 195, 230),  # pink
    (130, 200, 250, 230),  # sky blue
    (180, 230, 140, 230),  # light green
]


def render_roboking_map(snapshot: dict) -> bytes:
    """Render LG Roboking map snapshot to PNG bytes."""
    rt_map = snapshot.get("RT_MAP") or {}
    rt_map_l = rt_map.get("RT_MAP_L")
    if not rt_map_l:
        img = Image.new("RGBA", (400, 400), (28, 28, 30, 255))
        draw = ImageDraw.Draw(img)
        draw.text((130, 190), "No Map Data", fill=(200, 200, 200, 255))
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

    SCALE = 4
    canvas_w = width * SCALE
    canvas_h = height * SCALE

    base_img = Image.new("RGBA", (canvas_w, canvas_h), (24, 26, 32, 255))
    
    room_map = {}
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
            pixels[x, draw_y] = (70, 75, 85, 255)
        elif val == 127:
            pixels[x, draw_y] = (255, 255, 255, 180)
        elif val == 177:
            pixels[x, draw_y] = (240, 230, 200, 200)
        else:
            room_id = val - 50 if val > 50 else val
            if room_id not in room_map:
                room_map[room_id] = ROOM_PALETTE[palette_idx % len(ROOM_PALETTE)]
                palette_idx += 1
            pixels[x, draw_y] = room_map[room_id]

    grid_scaled = grid_img.resize((canvas_w, canvas_h), Image.Resampling.NEAREST)
    base_img.alpha_composite(grid_scaled)

    draw = ImageDraw.Draw(base_img, "RGBA")

    def mm_to_canvas(pos_x_mm: float, pos_y_mm: float):
        px = ((pos_x_mm / 1000.0) - x_min) / resolution * SCALE
        py = (height - (((pos_y_mm / 1000.0) - y_min) / resolution)) * SCALE
        return px, py

    # 1. Virtual Walls and Restricted Areas (VW)
    vw = snapshot.get("VW") or {}
    for poly in vw.get("VERTX") or []:
        if len(poly) >= 3:
            pts = [mm_to_canvas(pt[0], pt[1]) for pt in poly]
            draw.polygon(pts, fill=(240, 50, 50, 60), outline=(230, 40, 40, 220), width=max(1, int(SCALE * 0.8)))

    for line in vw.get("VLINE") or []:
        if len(line) >= 2:
            p1 = mm_to_canvas(line[0][0], line[0][1])
            p2 = mm_to_canvas(line[1][0], line[1][1])
            draw.line([p1, p2], fill=(230, 40, 40, 240), width=max(2, int(SCALE)))

    # 2. Cleaning Trajectory (RTW)
    rtw = snapshot.get("RTW")
    if rtw and isinstance(rtw, list) and len(rtw) > 1:
        line_pts = []
        for pt in rtw:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                line_pts.append(mm_to_canvas(pt[0], pt[1]))
        if len(line_pts) >= 2:
            draw.line(line_pts, fill=(255, 255, 255, 210), width=max(2, int(SCALE * 0.6)))

    # 3. Room labels / badges from FLOORMAP.AREA
    floormap = snapshot.get("FLOORMAP") or {}
    for area in floormap.get("AREA") or []:
        pos = area.get("ICON_POS")
        area_id = int(area.get("ID", 0))
        if pos and len(pos) >= 2:
            ax, ay = mm_to_canvas(pos[0], pos[1])
            if 0 <= ax < canvas_w and 0 <= ay < canvas_h:
                badge_r = 12
                draw.ellipse([ax - badge_r, ay - badge_r, ax + badge_r, ay + badge_r], fill=(0, 0, 0, 150), outline=(255, 255, 255, 200), width=1)
                label_txt = str(area_id)
                draw.text((ax - 4, ay - 6), label_txt, fill=(255, 255, 255, 240))

    # 4. Dock Position (HOME_POS)
    home_pos = rt_map.get("HOME_POS") or snapshot.get("HOME_POS")
    if home_pos and len(home_pos) >= 2:
        hx, hy = mm_to_canvas(home_pos[0], home_pos[1])
        dock_r = int(7 * SCALE)
        draw.ellipse([hx - dock_r, hy - dock_r, hx + dock_r, hy + dock_r], fill=(30, 200, 100, 240), outline=(255, 255, 255, 255), width=2)
        inner_r = dock_r * 0.5
        draw.rectangle([hx - inner_r, hy - inner_r, hx + inner_r, hy + inner_r], fill=(255, 255, 255, 255))

    # 5. Robot Current Pose (RT_POSE)
    rt_pose = snapshot.get("RT_POSE") or {}
    cur_pos = rt_pose.get("CUR_POS")
    if cur_pos and len(cur_pos) >= 2:
        rx, ry = mm_to_canvas(cur_pos[0], cur_pos[1])
        bot_r = int(8 * SCALE)
        draw.ellipse([rx - bot_r - 3, ry - bot_r - 3, rx + bot_r + 3, ry + bot_r + 3], fill=(0, 122, 255, 100))
        draw.ellipse([rx - bot_r, ry - bot_r, rx + bot_r, ry + bot_r], fill=(0, 122, 255, 250), outline=(255, 255, 255, 255), width=2)
        
        theta_raw = cur_pos[2] if len(cur_pos) > 2 else 0.0
        deg = theta_raw if abs(theta_raw) <= 360 else (theta_raw / 1000.0) * (180.0 / math.pi)
        rad = math.radians(-deg)
        arrow_len = bot_r + 6
        ax = rx + arrow_len * math.cos(rad)
        ay = ry + arrow_len * math.sin(rad)
        draw.line([rx, ry, ax, ay], fill=(255, 255, 255, 255), width=3)
        draw.ellipse([ax - 3, ay - 3, ax + 3, ay + 3], fill=(255, 215, 0, 255))

    # 6. Status banner
    cur_room = int(rt_map.get("CUR_ROOMID", 0))
    sweep_area = rt_map.get("SWEEP_AREA", 0)
    info_text = f"구역 {cur_room}번 | 청소 면적: {sweep_area}m²"
    draw.rectangle([10, 10, 220, 36], fill=(0, 0, 0, 160))
    draw.text((18, 16), info_text, fill=(255, 255, 255, 240))

    buf = BytesIO()
    base_img.save(buf, format="PNG")
    return buf.getvalue()
