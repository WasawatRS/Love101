import math as m
import random as r
import turtle as t
import tkinter as tk
import tkinter.font as tkf

BASE = 800
SC0 = 21
OY0 = 20
DURATION = 10
TICK = 16
ANIM = 42
LIFT0 = 34
GAP0 = 7
SIZES0 = (9, 10, 11, 12)
FONT = "Arial"
BG = "#060208"
MIN_ZOOM = 0.55
MAX_ZOOM = 1.45
FIT = 0.96
BAR = 46

try:
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

s = t.Screen()
s.bgcolor(BG)
s.title("Love Heart")
s.tracer(0)

cv = s.getcanvas()
rng = r.Random(11)

PHRASES = [
    "",
]

_fonts = {}
ZOOM = 1.0
SC = SC0
OY = OY0
LIFT = LIFT0
GAP = GAP0
SIZES = SIZES0


def zoom_clamp(v):
    return max(MIN_ZOOM, min(MAX_ZOOM, v))


def pick_zoom(sw, sh):
    return zoom_clamp((min(sw, sh - BAR)) * FIT / BASE)


def font_for(size):
    if size not in _fonts:
        _fonts[size] = tkf.Font(
            root=cv, family=FONT, size=size, weight="bold"
        )
    return _fonts[size]


def heart(a):
    x = 16 * (m.sin(a) ** 3)
    y = (
        13 * m.cos(a)
        - 5 * m.cos(2 * a)
        - 2 * m.cos(3 * a)
        - m.cos(4 * a)
    )
    return x * SC, y * SC + OY


def hx(c):
    return "#%02x%02x%02x" % tuple(
        int(max(0, min(1, v)) * 255) for v in c
    )


def mix(a, b, k):
    return tuple(p + (q - p) * k for p, q in zip(a, b))


def dim(c, k):
    return tuple(v * k for v in c)


POLY = []
EDGES = []
YMAX = 0
YMIN = 0
CY = 0


def rebuild_shape():
    global POLY, EDGES, YMAX, YMIN, CY
    POLY = [heart(2 * m.pi * i / 720) for i in range(720)]
    EDGES = list(zip(POLY, POLY[1:] + POLY[:1]))
    YMAX = max(p[1] for p in POLY)
    YMIN = min(p[1] for p in POLY)
    CY = (YMAX + YMIN) / 2


def apply_zoom(zoom):
    global ZOOM, SC, OY, LIFT, GAP, SIZES
    ZOOM = zoom_clamp(zoom)
    SC = SC0 * ZOOM
    OY = OY0 * ZOOM - BAR / 2
    LIFT = LIFT0 * ZOOM
    GAP = GAP0 * ZOOM
    SIZES = tuple(max(8, int(round(z * ZOOM))) for z in SIZES0)
    _fonts.clear()
    rebuild_shape()


def spans(y):
    xs = []
    for (x1, y1), (x2, y2) in EDGES:
        if (y1 <= y < y2) or (y2 <= y < y1):
            xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    xs.sort()
    return list(zip(xs[0::2], xs[1::2]))


def intersect(A, B):
    out = []
    for a in A:
        for b in B:
            lo, hi = max(a[0], b[0]), min(a[1], b[1])
            if hi - lo > 14 * ZOOM:
                out.append((lo, hi))
    return out


def phrase_cycle():
    while True:
        order = PHRASES[:]
        rng.shuffle(order)
        yield from order


def build():
    cycle = phrase_cycle()
    row_h = max(font_for(z).metrics("linespace") for z in SIZES) + 4 * ZOOM
    half = row_h / 2
    placed = []

    y = YMAX - half
    while y > YMIN + half:
        row = intersect(spans(y + half), spans(y - half))

        for lo, hi in row:
            lo += 4 * ZOOM
            hi -= 4 * ZOOM
            cur = lo + rng.uniform(0, 8 * ZOOM)
            line = []

            while True:
                fit = None
                for _ in range(10):
                    text = next(cycle)
                    size = rng.choice(SIZES)
                    w = font_for(size).measure(text)
                    if cur + w <= hi:
                        fit = (text, size, w)
                        break
                if not fit:
                    break
                text, size, w = fit
                line.append([cur + w / 2, text, size, w])
                cur += w + GAP

            if not line:
                continue

            if len(line) > 1:
                left = hi - (line[-1][0] + line[-1][3] / 2)
                for i, it in enumerate(line):
                    it[0] += left * i / (len(line) - 1)
            else:
                line[0][0] = (lo + hi) / 2

            for i, (x, text, size, w) in enumerate(line):
                edge = i == 0 or i == len(line) - 1
                placed.append(dict(x=x, y=y, text=text, size=size, edge=edge))

        y -= row_h

    wine = (0.58, 0.0, 0.09)
    crimson = (0.90, 0.05, 0.14)
    blood = (0.98, 0.10, 0.16)
    for p in placed:
        rad = min(1.0, math_dist(p["x"], p["y"]))
        base = mix(wine, crimson, 0.25 + 0.75 * rad)
        base = mix(base, blood, rng.uniform(0, 0.35) + (0.3 if p["edge"] else 0))
        p["color"] = tuple(min(1, v) for v in base)
        p["rad"] = rad

    edges = [p for p in placed if p["edge"]]
    inner = [p for p in placed if not p["edge"]]
    edges.sort(key=lambda p: m.atan2(p["x"], p["y"] - CY) % (2 * m.pi))
    inner.sort(key=lambda p: -p["rad"] + rng.uniform(0, 0.08))
    return edges + inner


def math_dist(x, y):
    return m.hypot(x / (16 * SC), (y - CY) / (14.5 * SC))


FLASH = (1.0, 0.78, 0.78)
main_ids = []
active = []
tick_no = 0


