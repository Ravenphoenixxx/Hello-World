"""Digital challenge coin display - server.

Run:  python app.py          (serves on http://0.0.0.0:8080)
  /        full-screen display (kiosk)
  /admin   upload / manage page for phones and PCs
"""
import io
import json
import os
import re
import socket
import threading
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file, send_from_directory

import imaging

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("COIN_DATA", BASE / "data"))
ORIG = DATA / "originals"
IMG = DATA / "images"
DB = DATA / "coins.json"
PORT = int(os.environ.get("COIN_PORT", "8080"))

DEFAULT_SETTINGS = {
    "title": "",
    "show_labels": False,
    "theme": "felt",            # felt | walnut | black | navy | slate | light
    "flip_style": "wave",       # wave | all | random | checker
    "flip_interval": 5,         # seconds
    "cols": 5,
    "rows": 5,
    "cell_in": 3.5,             # grid cell size in inches
    "scale_mode": "fit",        # fit | true | fill   (see README)
    "diagonal_in": 0,           # default screen diagonal; 0 = not set
    "page_seconds": 30,
}
LIMITS = {
    "flip_interval": (2, 120), "cols": (1, 12), "rows": (1, 12),
    "cell_in": (1, 8), "diagonal_in": (0, 150), "page_seconds": (5, 3600),
}
CHOICES = {
    "theme": ("felt", "walnut", "black", "navy", "slate", "light"),
    "flip_style": ("wave", "all", "random", "checker"),
    "scale_mode": ("fit", "true", "fill"),
}

