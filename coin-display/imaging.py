"""Image processing for coin photos.

Originals are kept untouched (apart from rotation and a size cap) so a coin can
be re-processed later with a different shape or tolerance.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

ORIGINAL_MAX = 2000   # longest edge kept for originals
DISPLAY_MAX = 1400    # longest edge of the processed image shown on screen
SHAPES = ("round", "custom", "none")


def _has_transparency(im):
    if im.mode not in ("RGBA", "LA", "PA") and "transparency" not in im.info:
        return False
    alpha = im.convert("RGBA").getchannel("A")
    return alpha.getextrema()[0] < 250


def save_original(stream, dest: Path):
    """Normalise an upload (rotation, size) and store it. Raises on bad images."""
    im = Image.open(stream)
    im = ImageOps.exif_transpose(im)
    if _has_transparency(im):
        im = im.convert("RGBA")
        im.thumbnail((ORIGINAL_MAX, ORIGINAL_MAX), Image.LANCZOS)
        im.save(dest, format="PNG")
    else:
        im = im.convert("RGB")
        im.thumbnail((ORIGINAL_MAX, ORIGINAL_MAX), Image.LANCZOS)
        im.save(dest, format="JPEG", quality=92)


def _background_alpha(im: Image.Image, tolerance: float) -> Image.Image:
    """Alpha mask that hides the photo background.

    The background colour is taken from the image border. Pixels close to that
    colour (within `tolerance`, 0-100) are removed only when they connect to the
    border, so similar colours inside the coin are kept.
    """
    arr = np.asarray(im, dtype=np.int16)
    h, w = arr.shape[:2]
    m = max(2, int(min(h, w) * 0.02))
    border = np.concatenate([
        arr[:m].reshape(-1, 3), arr[-m:].reshape(-1, 3),
        arr[:, :m].reshape(-1, 3), arr[:, -m:].reshape(-1, 3),
    ])
    bg = np.median(border, axis=0)
    dist = np.sqrt(((arr - bg) ** 2).sum(axis=2))
    cand = dist < (4 + tolerance * 2.0)

    # Border-connected test at low resolution (fast), refined at full resolution.
    k = min(1.0, 400 / max(h, w))
    sw, sh = max(1, round(w * k)), max(1, round(h * k))
    small = Image.fromarray((cand * 255).astype(np.uint8)).resize((sw, sh), Image.BOX)
    small = small.point(lambda v: 255 if v > 127 else 0)
    padded = ImageOps.expand(small, 1, fill=255)
    ImageDraw.floodfill(padded, (0, 0), 128)
    reached = padded.crop((1, 1, sw + 1, sh + 1)).point(lambda v: 255 if v == 128 else 0)
    reached = reached.filter(ImageFilter.MaxFilter(5)).resize((w, h), Image.NEAREST)
    bgmask = cand & (np.asarray(reached) > 0)

    alpha = Image.fromarray(((~bgmask) * 255).astype(np.uint8))
    # remove specks, trim the halo, soften the edge
    alpha = alpha.filter(ImageFilter.MedianFilter(5))
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1))
    return alpha


def process(src: Path, dest: Path, shape: str = "round", tolerance: float = 25):
    """Create the display image (WebP with transparency). Returns (width, height)."""
    im = Image.open(src)
    if _has_transparency(im):
        # Already cut out (e.g. a transparent PNG): trust it.
        im = im.convert("RGBA")
        alpha = im.getchannel("A")
        rgb = im.convert("RGB")
    else:
        rgb = im.convert("RGB")
        alpha = None
    rgb.thumbnail((DISPLAY_MAX, DISPLAY_MAX), Image.LANCZOS)
    if alpha is not None:
        alpha = alpha.resize(rgb.size, Image.LANCZOS)
    elif shape in ("round", "custom"):
        alpha = _background_alpha(rgb, tolerance)
        bbox = alpha.point(lambda v: 255 if v > 40 else 0).getbbox()
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) if bbox else 0
        if area < 0.02 * rgb.width * rgb.height:
            alpha = None  # detection failed; keep the whole photo
        elif shape == "round":
            # Clean edge: an ellipse fitted to the detected coin.
            ell = Image.new("L", rgb.size, 0)
            big = Image.new("L", (rgb.width * 2, rgb.height * 2), 0)
            ImageDraw.Draw(big).ellipse(
                [bbox[0] * 2 + 2, bbox[1] * 2 + 2, bbox[2] * 2 - 3, bbox[3] * 2 - 3], fill=255)
            ell = big.resize(rgb.size, Image.LANCZOS)
            alpha = ell
    if alpha is None:
        alpha = Image.new("L", rgb.size, 255)

    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    bbox = alpha.point(lambda v: 255 if v > 8 else 0).getbbox()
    if bbox:
        out = out.crop(bbox)
    out.save(dest, format="WEBP", quality=90, method=4)
    return out.size
