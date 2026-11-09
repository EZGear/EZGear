#!/usr/bin/env python3
"""
Desktop Pet — ekranda yuradigan personajlar (shimeji uslubida).

Har bir personaj — img/<Ism>/ papkasi. Ichiga quyidagilardan birini qo'ying:
  * bitta oddiy rasm (masalan Eren.png) — dastur fonni o'zi olib tashlaydi
    va undan yurish, o'tirish, yotish, osilish kadrlarini o'zi yasaydi;
  * yoki standart Shimeji to'plami: shime1.png ... shime46.png.
Rasm topilmasa, dastur vaqtinchalik oddiy shakllarni chizadi.

Boshqarish:
  * Sichqoncha chap tugmasi bilan ushlab sudrash va otish mumkin.
  * O'ng tugma — menyu (personaj qo'shish, o'tirg'izish, yopish, chiqish).
"""

import json
import os
import random
import sys
import time
import tkinter as tk

try:
    from PIL import Image, ImageDraw, ImageTk
except ImportError:  # pragma: no cover - faqat foydalanuvchiga xabar
    root = tk.Tk()
    root.withdraw()
    from tkinter import messagebox

    messagebox.showerror(
        "Desktop Pet",
        "Pillow kutubxonasi o'rnatilmagan.\n\n"
        "Buyruq qatorida bajaring:\n    pip install pillow",
    )
    sys.exit(1)


IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"

if getattr(sys, "frozen", False):  # PyInstaller bilan yig'ilgan .exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

IMG_DIR = os.path.join(BASE_DIR, "img")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

KEY_HEX = "#ff00fe"  # Windows'da shu rang shaffof bo'ladi
KEY_RGB = (255, 0, 254)

TICK_MS = 40  # ~25 kadr/soniya
GRAVITY = 1.2
MAX_FALL = 28
MAX_INDEX = 60

DEFAULT_SETTINGS = {
    "scale": 1.0,
    "height": 160,  # bitta rasmdan yasalganda personaj balandligi (piksel)
    "max_pets": 20,
    "characters": {"Eren": 1, "Mikasa": 1},
    # Mikasa ko'pincha Erenning orqasidan yuradi
    "follow": {"Mikasa": "Eren"},
    # kim o'tiradi, kim uning tizzasiga boshini qo'yib yotadi
    "lap": {"sitter": "Mikasa", "lier": "Eren"},
    # har necha daqiqada soatni aytadi (0 = o'chirilgan)
    "clock_every_min": 5,
    # kompyuter yoqilganda (Windows'ga kirganda) avtomatik ishga tushish
    "autostart": True,
}

# Shimeji rasm raqamlari bo'yicha animatsiyalar: (rasm raqami, necha tik)
ANIM = {
    "stand": [(1, 1)],
    # 41-43: yon tomonga burilgan yurish kadrlari (bo'lmasa 1-3 ishlatiladi)
    "walk": [(41, 6), (42, 6), (41, 6), (43, 6)],
    "run": [(41, 3), (42, 3), (41, 3), (43, 3)],
    "fall": [(4, 1)],
    "jump": [(22, 1)],
    "bounce": [(18, 4), (19, 4)],
    "sit": [(11, 1)],
    "sit_look": [(26, 1)],
    "spin_head": [(26, 5), (15, 5), (27, 5), (16, 5), (28, 5), (17, 5)],
    "dangle": [(31, 8), (32, 8), (31, 8), (33, 8)],
    "sprawl": [(21, 1)],
    "creep": [(20, 14), (21, 14)],
    "wall_hold": [(13, 1)],
    "wall_climb": [(14, 8), (12, 8), (13, 8)],
    "ceiling": [(25, 8), (23, 8), (24, 8)],
    "drag_resist": [(5, 6), (6, 6)],
    "lap_sit": [(11, 1)],
    "lap_lie": [(40, 1)],
}

# Biror rasm yo'q bo'lsa, o'rniga qaysi biri ishlatiladi
FALLBACK = {
    2: 1, 3: 1, 4: 1, 5: 4, 6: 5, 7: 5, 8: 5, 9: 7, 10: 8, 11: 1,
    12: 13, 13: 14, 14: 4, 15: 26, 16: 26, 17: 26, 18: 1, 19: 18,
    20: 21, 21: 11, 22: 4, 23: 24, 24: 25, 25: 4, 26: 11, 27: 26,
    28: 26, 30: 11, 31: 11, 32: 31, 33: 31, 40: 21, 41: 1, 42: 2, 43: 3,
}

PLACEHOLDER_INDICES = sorted(set(FALLBACK) | {1})


# --------------------------------------------------------------------------
# Sozlamalar va ekran
# --------------------------------------------------------------------------

