# Digital Challenge Coin Display

A wall display that shows a challenge coin collection in a grid. Each coin flips
between front and back every few seconds. Tap or click a coin to enlarge it with
both sides shown next to one another. Coins are added from a phone or PC.

## Run it

**Windows:** double-click `setup-windows.bat` once, then `start-windows.bat`.

**Mac:** double-click `setup-mac.command` once, then `start-mac.command`. If macOS
refuses to open them, right-click the file and choose Open. Needs Python 3 from
python.org; uses Google Chrome in kiosk mode if installed, otherwise your default browser.

**Raspberry Pi / Linux desktop:** `bash install.sh`, then reboot. The server
starts at boot and Chromium opens full-screen.

**By hand (any OS):**

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

- Display: `http://localhost:8080/`
- Admin (phone or PC on the same network): `http://<computer's address>:8080/admin`.
  With no coins yet, the display shows a QR code for this page.

## Different monitor sizes

A browser cannot detect a screen's physical size, so each screen is told once:
tap the ⚙ in the bottom-right corner of the display (or press `S`), pick the
diagonal, and check it by holding a credit card against the on-screen outline.
The size is remembered by that screen's browser. A default for all screens can
also be set on the admin page, or passed in the address: `/?diag=27`.

The layout re-computes whenever the screen or window size changes. Three layouts:

| Layout | What it does |
| --- | --- |
| Fit grid (default) | Keeps the full grid (5×5). Life-size when the screen is big enough, otherwise shrinks evenly. |
| True size | Coins always life-size. Rows and columns change to suit the screen; extra coins go to more pages. |
| Fill screen | Keeps the full grid and stretches it to fill the screen. |

With 3.5" cells, a 5×5 grid is 17.5" square: a 43" screen shows it life-size,
a 27" screen shows it at about 70%, or use *True size* for a 6×3 life-size grid.

## Touch

Tap (or click) a coin: it enlarges with front and back side by side, plus its
name and notes. Tap anywhere to close; it closes itself after 45 seconds.
Any touchscreen monitor that works as a normal touch input device will do.

## Coins

- Enter each coin's real width in inches; that drives life-size scaling.
- Coins too big for one cell automatically take more cells; this can be set by hand.
- Shape: *Round* (clean circular edge), *Odd shape* (background cut out, with a
  tolerance slider in Edit), or *Use photo as-is*. Transparent PNGs are kept as they are.
- Photograph coins straight-on against a plain, contrasting background.
- Edit, reorder, hide, delete, or replace one side from the admin page.

## Data and backup

Everything lives in the `data` folder (photos plus `coins.json`). The admin
page's **Download backup** gives a zip of it; to restore, unzip into `data`.

There is no password: anyone on your network can open the admin page.

## Testing

`python tools/make_test_coins.py 23` adds synthetic coins.
