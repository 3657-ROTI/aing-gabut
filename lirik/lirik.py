import tkinter as tk
import tkinter.font as tkfont
import random
import math
import time
import re
import os
import ctypes

# ============================================================
# OVERLAY LYRIC CARDS - TKINTER (khusus Windows)
# Kartu lirik naik dari bawah layar dan melayang DI ATAS DESKTOP
# (jendela transparan tanpa bingkai, menutupi seluruh layar).
#
# Jendela kecil "Kontrol" dipakai untuk MULAI / JEDA / ULANG / KELUAR.
# Kontrol keyboard di jendela Kontrol: SPASI, P, R, Esc.
# ============================================================

# ------------------------------------------------------------
# TEMPEL LIRIK KAMU DI SINI (satu baris lirik per baris)
# Boleh juga berformat [menit:detik.ratusan] teks, mis. [00:12.50] teks
# ------------------------------------------------------------
LYRICS_TEXT = """
You know it's true
Yeah, I miss you
You know it's true
So, what if I call?
And you pick up the phone?
And I use this holiday 
to make my way to your ghost
But, what if you're lonely?
And you know I am too?
And I get the chance to say
"I wish I didn't, but I miss you"
I miss you
"""

# --- Pengaturan timing (dipakai jika lirik TIDAK berformat [mm:ss]) ---
SONG_DURATION = 0        # durasi lagu dalam detik, mis. 195. 0 = pakai SECONDS_PER_LINE
SECONDS_PER_LINE = 4.4   # jeda tiap baris jika SONG_DURATION = 0
FIRST_LINE_AT = 0.0      # lirik pertama muncul di detik ke-berapa

# --- Mode sinkron manual (paling akurat) ---
# True  = putar lagu, lalu tekan ENTER (atau tombol BERIKUTNYA) tiap kali
#         baris lirik berganti. Waktunya disimpan ke lyrics_timing.txt
#         saat kamu menekan ULANG atau KELUAR.
# False = timing otomatis seperti pengaturan di atas.
SYNC_MODE = False

FILLER_PER_SECOND = 0.0     # kartu hiasan ekstra. 0 = mati (hanya kartu lirik)
FILLER_USE_TEXT = False     # kartu hiasan kosong tanpa teks
TYPE_CPS = 22               # kecepatan mengetik (huruf per detik)
TYPE_FRACTION = 0.6         # mengetik selesai maksimal di sekian bagian dari durasi baris
MAX_OLD_CARDS = 2           # kartu lirik lama yang masih terlihat di samping kartu aktif
PARTICLE_COUNT = 60
FRAME_TIME = 16

# --- Lagu (mp3 / wav) ---
# Taruh file lagu di folder yang sama dengan file .py ini, lalu isi namanya.
# Kosongkan ("") kalau tidak ingin memutar lagu.
AUDIO_FILE = "matthew.mp3"
# Geser sinkron lirik terhadap lagu (detik).
# Positif = lirik muncul lebih cepat, negatif = lebih lambat. Coba 0.1 / -0.1.
AUDIO_OFFSET = 0.0

# Warna (jangan pakai #010101, itu warna transparan)
TRANSPARENT = "#010101"
RED = "#3f1d9b"
RED_EDGE = "#f4eaea"
WHITE = "#f4efef"
WHITE_TEXT = "#2a1a1c"
PARTICLE = "#eae9e9"
FONT_NAME = "Georgia"
GRAY_FILL = "#5d5759"
GRAY_EDGE = "#9a9294"
GRAY_TEXT = "#d9d4d5"
FLASH_TEXT = "#3a3335"
GRAY_TIME = 0.9            # lama transisi kilatan lalu menjadi abu-abu (detik)
GRAY_START = 0.42          # kartu mulai abu-abu di atas tinggi layar ini (0 = atas, 1 = bawah)