def load_settings():
    settings = json.loads(json.dumps(DEFAULT_SETTINGS))
    if os.path.isfile(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                user = json.load(f)
            if isinstance(user, dict):
                settings.update(user)
        except (OSError, ValueError):
            pass
    return settings


def save_setting(key, value):
    """settings.json ichidagi bitta qiymatni o'zgartirib saqlaydi."""
    data = {}
    if os.path.isfile(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {}
    if not isinstance(data, dict):
        data = {}
    data[key] = value
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError:
        pass


# --------------------------------------------------------------------------
# Windows: avtomatik ishga tushish va bitta nusxa
# --------------------------------------------------------------------------

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "DesktopPet"


def autostart_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.isfile(pyw):
        exe = pyw  # qora oyna (konsol) chiqmasligi uchun
    return f'"{exe}" "{os.path.abspath(__file__)}"'


def get_autostart():
    if not IS_WIN:
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            value, _ = winreg.QueryValueEx(k, APP_NAME)
            return bool(value)
    except OSError:
        return False


def set_autostart(on):
    """Windows'ga kirganda ishga tushadiganlar ro'yxatiga qo'shadi/olib tashlaydi."""
    if not IS_WIN:
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, autostart_command())
            else:
                try:
                    winreg.DeleteValue(k, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


_MUTEX = None


def already_running():
    """Dastur allaqachon ochiq bo'lsa True (ikki marta ochilib qolmasligi uchun)."""
    global _MUTEX
    if not IS_WIN:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateMutexW.restype = wintypes.HANDLE
        k32.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
        _MUTEX = k32.CreateMutexW(None, False, "Local\\DesktopPet_Eren_Mikasa")
        return ctypes.get_last_error() == 183  # ERROR_ALREADY_EXISTS
    except Exception:
        return False


def enable_dpi_awareness():
    if not IS_WIN:
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def get_work_area(root):
    """Vazifalar paneli (taskbar)siz ekran maydoni: (chap, yuqori, o'ng, past)."""
    if IS_WIN:
        try:
            import ctypes
            from ctypes import wintypes

            rect = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(rect), 0):
                return rect.left, rect.top, rect.right, rect.bottom
        except Exception:
            pass
    top = 25 if IS_MAC else 0
    return 0, top, root.winfo_screenwidth(), root.winfo_screenheight()


# --------------------------------------------------------------------------
# Rasmlar
# --------------------------------------------------------------------------

def _palette(name):
    n = name.lower()
    if "eren" in n:
        # jigarrang soch, to'q ko'k maktab formasi, yashil galstuk
        return (95, 60, 40), (40, 52, 90), (40, 140, 90), (255, 224, 196)
    if "mikasa" in n:
        # qora soch, to'q ko'k forma, qizil sharf
        return (25, 25, 30), (40, 52, 90), (200, 30, 40), (255, 230, 210)
    rnd = random.Random(n)
    rc = lambda: tuple(rnd.randint(30, 220) for _ in range(3))  # noqa: E731
    return rc(), rc(), rc(), (255, 226, 200)


def _draw_figure(name, legs="stand", arms="down", head_y=30):
    """Chapga qaragan oddiy odamcha (128x128)."""
    S = 128
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    hair, coat, accent, skin = _palette(name)
    ol = (35, 28, 28, 255)
    cx = 64
    hy = head_y
    body_top, body_bot = hy + 17, hy + 55

    # oyoqlar
    if legs == "sit":
        d.rectangle((cx - 30, body_bot - 12, cx + 6, body_bot), fill=(30, 30, 40), outline=ol)
        d.rectangle((cx - 34, body_bot - 12, cx - 26, body_bot + 6), fill=(30, 30, 40), outline=ol)
    else:
        offs = {"stand": (0, 0), "walkA": (-8, 6), "walkB": (6, -8), "dangle": (-4, 4)}[legs]
        d.rectangle((cx - 13 + offs[0], body_bot, cx - 3 + offs[0], body_bot + 30),
                    fill=(30, 30, 40), outline=ol)
        d.rectangle((cx + 3 + offs[1], body_bot, cx + 13 + offs[1], body_bot + 30),
                    fill=(30, 30, 40), outline=ol)

    # qo'llar
    if arms == "up":
        d.rectangle((cx - 22, hy - 28, cx - 14, body_top + 14), fill=coat, outline=ol)
        d.rectangle((cx + 14, hy - 28, cx + 22, body_top + 14), fill=coat, outline=ol)
    elif arms == "forward":
        d.rectangle((cx - 44, body_top + 6, cx - 10, body_top + 14), fill=coat, outline=ol)
    else:
        d.rectangle((cx - 22, body_top + 2, cx - 14, body_bot - 4), fill=coat, outline=ol)
        d.rectangle((cx + 14, body_top + 2, cx + 22, body_bot - 4), fill=coat, outline=ol)

    # tana
    d.rounded_rectangle((cx - 16, body_top, cx + 16, body_bot), radius=6, fill=coat, outline=ol)
    d.polygon([(cx - 4, body_top), (cx + 4, body_top), (cx, body_top + 18)], fill=accent)

    # bosh
    d.ellipse((cx - 18, hy - 18, cx + 18, hy + 18), fill=skin, outline=ol)
    d.chord((cx - 19, hy - 20, cx + 19, hy + 12), 180, 360, fill=hair, outline=ol)
    d.rectangle((cx + 4, hy - 6, cx + 19, hy + 14), fill=hair)  # orqa soch
    d.ellipse((cx - 11, hy, cx - 6, hy + 6), fill=(30, 30, 30))  # ko'z (chapga qaraydi)
    if "mikasa" in name.lower():
        d.rectangle((cx - 17, hy + 14, cx + 17, hy + 22), fill=accent, outline=ol)  # sharf
    return img


def make_placeholder(idx, name):
    """Haqiqiy rasm bo'lmaganda ishlatiladigan vaqtinchalik shakl."""
    if idx in (2,):
        return _draw_figure(name, legs="walkA")
    if idx in (3,):
        return _draw_figure(name, legs="walkB")
    if idx in (4, 22):
        return _draw_figure(name, arms="up", legs="dangle")
    if idx in (5, 6, 7, 8, 9, 10):
        tilt = {5: 0, 6: 4, 7: 12, 8: -12, 9: 22, 10: -22}[idx]
        fig = _draw_figure(name, arms="up", legs="dangle", head_y=40)
        return fig.rotate(tilt, center=(64, 10), resample=Image.BICUBIC)
    if idx in (11, 15, 16, 17, 26, 27, 28, 30, 31, 32, 33):
        return _draw_figure(name, legs="sit", head_y=58)
    if idx in (12, 13, 14):
        return _draw_figure(name, arms="up", legs="stand" if idx != 14 else "walkA", head_y=38)
    if idx in (23, 24, 25):
        # qo'llari bilan shiftga osilib turadi
        return _draw_figure(name, arms="up", legs="dangle" if idx != 24 else "walkA", head_y=30)
    if idx in (18,):
        return _draw_figure(name, head_y=36)
    if idx in (19, 20, 21):
        fig = _draw_figure(name, arms="forward" if idx == 20 else "down")
        lying = fig.rotate(90, resample=Image.BICUBIC)  # boshi chapda
        out = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        out.paste(lying, (0, 34), lying)
        return out
    return _draw_figure(name)


def keyed(img):
    """Shaffof PNG'ni Windows uchun 'kalit rang' foniga tayyorlash."""
    img = img.convert("RGBA")
    bg = Image.new("RGB", img.size, KEY_RGB)
    mask = img.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
    bg.paste(img.convert("RGB"), (0, 0), mask)
    return bg


# --------------------------------------------------------------------------
# Bitta rasmdan animatsiya yasash
# --------------------------------------------------------------------------

PICTURE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")


def remove_background(img):
    """Shaffof bo'lmagan rasmda chetlardan boshlab bir xil fonni o'chiradi."""
    from collections import deque

    img = img.convert("RGBA")
    if img.getchannel("A").getextrema()[0] < 250:
        return img  # allaqachon shaffof
    W, H = img.size
    px = img.load()
    bg = bytearray(W * H)

    def diff(a, b):
        return max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))

    q = deque()
    for x in range(W):
        q.append((x, 0, px[x, 0]))
        q.append((x, H - 1, px[x, H - 1]))
    for y in range(H):
        q.append((0, y, px[0, y]))
        q.append((W - 1, y, px[W - 1, y]))
    while q:
        x, y, prev = q.popleft()
        i = y * W + x
        if bg[i]:
            continue
        c = px[x, y]
        if diff(c, prev) > 14:
            continue
        bg[i] = 1
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < W and 0 <= ny < H and not bg[ny * W + nx]:
                q.append((nx, ny, c))
    for y in range(H):
        row = y * W
        for x in range(W):
            if bg[row + x]:
                px[x, y] = (0, 0, 0, 0)
    return img


