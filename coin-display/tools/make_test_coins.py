"""Fill the app with synthetic coins for testing:  python tools/make_test_coins.py [count]"""
import io
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app  # noqa: E402

random.seed(7)
METALS = [((212, 175, 55), (120, 90, 20)), ((192, 192, 200), (90, 90, 100)),
          ((184, 115, 51), (95, 50, 20)), ((60, 60, 66), (200, 170, 80)), ((150, 30, 30), (230, 200, 120))]
TABLES = [(238, 236, 230), (40, 44, 52), (120, 150, 190), (225, 215, 195)]


def outline(shape, cx, cy, rx, ry):
    if shape == "shield":
        return [(cx - rx, cy - ry), (cx + rx, cy - ry), (cx + rx, cy + ry * .2), (cx, cy + ry), (cx - rx, cy + ry * .2)]
    if shape == "star":
        pts = []
        for i in range(10):
            r = 1 if i % 2 == 0 else .5
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)))
        return pts
    if shape == "tag":
        return [(cx - rx, cy - ry), (cx + rx, cy - ry), (cx + rx, cy + ry), (cx - rx, cy + ry)]
    return None


def photo(shape, aspect, metal, table, text, side):
    w, h = 900, int(900 * max(1, aspect))
    im = Image.new("RGB", (w, h), table)
    px = im.load()
    for _ in range(9000):  # a little texture so the background is not perfectly flat
        x, y = random.randrange(w), random.randrange(h)
        px[x, y] = tuple(max(0, min(255, c + random.randint(-7, 7))) for c in table)
    d = ImageDraw.Draw(im)
    cx, cy = w / 2 + random.randint(-30, 30), h / 2 + random.randint(-30, 30)
    rx = 330
    ry = rx * aspect
    fill, ink = metal if side == "front" else (tuple(int(c * .8) for c in metal[0]), metal[1])
    pts = outline(shape, cx, cy, rx, ry)
    if pts:
        d.polygon(pts, fill=fill, outline=ink, width=14)
    else:
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=fill, outline=ink, width=16)
        d.ellipse([cx - rx * .8, cy - ry * .8, cx + rx * .8, cy + ry * .8], outline=ink, width=6)
    font = ImageFont.load_default(size=74)
    d.text((cx, cy - 30), text, fill=ink, font=font, anchor="mm")
    d.text((cx, cy + 60), side.upper(), fill=ink, font=ImageFont.load_default(size=44), anchor="mm")
    im = im.filter(ImageFilter.GaussianBlur(.6))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    buf.seek(0)
    return buf


def main(count=23):
    client = app.app.test_client()
    specs = [("round", 1.0, 2.0)] * 3 + [("round", 1.0, 1.75), ("shield", 1.2, 2.5), ("round", 1.0, 3.0),
             ("star", 1.0, 2.75), ("round", 1.0, 4.5), ("tag", 0.55, 5.0), ("tag", 1.9, 2.0), ("round", 1.0, 1.5)]
    for i in range(count):
        shape, aspect, width = specs[i % len(specs)]
        metal, table = METALS[i % len(METALS)], TABLES[i % len(TABLES)]
        data = {"name": f"Test coin {i + 1} ({shape})", "width_in": str(width),
                "shape": "round" if shape == "round" else "custom", "notes": f"{width} in wide synthetic coin",
                "front": (photo(shape, aspect, metal, table, f"No. {i + 1}", "front"), "f.jpg")}
        if i % 9 != 8:  # some coins have no back photo
            data["back"] = (photo(shape, aspect, metal, table, f"No. {i + 1}", "back"), "b.jpg")
        r = client.post("/api/coins", data=data, content_type="multipart/form-data")
        assert r.status_code == 201, r.get_data(as_text=True)
    print(f"added {count} coins to {app.DATA}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 23)