def build_lyrics(text):
    parsed = []
    timed = 0
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"\[(\d+):(\d+(?:\.\d+)?)\]\s*(.*)", line)
        if m:
            if m.group(3).strip():
                t = int(m.group(1)) * 60 + float(m.group(2))
                parsed.append((t, m.group(3).strip()))
                timed += 1
        else:
            parsed.append((None, line))

    if parsed and timed == len(parsed):
        parsed.sort(key=lambda x: x[0])
        return parsed

    texts = [t for _, t in parsed]
    n = len(texts)
    if SONG_DURATION > 0 and n:
        step = max(0.5, (SONG_DURATION - FIRST_LINE_AT) / n)
    else:
        step = SECONDS_PER_LINE
    return [(FIRST_LINE_AT + i * step, t) for i, t in enumerate(texts)]


LYRICS = build_lyrics(LYRICS_TEXT)

# ============================================================
# AUDIO (khusus Windows, tanpa library tambahan)
# ============================================================
audio_ok = False
audio_state = {"started": False}


def _mci(cmd):
    try:
        return ctypes.windll.winmm.mciSendStringW(cmd, None, 0, 0)
    except Exception:
        return -1


def audio_init():
    global audio_ok
    if not AUDIO_FILE:
        return
    path = AUDIO_FILE
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    if not os.path.exists(path):
        print(f"File lagu tidak ditemukan: {path}")
        return
    _mci("close song")
    audio_ok = _mci(f'open "{path}" type mpegvideo alias song') == 0
    if not audio_ok:
        print("Gagal membuka lagu. Coba pakai format .mp3 atau .wav")
    else:
        _mci("set song time format milliseconds")


def audio_play():
    if audio_ok:
        _mci("play song from 0")


def audio_position():
    """Posisi lagu saat ini (detik), atau None jika tidak tersedia."""
    if not audio_ok:
        return None
    try:
        buf = ctypes.create_unicode_buffer(64)
        if ctypes.windll.winmm.mciSendStringW("status song position", buf, 64, 0) == 0:
            return int(buf.value) / 1000.0
    except Exception:
        pass
    return None


def audio_pause():
    if audio_ok:
        _mci("pause song")


def audio_resume():
    if audio_ok:
        _mci("resume song")


def audio_stop():
    if audio_ok:
        _mci("stop song")
        _mci("seek song to start")


def audio_close():
    if audio_ok:
        _mci("close song")


# ============================================================
# JENDELA OVERLAY TRANSPARAN
# ============================================================
root = tk.Tk()
root.overrideredirect(True)
SW = root.winfo_screenwidth()
SH = root.winfo_screenheight()
root.geometry(f"{SW}x{SH}+0+0")
root.attributes("-topmost", True)
root.configure(bg=TRANSPARENT)
try:
    root.attributes("-transparentcolor", TRANSPARENT)
except tk.TclError:
    print("Transparansi hanya didukung di Windows.")

canvas = tk.Canvas(root, width=SW, height=SH, bg=TRANSPARENT,
                   highlightthickness=0, bd=0)
canvas.pack(fill="both", expand=True)

S = max(0.6, min(SW / 1920, SH / 1080))   # skala mengikuti resolusi
CARD_W = 400 * S
CARD_H = 210 * S
GRAY_Y = GRAY_START * SH


# ============================================================
# PARTIKEL (serpihan merah kecil)
# ============================================================
class Particle:
    def __init__(self):
        self.reset(True)

    def reset(self, first=False):
        self.x = random.uniform(0, SW)
        self.y = random.uniform(0, SH) if first else SH + 20
        self.speed = random.uniform(0.4, 1.6) * S
        self.size = random.uniform(2, 5) * S
        self.drift = random.uniform(0.2, 0.7)
        self.phase = random.uniform(0, math.pi * 2)
        self.spin = random.uniform(0.015, 0.05)

    def update(self):
        self.phase += self.spin
        self.y -= self.speed
        self.x += math.sin(self.phase) * self.drift
        if self.y < -20:
            self.reset()

    def draw(self):
        s = self.size
        canvas.create_polygon(self.x, self.y - s * 1.6, self.x + s, self.y,
                              self.x, self.y + s * 1.6, self.x - s, self.y,
                              fill=PARTICLE, outline="")