def load_picture(folder):
    """Papkadagi birinchi oddiy rasmni (shime*.png emas) qaytaradi."""
    if not folder or not os.path.isdir(folder):
        return None
    for fn in sorted(os.listdir(folder)):
        low = fn.lower()
        if low.endswith(PICTURE_EXT) and not low.startswith("shime"):
            try:
                img = Image.open(os.path.join(folder, fn))
                img.seek(0)
                img = img.convert("RGBA")
            except Exception:
                continue
            if max(img.size) > 900:  # katta rasmni kichraytirib, tezroq ishlash
                k = 900 / max(img.size)
                img = img.resize((int(img.width * k), int(img.height * k)), Image.LANCZOS)
            img = remove_background(img)
            box = img.getbbox()
            return img.crop(box) if box else None
    return None


def frames_from_picture(pic, height):
    """Bitta rasmdan shimeji raqamlaridagi kadrlarni yasaydi (kvadrat S x S)."""
    k = height / pic.height
    base = pic.resize((max(1, int(pic.width * k)), height), Image.LANCZOS)
    S = height
    bw, bh = base.size

    def canvas():
        return Image.new("RGBA", (S, S), (0, 0, 0, 0))

    def place(img, dy=0):
        c = canvas()
        c.paste(img, ((S - img.width) // 2, S - img.height - dy), img)
        return c

    def rot_bottom(img, ang, dy=0):
        # oyoqlar (pastki markaz) atrofida aylantirish
        pad = Image.new("RGBA", (2 * S, 2 * img.height), (0, 0, 0, 0))
        pad.paste(img, (S - img.width // 2, 0), img)
        r = pad.rotate(ang, center=(S, img.height), resample=Image.BICUBIC)
        return place(r.crop((S // 2, 0, S // 2 + S, img.height)), dy)

    def rot_top(img, ang):
        # ushlab olingan joy (bosh tepasi) atrofida tebranish
        c = place(img)
        top_y = S - img.height
        return c.rotate(ang, center=(S / 2, top_y + 4), resample=Image.BICUBIC)

    def squash(img, sx, sy):
        return place(img.resize((max(1, int(img.width * sx)), max(1, int(img.height * sy))),
                                Image.LANCZOS))

    def sitting(img):
        cut = int(img.height * 0.62)
        top = img.crop((0, 0, img.width, cut))
        legs = img.crop((0, cut, img.width, img.height))
        legs = legs.resize((legs.width, max(1, int(legs.height * 0.35))), Image.LANCZOS)
        out = Image.new("RGBA", (img.width, top.height + legs.height), (0, 0, 0, 0))
        out.paste(top, (0, 0), top)
        out.paste(legs, (0, top.height), legs)
        return out

    def lying(img, lift=0, ang=0):
        r = img.rotate(90 + ang, expand=True, resample=Image.BICUBIC)  # bosh chapda
        r = r.crop(r.getbbox())
        if r.width > S:
            r = r.resize((S, max(1, int(r.height * S / r.width))), Image.LANCZOS)
        return place(r, lift)

    def crotch_y(img):
        """Oyoqlar orasidagi bo'shliq boshlanadigan qator (son boshi)."""
        a = img.getchannel("A").load()
        cx = img.width // 2
        y = img.height - 1
        while y > img.height * 0.5 and not any(a[x, y] for x in range(cx - 1, cx + 2)):
            y -= 1
        return y + 1

    def body_end_y(img):
        """Tana (kurtka/yubka) tugab, ingichka oyoqlar boshlanadigan qator."""
        a = img.getchannel("A").load()
        x0, x1 = int(img.width * 0.2), int(img.width * 0.8)
        count = lambda y: sum(1 for x in range(x0, x1) if a[x, y])  # noqa: E731
        ref = count(int(img.height * 0.5)) or 1
        for y in range(int(img.height * 0.55), img.height):
            if count(y) < ref * 0.6:
                return y
        return img.height

    hip = min(crotch_y(base), body_end_y(base), int(bh * 0.8))

    def stride(img, ang):
        """Oyoqlarni son atrofida oldinga-orqaga tashlash."""
        mid = img.width // 2
        out = Image.new("RGBA", (img.width * 2, img.height + 4), (0, 0, 0, 0))
        ox = img.width // 2
        body = img.copy()
        body.paste((0, 0, 0, 0), (0, hip, img.width, img.height))
        for x0, x1, a in ((0, mid, ang), (mid, img.width, -ang)):
            leg = img.crop((x0, hip, x1, img.height))
            pad = Image.new("RGBA", (leg.width * 3, leg.height * 2), (0, 0, 0, 0))
            pad.paste(leg, (leg.width, 0), leg)
            r = pad.rotate(a, center=(leg.width * 1.5, 0), resample=Image.BICUBIC)
            out.paste(r, (ox + x0 - leg.width, hip), r)
        out.paste(body, (ox, 0), body)
        box = out.getbbox()
        return out.crop((0, 0, out.width, box[3]))

    def turned(img, lean=4):
        """Tanani chap tomonga burilgandek ko'rsatish (uzoq tomoni kichikroq)."""
        w, h = img.size
        nw = max(1, int(w * 0.8))
        sq = img.resize((nw, h), Image.LANCZOS)
        d = int(h * 0.05)
        sq = sq.transform((nw, h), Image.QUAD, (0, -d, 0, h, nw, h, nw, 0),
                          resample=Image.BICUBIC)
        box = sq.getbbox()
        sq = sq.crop(box) if box else sq
        return rot_bottom(sq, lean)

    sit = sitting(base)
    f = {}
    f[41] = turned(stride(base, 0))
    f[42] = turned(stride(base, -16), 6)
    f[43] = turned(stride(base, 16), 6)
    f[1] = place(base)
    f[2] = rot_bottom(base, 5, 3)
    f[3] = rot_bottom(base, -5, 3)
    f[4] = rot_bottom(base, 10)
    f[5] = rot_top(base, 3)
    f[6] = rot_top(base, -3)
    f[7] = rot_top(base, -12)
    f[9] = rot_top(base, -22)
    f[8] = rot_top(base, 12)
    f[10] = rot_top(base, 22)
    f[11] = place(sit)
    f[12] = rot_bottom(base, 3, 2)
    f[13] = place(base)
    f[14] = rot_bottom(base, -3, 2)
    f[18] = squash(base, 1.12, 0.84)
    f[19] = squash(base, 1.05, 0.93)
    f[20] = lying(base, 2, 4)
    f[21] = lying(base)
    f[22] = squash(base, 0.94, 1.06)
    # shiftda boshi pastga qarab yuradi
    f[25] = f[41].transpose(Image.FLIP_TOP_BOTTOM)
    f[23] = f[42].transpose(Image.FLIP_TOP_BOTTOM)
    f[24] = f[43].transpose(Image.FLIP_TOP_BOTTOM)
    f[26] = rot_bottom(sit, -3)
    for i, a in ((15, 6), (16, -6), (17, 3), (27, -3), (28, 6)):
        f[i] = rot_bottom(sit, a)
    f[30] = place(sit)
    f[31] = place(sit)
    f[32] = place(sit, 2)
    f[33] = rot_bottom(sit, 2, 1)
    f[40] = lying(base, 0, -6)  # boshi biroz ko'tarilgan (tizzada)
    return f, bw / 2


class SpriteSet:
    def __init__(self, name, folder, scale, use_key, height=160):
        self.name = name
        raw = {}
        self.edge_half = None
        if folder and os.path.isdir(folder):
            for i in range(1, MAX_INDEX + 1):
                p = os.path.join(folder, f"shime{i}.png")
                if os.path.isfile(p):
                    try:
                        raw[i] = Image.open(p).convert("RGBA")
                    except Exception:
                        pass
        if not raw:
            pic = load_picture(folder)
            if pic is not None:
                h = max(24, int(height * (scale or 1.0)))
                raw, self.edge_half = frames_from_picture(pic, h)
                scale = 1.0
        self.placeholder = not raw
        if not raw:
            raw = {i: make_placeholder(i, name) for i in PLACEHOLDER_INDICES}
            self.edge_half = 24 * (scale or 1.0)

        base = raw.get(1) or raw[min(raw)]
        w, h = base.size
        if scale and abs(scale - 1.0) > 1e-3:
            w, h = max(8, int(w * scale)), max(8, int(h * scale))
        self.w, self.h = w, h
        if self.edge_half is None:
            self.edge_half = w / 2

        self.left, self.right = {}, {}
        self.tops = {}
        for i, im in raw.items():
            if im.size != (w, h):
                im = im.resize((w, h), Image.LANCZOS)
            box = im.getbbox()
            self.tops[i] = box[1] if box else 0
            fl = im.transpose(Image.FLIP_LEFT_RIGHT)
            if use_key:
                im, fl = keyed(im), keyed(fl)
            self.left[i] = ImageTk.PhotoImage(im)
            self.right[i] = ImageTk.PhotoImage(fl)

    def resolve(self, idx):
        for _ in range(8):
            if idx in self.left:
                break
            idx = FALLBACK.get(idx, 1)
        if idx not in self.left:
            idx = 1 if 1 in self.left else min(self.left)
        return idx

    def top(self, idx):
        return self.tops.get(self.resolve(idx), 0)

    def frame(self, idx, facing_right):
        idx = self.resolve(idx)
        # Shimeji rasmlari chapga qaragan bo'ladi
        return (self.right if facing_right else self.left)[idx]


# --------------------------------------------------------------------------
# Personaj
# --------------------------------------------------------------------------

FLOOR_STATES = {"stand", "walk", "run", "sit", "sit_look", "spin_head",
                "dangle", "sprawl", "creep", "follow", "bounce"}
SCENE_READY = FLOOR_STATES - {"bounce"}


class Bubble:
    """Personaj tepasida chiqadigan gap pufakchasi."""

    def __init__(self, app, text, seconds):
        self.until = time.time() + seconds
        self.win = tk.Toplevel(app.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.config(bg="#3a3a46")
        font = ("Segoe UI", 12, "bold") if IS_WIN else ("Helvetica", 12, "bold")
        self.label = tk.Label(self.win, text=text, bg="#fffaf0", fg="#2b2b33",
                              font=font, padx=10, pady=4)
        self.label.pack(padx=2, pady=2)
        self.win.update_idletasks()
        self.w = self.win.winfo_reqwidth()
        self.h = self.win.winfo_reqheight()
        self.pos = None

    def move(self, x, y):
        pos = (int(x - self.w / 2), int(y - self.h))
        if pos != self.pos:
            self.win.geometry(f"+{pos[0]}+{pos[1]}")
            self.pos = pos

    def destroy(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


class Pet:
    def __init__(self, app, sprites, x=None):
        self.app = app
        self.sp = sprites
        self.name = sprites.name
        L, T, R, B = app.area
        w = sprites.edge_half * 2
        self.x = x if x is not None else random.uniform(L + w, max(L + w + 1, R - w))
        self.y = T  # ekranning tepasidan tushib keladi
        self.vx = random.uniform(-2, 2)
        self.vy = 0.0
        self.right = random.random() < 0.5
        self.dragging = False
        self.jumping = False
        self.target_x = self.x
        self.climb_after = False
        self.side = "left"
        self.foot_x = self.x
        self.mouse_hist = []
        self.cur_img = None
        self.cur_geom = None
        self.cur_idx = 1
        self.partner = None
        self.bubble = None
        self.set_state("fall")

        self.win = tk.Toplevel(app.root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        bg = KEY_HEX
        if IS_WIN:
            self.win.attributes("-transparentcolor", KEY_HEX)
        elif IS_MAC:
            try:
                self.win.attributes("-transparent", True)
                bg = "systemTransparent"
            except tk.TclError:
                pass
        self.win.config(bg=bg)
        self.label = tk.Label(self.win, bd=0, highlightthickness=0, bg=bg)
        self.label.pack()

        self.label.bind("<ButtonPress-1>", self.on_press)
        self.label.bind("<B1-Motion>", self.on_motion)
        self.label.bind("<ButtonRelease-1>", self.on_release)
        self.label.bind("<Button-3>", self.on_menu)
        self.label.bind("<Double-Button-1>", lambda e: self.say_time())
        if IS_MAC:
            self.label.bind("<Button-2>", self.on_menu)
        self.render()

    # ---------------- holatlar ----------------
    def set_state(self, state, anim=None, duration=None):
        self.state = state
        self.anim = anim or state
        self.anim_pos = 0
        self.anim_tick = 0
        self.t = 0
        self.duration = duration

    def anim_frame(self):
        seq = ANIM.get(self.anim, ANIM["stand"])
        idx, dur = seq[self.anim_pos % len(seq)]
        self.anim_tick += 1
        if self.anim_tick >= dur:
            self.anim_tick = 0
            self.anim_pos = (self.anim_pos + 1) % len(seq)
        return idx

    def bounds(self):
        L, T, R, B = self.app.area
        half = self.sp.edge_half
        return L + half, R - half, T + self.sp.h, B

    def leader(self):
        target = None
        for k, v in self.app.settings.get("follow", {}).items():
            if k.lower() == self.name.lower():
                target = str(v).lower()
        if not target:
            return None
        best = None
        for p in self.app.pets:
            if p is not self and p.name.lower() == target and p.state in FLOOR_STATES:
                if best is None or abs(p.x - self.x) < abs(best.x - self.x):
                    best = p
        return best

    def choose_next(self):
        xmin, xmax, _, _ = self.bounds()
        self.climb_after = False
        self.jumping = False
        choices = [
            ("walk", 30), ("run", 5), ("stand", 15), ("sit", 10), ("sit_look", 5),
            ("spin_head", 5), ("dangle", 6), ("sprawl", 6), ("climb", 6), ("jump", 4),
        ]
        if self.leader() is not None:
            choices.append(("follow", 35))
        total = sum(w for _, w in choices)
        r = random.uniform(0, total)
        pick = choices[-1][0]
        for name, w in choices:
            r -= w
            if r <= 0:
                pick = name
                break

        if pick in ("walk", "run"):
            self.target_x = random.uniform(xmin, xmax)
            self.right = self.target_x > self.x
            self.set_state(pick)
        elif pick == "climb":
            self.target_x = xmin if self.x - xmin < xmax - self.x else xmax
            self.right = self.target_x > self.x
            self.climb_after = True
            self.set_state("walk")
        elif pick == "jump":
            self.right = random.random() < 0.5
            self.vx = random.uniform(2, 5) * (1 if self.right else -1)
            self.vy = -random.uniform(12, 17)
            self.jumping = True
            self.set_state("fall")
        elif pick == "follow":
            self.set_state("follow", anim="walk", duration=random.randint(150, 400))
        elif pick == "stand":
            self.set_state("stand", duration=random.randint(25, 100))
        elif pick == "sprawl":
            self.set_state("sprawl", duration=random.randint(60, 200))
        else:
            self.set_state(pick, duration=random.randint(80, 260))

    def fall_from_wall(self):
        self.vx = 2.5 if self.side == "left" else -2.5
        self.vy = 0
        self.set_state("fall")

    # ---------------- har bir tik ----------------
    def tick(self):
        if self.dragging:
            self.tick_drag()
            self.render()
            return

        xmin, xmax, ymin, ymax = self.bounds()
        st = self.state
        self.t += 1
        idx = None

        if st == "fall":
            self.vy = min(self.vy + GRAVITY, MAX_FALL)
            self.vx *= 0.99
            self.x += self.vx
            self.y += self.vy
            if self.y < ymin and self.vy < 0:  # shiftga urildi
                self.y = ymin
                self.vy = 0
            if self.x <= xmin or self.x >= xmax:
                self.side = "left" if self.x <= xmin else "right"
                self.x = xmin if self.side == "left" else xmax
                if abs(self.vx) > 4 and random.random() < 0.6 and self.y < ymax - 20:
                    self.right = self.side == "right"
                    self.vx = self.vy = 0
                    self.set_state("wall_hold", duration=random.randint(20, 60))
                    return self.render()
                self.vx = -self.vx * 0.4
            if self.y >= ymax:
                self.y = ymax
                hard = self.vy > 18
                self.vx = self.vy = 0
                self.jumping = False
                if hard:
                    self.set_state("bounce", duration=8)
                else:
                    self.choose_next()
            idx = ANIM["jump"][0][0] if (self.jumping and self.vy < 0) else ANIM["fall"][0][0]

        elif st in ("walk", "run", "creep"):
            speed = {"walk": 2.0, "run": 5.0, "creep": 0.7}[st] * max(0.5, self.app.scale)
            self.y = ymax
            dx = self.target_x - self.x
            if abs(dx) <= speed:
                self.x = self.target_x
                if self.climb_after:
                    self.side = "left" if self.x <= xmin + 1 else "right"
                    self.right = self.side == "right"
                    self.set_state("wall_climb")
                else:
                    self.choose_next()
            else:
                self.x += speed if dx > 0 else -speed
                self.right = dx > 0
            if st == "creep" and self.duration and self.t > self.duration:
                self.set_state("sprawl", duration=random.randint(40, 120))

        elif st == "follow":
            self.y = ymax
            lead = self.leader()
            if lead is None or (self.duration and self.t > self.duration):
                self.choose_next()
            else:
                gap = self.sp.edge_half * 2.2
                goal = lead.x - gap if self.x < lead.x else lead.x + gap
                goal = min(max(goal, xmin), xmax)
                dx = goal - self.x
                far = abs(dx) > self.sp.edge_half * 6
                speed = (5.0 if far else 2.2) * max(0.5, self.app.scale)
                self.anim = "run" if far else "walk"
                if abs(dx) <= speed:
                    self.x = goal
                    self.right = lead.x > self.x
                    self.anim = "stand"
                else:
                    self.x += speed if dx > 0 else -speed
                    self.right = dx > 0

        elif st == "wall_climb":
            self.x = xmin if self.side == "left" else xmax
            self.y -= 1.4 * max(0.5, self.app.scale)
            if self.y <= ymin:
                self.y = ymin
                self.right = self.side == "left"  # qarama-qarshi tomonga
                self.set_state("ceiling")
            elif random.random() < 0.004:
                self.fall_from_wall()
            elif random.random() < 0.008:
                self.set_state("wall_hold", duration=random.randint(20, 80))

        elif st == "wall_hold":
            self.x = xmin if self.side == "left" else xmax
            if self.t > (self.duration or 40):
                if random.random() < 0.7:
                    self.set_state("wall_climb")
                else:
                    self.fall_from_wall()

        elif st == "ceiling":
            self.y = ymin
            self.x += 1.2 * max(0.5, self.app.scale) * (1 if self.right else -1)
            if self.x <= xmin or self.x >= xmax or random.random() < 0.006:
                self.x = min(max(self.x, xmin), xmax)
                self.vx = self.vy = 0
                self.set_state("fall")

        elif st == "lap_go":
            self.y = ymax
            pt = self.partner
            if pt is None or pt.state != "lap_sit":
                self.end_scene()
            else:
                speed = 2.2 * max(0.5, self.app.scale)
                dx = self.target_x - self.x
                if abs(dx) <= speed:
                    self.x = self.target_x
                    self.right = self.lap_side < 0  # boshi o'tirganga qarab
                    self.set_state("lap_lie", duration=random.randint(450, 1100))
                    try:
                        self.win.lift()
                    except tk.TclError:
                        pass
                else:
                    self.x += speed if dx > 0 else -speed
                    self.right = dx > 0

        elif st == "lap_lie":
            self.y = ymax
            pt = self.partner
            if pt is None or pt.state != "lap_sit" or self.t > self.duration:
                self.end_scene()
            elif self.t == 90:
                self.say("Zzz...", 5)

        elif st == "lap_sit":
            self.y = ymax
            pt = self.partner
            if pt is None or pt.state not in ("lap_go", "lap_lie"):
                self.end_scene()
            elif pt.state == "lap_lie" and pt.t == 200 and random.random() < 0.6:
                self.say(f"{pt.name}, uxla...", 4)

        else:  # stand, sit, sprawl, bounce va boshqalar
            self.y = ymax
            if self.duration is not None and self.t > self.duration:
                if st == "sprawl" and random.random() < 0.5:
                    self.target_x = random.uniform(xmin, xmax)
                    self.right = self.target_x > self.x
                    self.set_state("creep", duration=random.randint(100, 250))
                else:
                    self.choose_next()

        if idx is None:
            idx = self.anim_frame()
        self.render(idx)

    def end_scene(self):
        pt, self.partner = self.partner, None
        if self.state in ("lap_go", "lap_lie", "lap_sit"):
            self.choose_next()
        if pt is not None and pt.partner is self:
            pt.partner = None
            if pt.state in ("lap_go", "lap_lie", "lap_sit"):
                pt.choose_next()

    # ---------------- gapirish ----------------
    def say(self, text, seconds=5):
        if self.bubble is not None:
            self.bubble.destroy()
        self.bubble = Bubble(self.app, text, seconds)
        self.update_bubble()

    def say_time(self):
        t = time.strftime("%H:%M")
        other = None
        for p in self.app.pets:
            if p is not self and p.name.lower() != self.name.lower():
                other = p
                break
        if other is not None and random.random() < 0.5:
            self.say(f"{other.name}, soat {t} bo'ldi!")
        else:
            self.say(f"Soat {t}")

    def update_bubble(self):
        b = self.bubble
        if b is None:
            return
        if time.time() > b.until:
            b.destroy()
            self.bubble = None
            return
        top = self.y - self.sp.h + self.sp.top(self.cur_idx)
        b.move(self.x, top - 4)

    def tick_drag(self):
        # oyoqlar kursordan biroz orqada qoladi -> tebranish
        self.foot_x += (self.x - self.foot_x) * 0.12
        diff = self.x - self.foot_x
        s = max(0.5, self.app.scale)
        if diff > 50 * s:
            self.drag_idx = 9
        elif diff > 25 * s:
            self.drag_idx = 7
        elif diff < -50 * s:
            self.drag_idx = 10
        elif diff < -25 * s:
            self.drag_idx = 8
        else:
            self.anim = "drag_resist"
            self.drag_idx = self.anim_frame()

    # ---------------- chizish ----------------
    def render(self, idx=None):
        if idx is None:
            idx = self.drag_idx if self.dragging else ANIM.get(self.anim, ANIM["stand"])[0][0]
        self.cur_idx = idx
        img = self.sp.frame(idx, self.right and not self.dragging)
        if img is not self.cur_img:
            self.label.config(image=img)
            self.cur_img = img
        gx = int(round(self.x - self.sp.w / 2))
        gy = int(round(self.y - self.sp.h))
        geom = (gx, gy)
        if geom != self.cur_geom:
            self.win.geometry(f"{self.sp.w}x{self.sp.h}+{gx}+{gy}")
            self.cur_geom = geom
        self.update_bubble()

    # ---------------- sichqoncha ----------------
    def on_press(self, e):
        self.app.close_menu()
        self.dragging = True
        self.jumping = False
        self.drag_off = (e.x_root - self.x, e.y_root - self.y)
        self.foot_x = self.x
        self.drag_idx = 5
        self.anim = "drag_resist"
        self.mouse_hist = [(time.time(), e.x_root, e.y_root)]

    def on_motion(self, e):
        if not self.dragging:
            return
        self.x = e.x_root - self.drag_off[0]
        self.y = e.y_root - self.drag_off[1]
        now = time.time()
        self.mouse_hist.append((now, e.x_root, e.y_root))
        self.mouse_hist = [m for m in self.mouse_hist if now - m[0] < 0.12]
        self.render()

    def on_release(self, e):
        if not self.dragging:
            return
        self.dragging = False
        vx = vy = 0.0
        if len(self.mouse_hist) >= 2:
            t0, x0, y0 = self.mouse_hist[0]
            t1, x1, y1 = self.mouse_hist[-1]
            dt = max(t1 - t0, 1e-3)
            ticks = dt * 1000 / TICK_MS
            vx = (x1 - x0) / ticks
            vy = (y1 - y0) / ticks
        self.vx = max(-35, min(35, vx))
        self.vy = max(-35, min(35, vy))
        self.set_state("fall")

    def on_menu(self, e):
        self.app.show_menu(self, e.x_root, e.y_root)

    def sit_down(self):
        if self.state in FLOOR_STATES:
            self.set_state("sit", duration=random.randint(250, 500))

    def destroy(self):
        if self.bubble is not None:
            self.bubble.destroy()
            self.bubble = None
        try:
            self.win.destroy()
        except tk.TclError:
            pass


# --------------------------------------------------------------------------
# Ilova
# --------------------------------------------------------------------------

class App:
    def __init__(self):
        enable_dpi_awareness()
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Desktop Pet")
        self.settings = load_settings()
        try:
            self.scale = float(self.settings.get("scale", 1.0))
        except (TypeError, ValueError):
            self.scale = 1.0
        self.area = get_work_area(self.root)
        self.use_key = not IS_MAC
        self.sprites = {}
        self.pets = []
        self.menu = None
        self.ticks = 0
        self.last_clock = None
        # kompyuter yoqilganda ishga tushish (papka ko'chirilsa, yo'l ham yangilanadi)
        self.autostart = tk.BooleanVar(self.root, value=bool(self.settings.get("autostart", True)))
        if IS_WIN:
            set_autostart(self.autostart.get())

        counts = {}
        for name, cnt in (self.settings.get("characters") or {}).items():
            try:
                counts[name] = int(cnt)
            except (TypeError, ValueError):
                counts[name] = 1
        if os.path.isdir(IMG_DIR):
            for d in sorted(os.listdir(IMG_DIR)):
                if os.path.isdir(os.path.join(IMG_DIR, d)) and d not in counts:
                    counts[d] = 1
        self.names = list(counts)
        for name, cnt in counts.items():
            for _ in range(max(0, cnt)):
                self.spawn(name)
        if not self.pets:
            self.spawn("Eren")

    def sprite_set(self, name):
        if name not in self.sprites:
            folder = os.path.join(IMG_DIR, name)
            try:
                height = int(self.settings.get("height", 160))
            except (TypeError, ValueError):
                height = 160
            self.sprites[name] = SpriteSet(name, folder, self.scale, self.use_key, height)
        return self.sprites[name]

    def spawn(self, name, x=None):
        if len(self.pets) >= int(self.settings.get("max_pets", 20)):
            return None
        pet = Pet(self, self.sprite_set(name), x)
        self.pets.append(pet)
        return pet

    def find_lap_pair(self):
        lap = self.settings.get("lap") or {}
        sn = str(lap.get("sitter", "")).lower()
        ln = str(lap.get("lier", "")).lower()
        sitters = [p for p in self.pets if p.name.lower() == sn and p.partner is None]
        liers = [p for p in self.pets if p.name.lower() == ln and p.partner is None]
        if not sitters or not liers:
            return None
        best = min(((a, b) for a in sitters for b in liers if a is not b),
                   key=lambda ab: abs(ab[0].x - ab[1].x), default=None)
        return best

    def start_lap(self, force=False):
        pair = self.find_lap_pair()
        if pair is None:
            return False
        sitter, lier = pair
        if not force and not (sitter.state in SCENE_READY and lier.state in SCENE_READY):
            return False
        if sitter.dragging or lier.dragging:
            return False
        xmin, xmax, _, _ = lier.bounds()
        off = sitter.sp.edge_half * 0.75 + lier.sp.w * 0.36
        side = 1 if lier.x >= sitter.x else -1
        tx = sitter.x + side * off
        if not (xmin <= tx <= xmax):
            side = -side
            tx = sitter.x + side * off
        tx = min(max(tx, xmin), xmax)
        if sitter.state not in FLOOR_STATES:
            sitter.vx = sitter.vy = 0
        sitter.partner, lier.partner = lier, sitter
        lier.lap_side = side
        sitter.right = side > 0
        sitter.set_state("lap_sit", anim="lap_sit")
        lier.target_x = tx
        lier.set_state("lap_go", anim="walk")
        return True

    def toggle_autostart(self):
        on = bool(self.autostart.get())
        set_autostart(on)
        save_setting("autostart", on)
        if self.pets:
            self.pets[0].say("Endi kompyuter yoqilganda o'zim chiqaman!" if on
                             else "Avtomatik ishga tushish o'chirildi", 4)

    def announce_time(self):
        ready = [p for p in self.pets if p.state in SCENE_READY or p.state == "lap_sit"]
        pet = random.choice(ready or self.pets) if self.pets else None
        if pet is not None:
            pet.say_time()

    def remove(self, pet):
        if pet in self.pets:
            self.pets.remove(pet)
            pet.destroy()
        if not self.pets:
            self.quit()

    def close_menu(self):
        if self.menu is not None:
            try:
                self.menu.unpost()
                self.menu.destroy()
            except tk.TclError:
                pass
            self.menu = None

    def show_menu(self, pet, x, y):
        self.close_menu()
        m = tk.Menu(self.root, tearoff=0)
        title = pet.name + (" (rasm topilmadi)" if pet.sp.placeholder else "")
        m.add_command(label=title, state="disabled")
        m.add_separator()
        for name in self.names:
            m.add_command(label=f"{name} qo'shish", command=lambda n=name: self.spawn(n))
        m.add_separator()
        m.add_command(label="Soat nechchi?", command=pet.say_time)
        if self.find_lap_pair() is not None or pet.partner is not None:
            lap = self.settings.get("lap") or {}
            m.add_command(label=f"{lap.get('lier', '?')} {lap.get('sitter', '?')}ning tizzasiga yotsin",
                          command=lambda: self.start_lap(force=True))
        m.add_command(label="O'tirsin", command=pet.sit_down)
        m.add_command(label="Hammasi o'tirsin",
                      command=lambda: [p.sit_down() for p in self.pets])
        m.add_command(label="Bu personajni yopish", command=lambda: self.remove(pet))
        m.add_separator()
        if IS_WIN:
            m.add_checkbutton(label="Kompyuter yoqilganda ishga tushsin",
                              variable=self.autostart, command=self.toggle_autostart)
        m.add_command(label="Chiqish (hammasini yopish)", command=self.quit)
        self.menu = m
        try:
            m.tk_popup(x, y)
        finally:
            m.grab_release()

    def loop(self):
        self.ticks += 1
        if self.ticks % 125 == 0:  # har 5 soniyada
            self.area = get_work_area(self.root)
            # yotgan personaj o'tirganning ustida ko'rinishi uchun oxirida ko'tariladi
            order = sorted(self.pets, key=lambda q: q.state in ("lap_go", "lap_lie"))
            for p in order:
                try:
                    p.win.attributes("-topmost", True)
                    p.win.lift()
                    if p.bubble is not None:
                        p.bubble.win.lift()
                except tk.TclError:
                    pass
        if self.ticks % 25 == 0:  # har soniyada soatni tekshirish
            self.check_clock()
        if self.ticks % 750 == 0 and random.random() < 0.4:  # ~har 30 soniyada
            self.start_lap()
        for p in list(self.pets):
            try:
                p.tick()
            except tk.TclError:
                self.pets.remove(p)
        self.root.after(TICK_MS, self.loop)

    def check_clock(self):
        try:
            every = int(self.settings.get("clock_every_min", 5))
        except (TypeError, ValueError):
            every = 5
        if every <= 0:
            return
        now = time.localtime()
        key = (now.tm_hour, now.tm_min)
        if self.last_clock is None:
            # ishga tushgandan 3 soniya o'tib bir marta aytadi
            if self.ticks >= 75:
                self.last_clock = key
                self.announce_time()
            return
        if key != self.last_clock and now.tm_min % every == 0:
            self.last_clock = key
            self.announce_time()

    def quit(self):
        self.close_menu()
        for p in self.pets:
            p.destroy()
        self.pets = []
        self.root.quit()

    def run(self):
        self.root.after(TICK_MS, self.loop)
        self.root.mainloop()


if __name__ == "__main__":
    if not already_running():
        App().run()