def clamp(v):
    return max(0.0, min(1.0, v))


def spawn(p):
    x, y = p["x"], -p["y"]
    size, text, c = p["size"], p["text"], p["color"]
    font = (FONT, size, "bold")
    big = (FONT, size + 1, "bold")

    shadow = cv.create_text(
        x + 2 * ZOOM, y + 3 * ZOOM, text=text, font=font, fill=BG
    )
    halo = cv.create_text(x, y, text=text, font=big, fill=BG)
    main = cv.create_text(x, y - LIFT, text=text, font=font, fill=BG)

    p.update(shadow=shadow, halo=halo, main=main,
             f=0, dx=rng.uniform(-10, 10) * ZOOM)
    main_ids.append((main, c))
    active.append(p)


def animate(p):
    p["f"] += 1
    u = clamp(p["f"] / ANIM)
    e = 1 - (1 - u) ** 3
    c = p["color"]
    x, y = p["x"], -p["y"]
    hover = (1 - e) * LIFT
    px = x + p["dx"] * (1 - e)
    py = y - hover

    cv.itemconfig(p["shadow"], fill=hx(mix(BGC, dim(c, 0.30), e)))
    cv.itemconfig(p["halo"], fill=hx(mix(BGC, dim(c, 0.20), e * e)))
    cv.coords(p["halo"], px, py)

    flash = 0.75 * math_sin(clamp((u - 0.55) / 0.45))
    col = mix(mix(BGC, c, e ** 1.5), FLASH, flash)
    cv.itemconfig(p["main"], fill=hx(col))
    cv.coords(p["main"], px, py)

    if u >= 1:
        cv.coords(p["halo"], x, y)
        cv.coords(p["main"], x, y)
        cv.itemconfig(p["main"], fill=hx(c))
        return False
    return True


def math_sin(v):
    return m.sin(m.pi * v)


BGC = tuple(int(BG[i:i + 2], 16) / 255 for i in (1, 3, 5))
gen = 0
ORDER = []
items = iter(())
RATE = 0.0
acc = 0.0
spawning = False


def step(my_gen):
    global spawning, acc
    if my_gen != gen:
        return
    if spawning:
        acc += RATE
        try:
            while acc >= 1:
                acc -= 1
                spawn(next(items))
        except StopIteration:
            spawning = False

    active[:] = [p for p in active if animate(p)]

    if not spawning and not active:
        shimmer(my_gen)
        return
    cv.after(TICK, lambda: step(my_gen))


def _safe(i, c):
    try:
        cv.itemconfig(i, fill=hx(c))
    except Exception:
        pass


def shimmer(my_gen):
    if my_gen != gen or not main_ids:
        return
    for _ in range(1):
        i, c = rng.choice(main_ids)
        _safe(i, mix(c, FLASH, 0.6))
        cv.after(260, lambda i=i, c=c: _safe(i, c))
    cv.after(140, lambda: shimmer(my_gen))


def start():
    global gen, items, acc, spawning, ORDER, RATE
    gen += 1
    main_ids.clear()
    active.clear()
    ORDER = build()
    items = iter(ORDER)
    RATE = len(ORDER) / (DURATION * 1000 / TICK)
    acc = 0.0
    spawning = True
    cv.after(200, lambda: step(gen))


box = [BASE, BASE]
_resize_job = None


def _apply_resize(w, h):
    global _resize_job
    _resize_job = None
    w = max(320, int(w))
    h = max(320, int(h))
    if abs(w - box[0]) <= 2 and abs(h - box[1]) <= 2:
        return
    box[0], box[1] = w, h
    s.setup(w, h)
    apply_zoom(min(w, h - BAR) / BASE)
    cv.delete("all")
    start()


def on_configure(event):
    global _resize_job
    if event.widget is not cv:
        return
    if _resize_job is not None:
        try:
            cv.after_cancel(_resize_job)
        except Exception:
            pass
    _resize_job = cv.after(
        220, lambda w=event.width, h=event.height: _apply_resize(w, h)
    )


def on_submit(_event=None):
    name = entry.get().strip()[:18]
    if not name:
        return
    PHRASES[:] = [f"Love {name}"]
    cv.delete("all")
    start()


def build_ui():
    global entry
    root = cv.winfo_toplevel()
    bar = tk.Frame(root, bg="#1a0810")
    bar.place(x=0, y=0, relwidth=1, height=BAR)

    tk.Label(
        bar, text="Enter U name:", fg="#f0c0c8", bg="#1a0810",
        font=(FONT, 11, "bold")
    ).grid(row=0, column=0, padx=(14, 8), pady=10)

    entry = tk.Entry(
        bar, width=18, font=(FONT, 11, "bold"),
        bg="#2a0d18", fg="#ffe8ec", insertbackground="#ffe8ec",
        relief="flat", bd=4, highlightthickness=1,
        highlightcolor="#e04060", highlightbackground="#5a2030",
    )
    entry.grid(row=0, column=1, pady=10)

    tk.Button(
        bar, text="Show", font=(FONT, 10, "bold"),
        bg="#c02040", fg="white", activebackground="#e04060",
        activeforeground="white", relief="flat", bd=0, padx=16,
        cursor="hand2", command=on_submit,
    ).grid(row=0, column=2, padx=10, pady=10)

    entry.bind("<Return>", on_submit)
    entry.focus_set()


try:
    side = int(BASE * pick_zoom(cv.winfo_screenwidth(), cv.winfo_screenheight()))
    box[0] = box[1] = side
    s.setup(side, side)
    apply_zoom(side / BASE)
    cv.bind("<Configure>", on_configure)
    build_ui()
    start()
    t.done()
except (t.Terminator, Exception):
    pass