particles = [Particle() for _ in range(PARTICLE_COUNT)]


# ============================================================
# KARTU
# ============================================================
def rounded_rect(w, h, r, steps=6):
    pts = []
    corners = [(w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0),
               (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)]
    for cx, cy, start in corners:
        for i in range(steps + 1):
            a = math.radians(start + 90 * i / steps)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def transform(pts, cx, cy, angle):
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    flat = []
    for px, py in pts:
        flat.extend([px * ca - py * sa + cx, px * sa + py * ca + cy])
    return flat


def hex_blend(c1, c2, t):
    t = max(0.0, min(1.0, t))
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


_fonts = {}
_wrap_cache = {}
frame_no = 0


def get_font(size):
    if size not in _fonts:
        _fonts[size] = tkfont.Font(family=FONT_NAME, size=size, weight="bold")
    return _fonts[size]


def wrap_lines(text, font, max_w, size):
    key = (text, size, max_w)
    if key in _wrap_cache:
        return _wrap_cache[key]
    if len(_wrap_cache) > 500:
        _wrap_cache.clear()
    lines, cur = [], ""
    for word in text.split():
        trial = word if not cur else cur + " " + word
        if cur and font.measure(trial) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    _wrap_cache[key] = lines
    return lines


class Card:
    def __init__(self, text, is_red, big=False, type_cps=None):
        self.text = " ".join(text.split())
        self.is_red = is_red
        self.typed = 0.0
        self.type_cps = type_cps or TYPE_CPS
        self.type_started = False
        self.big = big

        if big:
            self.scale = 1.0
            self.target_scale = random.uniform(1.0, 1.15)
        else:
            self.scale = 0.4
            self.target_scale = random.uniform(0.45, 0.75)

        margin = CARD_W * 0.6
        self.x0 = random.uniform(margin, SW - margin)
        self.x = self.x0
        self.y = SH + CARD_H
        self.hold_y = random.uniform(0.45, 0.72) * SH   # posisi diam kartu besar
        self.vy = 4.0 * S
        self.target_vy = random.uniform(0.8, 1.6) * S

        self.angle = random.uniform(-6, 6)
        self.sway_amp = random.uniform(10, 30) * S
        self.phase = random.uniform(0, math.pi * 2)
        self.speed = random.uniform(0.010, 0.022)
        self.alpha = 1.0
        self.leave = False
        self.gray_t = None
        self.leave_alpha = 1.0
        self.dead = False

    def demote(self):
        self.big = False
        self.target_scale = random.uniform(0.6, 0.8)
        self.target_vy = random.uniform(0.8, 1.5) * S

    def update(self):
        self.phase += self.speed
        self.x = self.x0 + math.sin(self.phase) * self.sway_amp

        if self.big:
            goal_vy = 4.5 * S if self.y > self.hold_y else 0.25 * S
        else:
            goal_vy = self.target_vy
        self.vy += (goal_vy - self.vy) * 0.06
        self.y -= self.vy

        self.scale += (self.target_scale - self.scale) * 0.05

        if not self.type_started and self.y < SH:
            self.type_started = True
        if self.type_started and self.typed < len(self.text):
            self.typed = min(len(self.text),
                             self.typed + self.type_cps * FRAME_TIME / 1000)

        if not self.big and self.gray_t is None and (self.y < GRAY_Y or self.leave):
            self.gray_t = 0.0
        if self.gray_t is not None and self.gray_t < 1.0:
            self.gray_t = min(1.0, self.gray_t + FRAME_TIME / 1000 / GRAY_TIME)

        fade_zone = 260 * S
        self.alpha = 1.0 if self.y > fade_zone else max(0.0, self.y / fade_zone)
        if self.leave:
            self.leave_alpha -= 0.02
            self.alpha = min(self.alpha, self.leave_alpha)
            if self.leave_alpha <= 0:
                self.dead = True

        if self.y < -CARD_H:
            self.dead = True

    def colors(self):
        base_fill = RED if self.is_red else WHITE
        base_edge = RED_EDGE if self.is_red else RED
        base_text = "#ffffff" if self.is_red else WHITE_TEXT
        p = self.gray_t
        if p is None:
            return base_fill, base_edge, base_text
        if p < 0.3:                      # kilatan: menuju putih
            t = p / 0.3
            return (hex_blend(base_fill, "#ffffff", t),
                    hex_blend(base_edge, "#ffffff", t),
                    hex_blend(base_text, FLASH_TEXT, t))
        t = (p - 0.3) / 0.7              # putih memudar menjadi abu-abu
        return (hex_blend("#ffffff", GRAY_FILL, t),
                hex_blend("#ffffff", GRAY_EDGE, t),
                hex_blend(FLASH_TEXT, GRAY_TEXT, t))

    def draw(self):
        w = CARD_W * self.scale
        h = CARD_H * self.scale
        fill, edge, text_color = self.colors()

        # cincin cahaya + kilau saat berubah menjadi abu-abu
        if self.gray_t is not None and self.gray_t < 0.6:
            t = self.gray_t / 0.6
            for grow in (0.10, 0.24):
                k = 1.0 + grow * (0.4 + t)
                ring = transform(rounded_rect(w * k, h * k, 26 * self.scale * S),
                                 self.x, self.y, self.angle)
                canvas.create_polygon(ring, fill="", outline="#ffffff",
                                      width=max(1, int(6 * (1 - t) * S)))
            L = 55 * S * self.scale * math.sin(math.pi * t)
            sx = self.x + w * 0.36
            sy = self.y - h * 0.36
            if L > 2:
                canvas.create_line(sx - L, sy, sx + L, sy, fill="#ffffff", width=2)
                canvas.create_line(sx, sy - L, sx, sy + L, fill="#ffffff", width=2)
                d = L * 0.55
                canvas.create_line(sx - d, sy - d, sx + d, sy + d, fill="#ffffff", width=1)
                canvas.create_line(sx - d, sy + d, sx + d, sy - d, fill="#ffffff", width=1)

        pts = transform(rounded_rect(w, h, 26 * self.scale * S), self.x, self.y, self.angle)

        # Tkinter tidak punya alpha, jadi memudar dipalsukan dengan stipple
        if self.alpha > 0.75:
            stipple = ""
        elif self.alpha > 0.5:
            stipple = "gray75"
        elif self.alpha > 0.25:
            stipple = "gray50"
        else:
            stipple = "gray25"

        canvas.create_polygon(pts, fill=fill, stipple=stipple,
                              outline=edge if self.alpha > 0.3 else "",
                              width=max(2, int(3 * self.scale * S)))

        # kotak kecil di pojok kiri bawah
        q = 16 * self.scale * S
        bx = self.x - w * 0.42
        by = self.y + h * 0.36
        a = math.radians(self.angle)
        rx = (bx - self.x) * math.cos(a) - (by - self.y) * math.sin(a) + self.x
        ry = (bx - self.x) * math.sin(a) + (by - self.y) * math.cos(a) + self.y
        if self.alpha > 0.3:
            if self.gray_t is None:
                sq = PARTICLE if self.is_red else RED
            else:
                sq = edge
            canvas.create_rectangle(rx - q / 2, ry - q / 2, rx + q / 2, ry + q / 2,
                                    fill=sq, outline="")

        # teks tetap terlihat saat naik (berubah abu-abu), baru hilang di ujung atas
        if self.text and self.alpha > 0.12 and self.scale > 0.4:
            self.draw_text(w, h, text_color)

    def draw_text(self, w, h, text_color):
        """Teks muncul huruf demi huruf (efek mengetik) dengan kursor berkedip."""
        size = max(11, int(30 * self.scale * S))
        font = get_font(size)
        lines = wrap_lines(self.text, font, int(w * 0.78), size)
        lh = font.metrics("linespace")
        total_h = lh * len(lines)
        a = math.radians(self.angle)
        ca, sa = math.cos(a), math.sin(a)

        typing = self.typed < len(self.text)
        caret_on = typing and (frame_no // 18) % 2 == 0
        remaining = int(self.typed)

        for i, line in enumerate(lines):
            is_current = typing and 0 <= remaining <= len(line)
            shown = line[:max(0, min(len(line), remaining))]
            remaining -= len(line) + 1
            txt = shown + ("|" if caret_on and is_current else "")
            if not txt:
                continue
            dx = -font.measure(line) / 2
            dy = -total_h / 2 + lh * (i + 0.5) - h * 0.03
            gx = self.x + dx * ca - dy * sa
            gy = self.y + dx * sa + dy * ca
            canvas.create_text(gx, gy, text=txt, anchor="w", fill=text_color,
                               font=(FONT_NAME, size, "bold"),
                               angle=-self.angle)


# ============================================================
# STATE
# ============================================================
cards = []
current_index = -1
filler_timer = 0.0
running = False
paused = False
start_time = 0.0
saved_elapsed = 0.0
sync_index = -1
sync_times = []


def pick_red():
    return random.random() < 0.75


def spawn_lyric(index):
    for c in cards:
        if c.big:
            c.demote()
    text = LYRICS[index][1]
    cps = TYPE_CPS
    if not SYNC_MODE and index + 1 < len(LYRICS):
        dur = LYRICS[index + 1][0] - LYRICS[index][0]
        want = max(0.3, min(len(text) / TYPE_CPS, dur * TYPE_FRACTION))
        cps = len(text) / want
    cards.append(Card(text, pick_red(), big=True, type_cps=cps))
    olds = [c for c in cards if not c.big and not c.leave]
    extra = olds[:-MAX_OLD_CARDS] if MAX_OLD_CARDS > 0 else olds
    for c in extra:
        c.leave = True


def spawn_filler():
    text = ""
    if FILLER_USE_TEXT and current_index >= 0:
        text = LYRICS[random.randint(0, current_index)][1]
    cards.append(Card(text, pick_red(), big=False, type_cps=9999))


def get_current_index(elapsed):
    result = -1
    for i, (start, _) in enumerate(LYRICS):
        if elapsed >= start:
            result = i
        else:
            break
    return result


def get_elapsed():
    """Waktu animasi. Jika ada lagu, waktunya mengikuti posisi lagu sebenarnya,
    jadi animasi baru mulai tepat saat lagu benar-benar bunyi."""
    if not running:
        return 0.0
    if paused:
        return max(0.0, saved_elapsed + AUDIO_OFFSET)
    if audio_ok:
        pos = audio_position()
        if pos is not None and pos > 0.0:
            audio_state["started"] = True
        if audio_state["started"] and pos is not None:
            return max(0.0, pos + AUDIO_OFFSET)
        if time.perf_counter() - start_time < 1.5:
            return -1.0          # tunggu sampai lagu benar-benar mulai
        # lagu tidak kunjung mulai: pakai timer biasa
    return max(0.0, time.perf_counter() - start_time + AUDIO_OFFSET)


# ============================================================
# JENDELA KONTROL
# ============================================================
control = tk.Toplevel(root)
control.title("Kontrol")
control.configure(bg="#1a1012")
control.attributes("-topmost", True)
control.resizable(False, False)
control.geometry(f"+{SW // 2 - 190}+{SH - 170}")
control.protocol("WM_DELETE_WINDOW", lambda: quit_app())


def start_or_continue(event=None):
    global running, paused, start_time
    if not running:
        audio_state["started"] = False
        audio_play()
        running, paused = True, False
        start_time = time.perf_counter()
    elif paused:
        paused = False
        start_time = time.perf_counter() - saved_elapsed
        audio_resume()
    update_buttons()


def pause(event=None):
    global paused, saved_elapsed
    if running and not paused:
        saved_elapsed = max(0.0, get_elapsed() - AUDIO_OFFSET)
        paused = True
        audio_pause()
    update_buttons()


def save_timing():
    if not sync_times:
        return
    lines = []
    for t, (_, txt) in zip(sync_times, LYRICS):
        lines.append(f"[{int(t) // 60:02d}:{t % 60:05.2f}] {txt}")
    with open("lyrics_timing.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Timing disimpan ke lyrics_timing.txt")


def next_line(event=None):
    global sync_index
    if SYNC_MODE and running and not paused and sync_index + 1 < len(LYRICS):
        sync_index += 1
        sync_times.append(get_elapsed())


def reset(event=None):
    global running, paused, saved_elapsed, current_index, filler_timer
    global sync_index
    audio_stop()
    audio_state["started"] = False
    save_timing()
    sync_times.clear()
    sync_index = -1
    running = paused = False
    saved_elapsed = 0
    current_index = -1
    filler_timer = 0
    cards.clear()
    update_buttons()


def quit_app(event=None):
    save_timing()
    audio_close()
    root.destroy()


def make_button(text, cmd, bg, active):
    b = tk.Button(control, text=text, command=cmd, bg=bg, fg="white",
                  activebackground=active, activeforeground="white",
                  relief="flat", bd=0, padx=14, pady=6,
                  font=("Arial", 9, "bold"), takefocus=0)
    b.pack(side="left", padx=5, pady=8)
    return b


start_button = make_button("HAYU", start_or_continue, "#4f1f9d", "#982dc9")
make_button("JEDA", pause, "#4f1f9d", "#982dc9")
make_button("ULANG", reset, "#4f1f9d", "#982dc9")
make_button("BERIKUTNYA", next_line, "#4f1f9d", "#982dc9")
make_button("KELUAR", quit_app, "#4f1f9d", "#982dc9")
time_label = tk.Label(control, text="00:00", bg="#1a1012", fg="#b8a5a6",
                      font=("Arial", 9))
time_label.pack(side="left", padx=(8, 12))

control.bind("<space>", start_or_continue)
control.bind("<p>", pause)
control.bind("<r>", reset)
control.bind("<Return>", next_line)
control.bind("<Escape>", quit_app)


def update_buttons():
    if not running:
        start_button.config(text="HAYU")
    elif paused:
        start_button.config(text="LANJUT")
    else:
        start_button.config(text="BERJALAN")


# ============================================================
# LOOP ANIMASI
# ============================================================
def animate():
    global current_index, filler_timer, frame_no

    frame_no += 1
    canvas.delete("all")

    for p in particles:
        p.update()
        p.draw()

    elapsed = get_elapsed()
    active = running and not paused

    if running and LYRICS:
        index = sync_index if SYNC_MODE else get_current_index(elapsed)
        if index != current_index:
            current_index = index
            if index >= 0:
                spawn_lyric(index)

    if active:
        filler_timer += FRAME_TIME / 1000
        if FILLER_PER_SECOND > 0 and filler_timer >= 1.0 / FILLER_PER_SECOND:
            filler_timer = 0
            spawn_filler()
        for c in cards:
            c.update()
        cards[:] = [c for c in cards if not c.dead]

    for c in sorted(cards, key=lambda c: (c.big, c.scale)):
        c.draw()

    shown = max(0.0, elapsed)
    time_label.config(text=f"{int(shown) // 60:02d}:{int(shown) % 60:02d}")
    root.after(FRAME_TIME, animate)


audio_init()
control.lift()
animate()
root.mainloop()