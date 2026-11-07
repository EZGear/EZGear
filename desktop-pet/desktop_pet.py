#!/usr/bin/env python3
"""
Desktop Pet — ekranda yuradigan personajlar (shimeji uslubida).

Personaj rasmlari  img/<Ism>/shime1.png ... shime46.png  ko'rinishida
saqlanadi (standart Shimeji formati). Har bir papka — bitta personaj.
Rasmlar topilmasa, dastur vaqtinchalik oddiy shakllarni chizadi.

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
    "max_pets": 20,
    "characters": {"Eren": 1, "Mikasa": 1},
    # Mikasa ko'pincha Erenning orqasidan yuradi
    "follow": {"Mikasa": "Eren"},
}

# Shimeji rasm raqamlari bo'yicha animatsiyalar: (rasm raqami, necha tik)
ANIM = {
    "stand": [(1, 1)],
    "walk": [(1, 6), (2, 6), (1, 6), (3, 6)],
    "run": [(1, 3), (2, 3), (1, 3), (3, 3)],
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
}

# Biror rasm yo'q bo'lsa, o'rniga qaysi biri ishlatiladi
FALLBACK = {
    2: 1, 3: 1, 4: 1, 5: 4, 6: 5, 7: 5, 8: 5, 9: 7, 10: 8, 11: 1,
    12: 13, 13: 14, 14: 4, 15: 26, 16: 26, 17: 26, 18: 1, 19: 18,
    20: 21, 21: 11, 22: 4, 23: 24, 24: 25, 25: 4, 26: 11, 27: 26,
    28: 26, 30: 11, 31: 11, 32: 31, 33: 31,
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


class SpriteSet:
    def __init__(self, name, folder, scale, use_key):
        self.name = name
        raw = {}
        if folder and os.path.isdir(folder):
            for i in range(1, MAX_INDEX + 1):
                p = os.path.join(folder, f"shime{i}.png")
                if os.path.isfile(p):
                    try:
                        raw[i] = Image.open(p).convert("RGBA")
                    except Exception:
                        pass
        self.placeholder = not raw
        if not raw:
            raw = {i: make_placeholder(i, name) for i in PLACEHOLDER_INDICES}

        base = raw.get(1) or raw[min(raw)]
        w, h = base.size
        if scale and abs(scale - 1.0) > 1e-3:
            w, h = max(8, int(w * scale)), max(8, int(h * scale))
        self.w, self.h = w, h

        self.left, self.right = {}, {}
        for i, im in raw.items():
            if im.size != (w, h):
                im = im.resize((w, h), Image.LANCZOS)
            fl = im.transpose(Image.FLIP_LEFT_RIGHT)
            if use_key:
                im, fl = keyed(im), keyed(fl)
            self.left[i] = ImageTk.PhotoImage(im)
            self.right[i] = ImageTk.PhotoImage(fl)

    def frame(self, idx, facing_right):
        for _ in range(8):
            if idx in self.left:
                break
            idx = FALLBACK.get(idx, 1)
        if idx not in self.left:
            idx = 1 if 1 in self.left else min(self.left)
        # Shimeji rasmlari chapga qaragan bo'ladi
        return (self.right if facing_right else self.left)[idx]


# --------------------------------------------------------------------------
# Personaj
# --------------------------------------------------------------------------

FLOOR_STATES = {"stand", "walk", "run", "sit", "sit_look", "spin_head",
                "dangle", "sprawl", "creep", "follow", "bounce"}


class Pet:
    def __init__(self, app, sprites, x=None):
        self.app = app
        self.sp = sprites
        self.name = sprites.name
        L, T, R, B = app.area
        w = sprites.w
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
        half = self.sp.w / 2
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
                gap = self.sp.w * 0.55
                goal = lead.x - gap if self.x < lead.x else lead.x + gap
                goal = min(max(goal, xmin), xmax)
                dx = goal - self.x
                far = abs(dx) > self.sp.w * 3
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
        img = self.sp.frame(idx, self.right)
        if img is not self.cur_img:
            self.label.config(image=img)
            self.cur_img = img
        gx = int(round(self.x - self.sp.w / 2))
        gy = int(round(self.y - self.sp.h))
        geom = (gx, gy)
        if geom != self.cur_geom:
            self.win.geometry(f"{self.sp.w}x{self.sp.h}+{gx}+{gy}")
            self.cur_geom = geom

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
            self.sprites[name] = SpriteSet(name, folder, self.scale, self.use_key)
        return self.sprites[name]

    def spawn(self, name, x=None):
        if len(self.pets) >= int(self.settings.get("max_pets", 20)):
            return None
        pet = Pet(self, self.sprite_set(name), x)
        self.pets.append(pet)
        return pet

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
        m.add_command(label="O'tirsin", command=pet.sit_down)
        m.add_command(label="Hammasi o'tirsin",
                      command=lambda: [p.sit_down() for p in self.pets])
        m.add_command(label="Bu personajni yopish", command=lambda: self.remove(pet))
        m.add_separator()
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
            for p in self.pets:
                try:
                    p.win.attributes("-topmost", True)
                    p.win.lift()
                except tk.TclError:
                    pass
        for p in list(self.pets):
            try:
                p.tick()
            except tk.TclError:
                self.pets.remove(p)
        self.root.after(TICK_MS, self.loop)

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
    App().run()