app = Flask(__name__, static_folder=str(BASE / "static"), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024
_lock = threading.RLock()
ID_RE = re.compile(r"^[0-9a-f]{12}$")


# ---------------------------------------------------------------- storage
def load():
    for d in (DATA, ORIG, IMG):
        d.mkdir(parents=True, exist_ok=True)
    db = {"version": 1, "settings": {}, "coins": []}
    if DB.exists():
        try:
            db.update(json.loads(DB.read_text("utf-8")))
        except (ValueError, OSError):
            pass
    db["settings"] = {**DEFAULT_SETTINGS, **db.get("settings", {})}
    return db


def save(db):
    db["version"] = int(db.get("version", 0)) + 1
    tmp = DB.with_suffix(".tmp")
    tmp.write_text(json.dumps(db, indent=1), "utf-8")
    os.replace(tmp, DB)


def find(db, cid):
    for c in db["coins"]:
        if c["id"] == cid:
            return c
    abort(404)


def clean_settings(incoming, current):
    out = dict(current)
    for key, default in DEFAULT_SETTINGS.items():
        if key not in incoming:
            continue
        val = incoming[key]
        try:
            if isinstance(default, bool):
                val = bool(val)
            elif isinstance(default, int) and key != "diagonal_in":
                val = int(float(val))
            elif isinstance(default, (int, float)):
                val = float(val)
            else:
                val = str(val)[:80]
        except (TypeError, ValueError):
            continue
        if key in LIMITS:
            lo, hi = LIMITS[key]
            val = min(hi, max(lo, val))
        if key in CHOICES and val not in CHOICES[key]:
            continue
        out[key] = val
    return out


def apply_fields(coin, data):
    """Copy validated editable fields onto a coin. Returns True if images need reprocessing."""
    redo = False
    if "name" in data:
        coin["name"] = str(data["name"]).strip()[:80]
    if "notes" in data:
        coin["notes"] = str(data["notes"]).strip()[:300]
    if "hidden" in data:
        coin["hidden"] = str(data["hidden"]).lower() in ("1", "true", "on", "yes")
    if "width_in" in data:
        try:
            coin["width_in"] = round(min(20, max(0.5, float(data["width_in"]))), 2)
        except (TypeError, ValueError):
            pass
    for key in ("span_cols", "span_rows"):
        if key in data:
            try:
                coin[key] = min(6, max(0, int(data[key])))  # 0 = automatic
            except (TypeError, ValueError):
                pass
    if "shape" in data and data["shape"] in imaging.SHAPES and data["shape"] != coin.get("shape"):
        coin["shape"] = data["shape"]
        redo = True
    if "tolerance" in data:
        try:
            tol = min(100, max(0, int(float(data["tolerance"]))))
            if tol != coin.get("tolerance"):
                coin["tolerance"] = tol
                redo = True
        except (TypeError, ValueError):
            pass
    return redo


def orig_path(cid, side):
    return ORIG / f"{cid}_{side}.img"


def img_path(cid, side):
    return IMG / f"{cid}_{side}.webp"


def reprocess(coin):
    for side in ("front", "back"):
        src = orig_path(coin["id"], side)
        if not src.exists():
            continue
        w, h = imaging.process(src, img_path(coin["id"], side), coin["shape"], coin["tolerance"])
        if side == "front":
            coin["aspect"] = round(h / w, 4)
    coin["has_back"] = orig_path(coin["id"], "back").exists()
    coin["v"] = coin.get("v", 0) + 1


def store_upload(coin, side, file):
    dest = orig_path(coin["id"], side)
    tmp = dest.with_suffix(".tmp")
    try:
        imaging.save_original(file.stream, tmp)
    except Exception:
        tmp.unlink(missing_ok=True)
        abort(400, "That file could not be read as an image.")
    os.replace(tmp, dest)


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def admin_url():
    return f"http://{lan_ip()}:{PORT}/admin"


# ---------------------------------------------------------------- pages
@app.get("/")
def display_page():
    return send_from_directory(app.static_folder, "display.html")


@app.get("/admin")
def admin_page():
    return send_from_directory(app.static_folder, "admin.html")


@app.after_request
def no_cache_pages(resp):
    if request.path in ("/", "/admin") or request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(413)
def json_error(err):
    return jsonify(error=getattr(err, "description", str(err))), err.code


# ---------------------------------------------------------------- api
@app.get("/api/state")
def api_state():
    with _lock:
        db = load()
    return jsonify(version=db["version"], settings=db["settings"], coins=db["coins"],
                   admin_url=admin_url())


@app.get("/api/version")
def api_version():
    with _lock:
        return jsonify(version=load()["version"])


@app.put("/api/settings")
def api_settings():
    with _lock:
        db = load()
        db["settings"] = clean_settings(request.get_json(force=True) or {}, db["settings"])
        save(db)
        return jsonify(db["settings"])


@app.post("/api/coins")
def api_add():
    front = request.files.get("front")
    if not front or not front.filename:
        abort(400, "A photo of the front is required.")
    coin = {"id": uuid.uuid4().hex[:12], "name": "", "notes": "", "width_in": 2.0,
            "shape": "round", "tolerance": 25, "hidden": False,
            "span_cols": 0, "span_rows": 0, "aspect": 1.0, "has_back": False, "v": 0,
            "added": datetime.now().isoformat(timespec="seconds")}
    apply_fields(coin, request.form)
    with _lock:
        load()  # makes sure the data folders exist
        store_upload(coin, "front", front)
        back = request.files.get("back")
        if back and back.filename:
            store_upload(coin, "back", back)
        reprocess(coin)
        db = load()
        db["coins"].append(coin)
        save(db)
    return jsonify(coin), 201


@app.patch("/api/coins/<cid>")
def api_edit(cid):
    with _lock:
        db = load()
        coin = find(db, cid)
        if apply_fields(coin, request.get_json(force=True) or {}):
            reprocess(coin)
        save(db)
        return jsonify(coin)


@app.post("/api/coins/<cid>/image/<side>")
def api_replace(cid, side):
    if side not in ("front", "back"):
        abort(404)
    file = request.files.get("file")
    if not file or not file.filename:
        abort(400, "No image was sent.")
    with _lock:
        db = load()
        coin = find(db, cid)
        store_upload(coin, side, file)
        reprocess(coin)
        save(db)
        return jsonify(coin)


@app.delete("/api/coins/<cid>")
def api_delete(cid):
    with _lock:
        db = load()
        coin = find(db, cid)
        db["coins"].remove(coin)
        save(db)
        for side in ("front", "back"):
            orig_path(cid, side).unlink(missing_ok=True)
            img_path(cid, side).unlink(missing_ok=True)
    return jsonify(ok=True)


@app.post("/api/order")
def api_order():
    ids = (request.get_json(force=True) or {}).get("ids", [])
    with _lock:
        db = load()
        by_id = {c["id"]: c for c in db["coins"]}
        ordered = [by_id.pop(i) for i in ids if i in by_id]
        db["coins"] = ordered + list(by_id.values())
        save(db)
    return jsonify(ok=True)


@app.get("/img/<cid>/<side>")
def api_image(cid, side):
    if not ID_RE.match(cid) or side not in ("front", "back"):
        abort(404)
    path = img_path(cid, side)
    if not path.exists():
        abort(404)
    resp = send_file(path, mimetype="image/webp")
    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"  # URL carries ?v=
    return resp


@app.get("/api/backup")
def api_backup():
    buf = io.BytesIO()
    with _lock, zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        load()
        for path in sorted(DATA.rglob("*")):
            if path.is_file() and path.suffix != ".tmp":
                z.write(path, path.relative_to(DATA).as_posix())
    buf.seek(0)
    name = f"coin-display-backup-{datetime.now():%Y%m%d-%H%M}.zip"
    return send_file(buf, mimetype="application/zip", as_attachment=True, download_name=name)


if __name__ == "__main__":
    from waitress import serve
    load()
    print(f"Display:  http://localhost:{PORT}/")
    print(f"Admin:    {admin_url()}")
    serve(app, host="0.0.0.0", port=PORT, threads=8)
