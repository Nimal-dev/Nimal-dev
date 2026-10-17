"""Generate cartoon-style SVG cards for the GitHub profile README.

Usage: python -I build.py <path-to-Fredoka-variable.ttf> <output-dir>
"""
import base64
import io
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

FONT_PATH = Path(sys.argv[1])
OUT = Path(sys.argv[2])
STATIC = "--static" in sys.argv
OUT.mkdir(parents=True, exist_ok=True)

# ---- design tokens (from src/styles/global.css) --------------------------
PAPER = "#eef6ff"
PAPER2 = "#e3effd"
WHITE = "#ffffff"
INK = "#17162b"
MUTED = "#4d4f6b"
YELLOW = "#ffd23f"
YELLOW_SOFT = "#fff1b8"
ORANGE = "#ff5e3a"
BLUE = "#2e7cf6"
BLUE_TEXT = "#1f5fd0"
BLUE_SOFT = "#d8e7ff"
LIME = "#7ed957"
LIME_SOFT = "#e2f8d5"
VIOLET = "#9b5de5"
VIOLET_SOFT = "#ece2ff"

SHAPES = {
    "star": '<path d="M50 4l12 30 32 2-25 20 9 31-28-18-28 18 9-31L6 36l32-2z"/>',
    "blob": '<path d="M28 12c18-14 50-10 60 10s16 48-4 62-54 14-70-4S10 26 28 12z"/>',
    "squiggle": '<path d="M4 50c14-30 28-30 42 0s28 30 42 0 28-30 42 0" fill="none" stroke-width="9"/>',
    "bolt": '<path d="M58 4L18 56h26l-8 40 46-56H56z"/>',
    "cloud": '<path d="M28 76a18 18 0 0 1-4-35 24 24 0 0 1 46-8 18 18 0 0 1 22 26 14 14 0 0 1-8 17z"/>',
    "ring": '<circle cx="50" cy="50" r="36" fill="none" stroke-width="10"/>',
    "sparkle": '<path d="M50 6c4 26 18 40 44 44-26 4-40 18-44 44-4-26-18-40-44-44 26-4 40-18 44-44z"/>',
    "heart": '<path d="M50 88C20 66 6 50 6 32A20 20 0 0 1 50 20a20 20 0 0 1 44 12c0 18-14 34-44 56z"/>',
}

# ---- font: static instances for measuring + per-file subsets ------------
_var = TTFont(FONT_PATH)
_instances = {}


def instance(weight):
    if weight not in _instances:
        f = TTFont(FONT_PATH)
        _instances[weight] = instancer.instantiateVariableFont(f, {"wght": weight, "wdth": 100})
    return _instances[weight]


def measure(text, size, weight):
    f = instance(weight)
    cmap = f.getBestCmap()
    hmtx = f["hmtx"]
    upm = f["head"].unitsPerEm
    total = 0
    for ch in text:
        g = cmap.get(ord(ch)) or cmap.get(ord("?"))
        total += hmtx[g][0]
    return total * size / upm


def font_face(weight, chars):
    f = instance(weight)
    buf = io.BytesIO()
    f.save(buf)
    buf.seek(0)
    sub = TTFont(buf)
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga"]
    opts.hinting = False
    subsetter = subset.Subsetter(opts)
    subsetter.populate(text="".join(sorted(set(chars))) + " ?")
    subsetter.subset(sub)
    out = io.BytesIO()
    sub.flavor = "woff2"
    sub.save(out)
    b64 = base64.b64encode(out.getvalue()).decode()
    return (
        f"@font-face{{font-family:'Fredoka';font-weight:{weight};font-style:normal;"
        f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
    )


# ---- svg builder ---------------------------------------------------------
class Svg:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.body = []
        self.chars = {}  # weight -> set of chars
        self.css = []

    def use_text(self, text, weight):
        self.chars.setdefault(weight, set()).update(text)

    def add(self, s):
        self.body.append(s)

    def text(self, x, y, s, size, weight=500, fill=INK, anchor="start", extra="", cls=""):
        self.use_text(s, weight)
        s = esc(s)
        return (
            f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}" class="{cls}" {extra}>{s}</text>'
        )

    def render(self, bg=None, border=True, radius=28, shadow=10, pad_shadow=True):
        faces = "".join(font_face(w, c) for w, c in self.chars.items())
        css = BASE_CSS + "".join(self.css) + (STATIC_CSS if STATIC else "")
        W, H = self.w, self.h
        head = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
            f'font-family="Fredoka, \'Segoe UI\', system-ui, sans-serif">'
            f"<defs><style>{faces}{css}</style>"
            f'<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">'
            f'<circle cx="2" cy="2" r="1.6" fill="{INK}" opacity="0.12"/></pattern>'
            f'<clipPath id="clip"><rect x="2" y="2" width="{W - shadow - 4}" height="{H - shadow - 4}" rx="{radius}"/></clipPath>'
            f"</defs>"
        )
        frame = ""
        if border:
            iw, ih = W - shadow - 4, H - shadow - 4
            frame = (
                f'<rect x="{2 + shadow}" y="{2 + shadow}" width="{iw}" height="{ih}" rx="{radius}" fill="{INK}"/>'
                f'<rect x="2" y="2" width="{iw}" height="{ih}" rx="{radius}" fill="{bg or PAPER}" stroke="{INK}" stroke-width="4"/>'
                f'<rect x="2" y="2" width="{iw}" height="{ih}" rx="{radius}" fill="url(#dots)" clip-path="url(#clip)"/>'
            )
        return head + frame + "".join(self.body) + "</svg>"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


STATIC_CSS = ".pop,.rise,.draw,.float,.spin,.wiggle{animation:none!important;opacity:1!important;transform:none!important;stroke-dashoffset:0!important}.cycle{animation:none!important;opacity:0!important}.cycle.first{opacity:1!important}"
BASE_CSS = """
text{font-family:'Fredoka','Segoe UI',system-ui,sans-serif;}
.float{animation:float var(--d,4s) ease-in-out infinite;animation-delay:var(--dl,0s);transform-box:fill-box;transform-origin:center;}
.spin{animation:spin 14s linear infinite;transform-box:fill-box;transform-origin:center;}
.pop{opacity:0;transform:scale(0.2) translateY(30px);animation:pop .7s cubic-bezier(.34,1.56,.64,1) forwards;animation-delay:var(--dl,0s);transform-box:fill-box;transform-origin:center;}
.rise{opacity:0;transform:translateY(22px);animation:rise .6s cubic-bezier(.22,1,.36,1) forwards;animation-delay:var(--dl,0s);transform-box:fill-box;transform-origin:center;}
.wiggle{animation:wiggle 3.2s ease-in-out infinite;animation-delay:var(--dl,0s);transform-box:fill-box;transform-origin:center;}
.draw{stroke-dasharray:1200;stroke-dashoffset:1200;animation:draw 1.4s cubic-bezier(.22,1,.36,1) forwards;animation-delay:var(--dl,.4s);}
.blink{animation:blink 1.1s steps(2,start) infinite;}
.cycle{opacity:0;animation:cycle 9.6s ease-in-out infinite;animation-delay:var(--dl,0s);}
@keyframes float{0%,100%{transform:translateY(0) rotate(var(--r,0deg))}50%{transform:translateY(-12px) rotate(calc(var(--r,0deg) + 4deg))}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes pop{to{opacity:1;transform:scale(1) translateY(0)}}
@keyframes rise{to{opacity:1;transform:translateY(0)}}
@keyframes wiggle{0%,100%{transform:rotate(-4deg)}50%{transform:rotate(4deg)}}
@keyframes draw{to{stroke-dashoffset:0}}
@keyframes blink{to{opacity:0}}
@keyframes cycle{0%,1%{opacity:0;transform:translateY(8px)}4%,22%{opacity:1;transform:translateY(0)}25%,100%{opacity:0;transform:translateY(-8px)}}
"""


def doodle(shape, x, y, size, fill, delay=0.0, dur=4.0, rot=0, spin=False, stroke=5):
    inner_cls = "spin" if spin else "float"
    return (
        f'<g transform="translate({x} {y})"><g class="{inner_cls}" style="--dl:{delay}s;--d:{dur}s;--r:{rot}deg">'
        f'<svg viewBox="0 0 100 100" width="{size}" height="{size}" fill="{fill}" stroke="{INK}" stroke-width="{stroke}" '
        f'stroke-linejoin="round" stroke-linecap="round">{SHAPES[shape]}</svg></g></g>'
    )


def box(x, y, w, h, fill, r=16, shadow=6, stroke=4, extra=""):
    return (
        f'<rect x="{x + shadow}" y="{y + shadow}" width="{w}" height="{h}" rx="{r}" fill="{INK}"/>'
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{INK}" stroke-width="{stroke}" {extra}/>'
    )


def pill(svg, x, y, label, fill, size=22, weight=600, color=INK, padx=18, h=None, shadow=5, rot=0, cls="", delay=0.0, r=None):
    """Sticker pill. Returns (markup, width)."""
    tw = measure(label, size, weight)
    w = tw + padx * 2
    h = h or size * 1.9
    r = r if r is not None else h / 2
    inner = box(0, 0, w, h, fill, r=r, shadow=shadow) + svg.text(
        w / 2, h / 2 + size * 0.36, label, size, weight, color, "middle"
    )
    wrap = f'<g transform="translate({x} {y}) rotate({rot})"><g class="{cls}" style="--dl:{delay}s">{inner}</g></g>'
    return wrap, w


def wrap_text(text, size, weight, max_w):
    words = text.split()
    lines, cur = [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if measure(trial, size, weight) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def paragraph(svg, x, y, text, size, weight, fill, max_w, lh=1.4, cls="", delay=0.0):
    out, yy = [], y
    for ln in wrap_text(text, size, weight, max_w):
        out.append(svg.text(x, yy, ln, size, weight, fill, cls=cls, extra=f'style="--dl:{delay}s"'))
        yy += size * lh
    return "".join(out), yy


def letters(svg, x, y, word, size, weight, fill, delay0=0.0, step=0.06):
    """Each letter is its own <text> so it can pop in independently."""
    out, xx = [], x
    for i, ch in enumerate(word):
        out.append(
            svg.text(xx, y, ch, size, weight, fill, cls="pop", extra=f'style="--dl:{delay0 + i * step}s"')
        )
        xx += measure(ch, size, weight)
    return "".join(out), xx


def save(name, markup):
    p = OUT / name
    p.write_text(markup, encoding="utf-8")
    print(f"{name:28s} {p.stat().st_size / 1024:6.1f} KB")


# =========================================================================
# HERO
# =========================================================================
def hero():
    W, H = 1200, 610
    s = Svg(W, H)

    # doodles (background layer)
    s.add(doodle("cloud", 440, 48, 110, WHITE, 0.2, 5))
    s.add(doodle("star", 700, 36, 72, YELLOW, 0.8, 4.2, rot=12))
    s.add(doodle("ring", 600, 180, 80, "none", 0.4, 4.6))
    s.add(doodle("squiggle", 630, 250, 140, "none", 1.0, 5.2, stroke=9))
    s.add(doodle("bolt", 560, 318, 54, ORANGE, 0.6, 3.8, rot=-10))
    s.add(doodle("blob", 1040, 16, 140, LIME, 0.0, 6))
    s.add(doodle("sparkle", 1088, 500, 48, BLUE, 1.2, 4, spin=True))

    # "Hi, I'm" sticker
    m, _ = pill(s, 60, 54, "Hi, I'm", BLUE, size=22, weight=600, color=WHITE, rot=-4, cls="pop", delay=0.1)
    s.add(m)

    # Name
    m, _ = letters(s, 56, 230, "Nimal", 150, 700, INK, delay0=0.25, step=0.07)
    s.add(m)
    m, _ = letters(s, 56, 370, "Prince", 150, 700, BLUE, delay0=0.6, step=0.07)
    s.add(m)

    # Subtitle with cycling word
    size = 26
    lead = "I build"
    s.add(s.text(60, 428, lead, size, 400, MUTED, cls="rise", extra='style="--dl:1.1s"'))
    lx = 60 + measure(lead + " ", size, 400)
    words = ["iPhone apps", "web platforms", "things that help people", "Gate Track"]
    pw = max(measure(w, 24, 600) for w in words) + 36
    ph = 42
    s.add(f'<g class="rise" style="--dl:1.2s">{box(lx, 428 - 31, pw, ph, YELLOW, r=14, shadow=4)}')
    for i, w in enumerate(words):
        s.add(
            s.text(lx + pw / 2, 428, w, 24, 600, INK, "middle", cls="cycle first" if i == 0 else "cycle", extra=f'style="--dl:{i * 2.4}s"')
        )
    s.add("</g>")
    tail = "as an iOS engineer at Infilect"
    s.add(s.text(lx + pw + 12, 428, tail, size, 400, MUTED, cls="rise", extra='style="--dl:1.15s"'))
    s.add(s.text(60, 466, "Technologies and the founder of Gate Track.", size, 400, MUTED, cls="rise", extra='style="--dl:1.2s"'))

    # Buttons
    m, w1 = pill(s, 60, 492, "See the work  ↓", YELLOW, size=21, weight=600, h=50, r=25, shadow=5, cls="pop", delay=1.35)
    s.add(m)
    m, w2 = pill(s, 60 + w1 + 16, 492, "Portfolio  ↗", WHITE, size=21, weight=600, h=50, r=25, shadow=5, cls="pop", delay=1.45)
    s.add(m)
    m, _ = pill(s, 60 + w1 + w2 + 32, 492, "Gate Track  ↗", BLUE_SOFT, size=21, weight=600, color=BLUE_TEXT, h=50, r=25, shadow=5, cls="pop", delay=1.55)
    s.add(m)

    # Right-now card
    cx, cy, cw, ch = 800, 196, 340, 344
    s.add(f'<g class="pop" style="--dl:0.9s">{box(cx, cy, cw, ch, WHITE, r=24, shadow=8)}')
    m, _ = pill(s, cx + 14, cy - 22, "Right now", ORANGE, size=18, weight=600, color=WHITE, h=38, shadow=4, rot=-5, cls="wiggle", padx=16)
    s.add(m)
    tx = cx + 26
    yy = cy + 54
    s.add(s.text(tx, yy, "Working as", 15, 500, MUTED))
    yy += 26
    m, yy = paragraph(s, tx, yy, "iOS Engineer Intern at Infilect Technologies", 20, 600, INK, cw - 52, lh=1.25)
    yy += 12
    s.add(s.text(tx, yy, "Founder of", 15, 500, MUTED))
    yy += 12
    m2, gw = pill(s, tx, yy, "Gate Track  ↗", WHITE, size=18, weight=600, color=INK, h=38, shadow=0, padx=16)
    s.add(m2.replace(f'fill="{WHITE}" stroke="{INK}" stroke-width="4"', f'fill="{WHITE}" stroke="{BLUE}" stroke-width="3"'))
    s.add(m)
    yy += 38 + 30
    s.add(s.text(tx, yy, "Graduated", 15, 500, MUTED))
    yy += 26
    m, yy = paragraph(s, tx, yy, "B.Tech in Computer Science and Engineering, 2026", 19, 600, INK, cw - 52, lh=1.25)
    s.add(m)
    yy += 4
    s.add(f'<line x1="{tx}" y1="{yy}" x2="{cx + cw - 26}" y2="{yy}" stroke="{INK}" stroke-width="2" stroke-dasharray="6 6" opacity=".6"/>')
    yy += 30
    s.add(s.text(tx, yy, "Kerala, India", 16, 500, MUTED))
    s.add("</g>")

    save("hero.svg", s.render())


# =========================================================================
# SECTION TITLE STICKERS
# =========================================================================
def section(name, label, fill, color=INK, shape="star", shape_fill=YELLOW):
    size = 34
    tw = measure(label, size, 700)
    W = int(tw + 180)
    H = 96
    s = Svg(W, H)
    s.add(doodle(shape, 14, 12, 56, shape_fill, 0.3, 3.6, rot=-8))
    m, pw = pill(s, 82, 18, label, fill, size=size, weight=700, color=color, h=60, r=20, shadow=7, padx=26, cls="pop", delay=0.05)
    s.add(m)
    # squiggle underline that draws itself
    ux = 82
    s.add(
        f'<path class="draw" d="M{ux} {H - 8} q 20 -10 40 0 t 40 0 t 40 0 t 40 0" fill="none" stroke="{BLUE}" stroke-width="5" stroke-linecap="round"/>'
    )
    save(f"section-{name}.svg", s.render(border=False))


# =========================================================================
# ABOUT CARD
# =========================================================================
def about():
    W, H = 1200, 500
    s = Svg(W, H)
    s.add(doodle("heart", 1050, 40, 70, ORANGE, 0.5, 4.4, rot=8))
    s.add(doodle("sparkle", 1120, 300, 54, YELLOW, 0.2, 4, spin=True))
    s.add(doodle("ring", 1000, 390, 60, "none", 0.9, 5))
    title = "Software engineer from Kerala who likes building tech that helps people"
    m, yy = paragraph(s, 54, 78, title, 34, 700, INK, 860, lh=1.2, cls="rise", delay=0.1)
    s.add(m)
    bullets = [
        (BLUE, "iOS Engineer Intern at Infilect Technologies, shipping native Swift and SwiftUI screens from design review to the App Store."),
        (ORANGE, "Founder of Gate Track, a Flutter app that crowdsources railway-gate timings so nobody gets stuck at a closed crossing."),
        (YELLOW, "B.Tech in Computer Science and Engineering, class of 2026, UKF College of Engineering and Technology."),
        (LIME, "Two years of full-stack client work before iOS: React and Node platforms, Flutter apps, and LLM-backed tools at Logiprompt."),
        (VIOLET, "I care about interfaces that feel considered, code that stays readable, and products that solve a real problem."),
    ]
    yy += 18
    for i, (col, txt) in enumerate(bullets):
        d = 0.3 + i * 0.12
        s.add(f'<g class="rise" style="--dl:{d}s">')
        s.add(f'<rect x="54" y="{yy - 16}" width="18" height="18" rx="5" fill="{col}" stroke="{INK}" stroke-width="3" transform="rotate(-8 63 {yy - 7})"/>')
        m, yy = paragraph(s, 86, yy, txt, 20, 500, MUTED, 860, lh=1.3)
        s.add(m + "</g>")
        yy += 10
    save("about.svg", s.render())


# =========================================================================
# PROJECT CARDS
# =========================================================================
def project(name, title, tag, tag_fill, desc, tech, cta, accent, W=580, H=300, big=False, shape="star", shape_fill=YELLOW):
    s = Svg(W, H)
    pad = 36
    # accent strip at the top
    s.add(f'<rect x="4" y="4" width="{W - 16}" height="14" rx="12" fill="{accent}" stroke="{INK}" stroke-width="4" clip-path="url(#clip)"/>')
    s.add(doodle(shape, W - 110, 34, 64, shape_fill, 0.4, 4.2, rot=10))
    tsize = 40 if big else 30
    s.add(s.text(pad, 78 if big else 70, title, tsize, 700, INK, cls="rise", extra='style="--dl:.05s"'))
    tx = pad + measure(title, tsize, 700) + 16
    m, _ = pill(s, tx, (78 if big else 70) - 26, tag, tag_fill, size=15, weight=600, color=INK if tag_fill in (YELLOW, LIME, WHITE, BLUE_SOFT, YELLOW_SOFT) else WHITE, h=32, shadow=3, padx=12, cls="pop", delay=0.3)
    s.add(m)
    m, yy = paragraph(s, pad, 120 if big else 108, desc, 21 if big else 19, 400, MUTED, W - pad * 2 - 20, lh=1.35, cls="rise", delay=0.15)
    s.add(m)
    # tech chips
    yy += 6
    xx = pad
    for i, t in enumerate(tech):
        cw = measure(t, 15, 600) + 22
        if xx + cw > W - pad - 150:
            xx = pad
            yy += 38
        s.add(f'<g class="pop" style="--dl:{0.35 + i * 0.05}s">')
        s.add(box(xx, yy - 12, cw, 30, WHITE, r=10, shadow=3, stroke=3))
        s.add(s.text(xx + cw / 2, yy + 9, t, 15, 600, INK, "middle"))
        s.add("</g>")
        xx += cw + 10
    # CTA button bottom-right
    m, bw = pill(s, 0, 0, cta, accent if accent not in (YELLOW,) else YELLOW, size=18, weight=600, color=INK if accent in (YELLOW, LIME, YELLOW_SOFT, BLUE_SOFT) else WHITE, h=46, r=23, shadow=5, padx=20, cls="pop", delay=0.5)
    m = m.replace('translate(0 0)', f'translate({W - 16 - pad - bw} {H - 16 - pad - 46})')
    s.add(m)
    save(f"project-{name}.svg", s.render(bg=WHITE))


# =========================================================================
# CONNECT CARD + FOOTER
# =========================================================================
def connect():
    W, H = 1200, 300
    s = Svg(W, H)
    s.add(doodle("cloud", 920, 30, 110, WHITE, 0.2, 5))
    s.add(doodle("star", 1080, 160, 70, YELLOW, 0.6, 4, rot=14))
    s.add(doodle("bolt", 860, 180, 56, ORANGE, 0.9, 3.8, rot=-12))
    m, _ = pill(s, 54, 46, "Let's talk", ORANGE, size=20, weight=600, color=WHITE, h=42, shadow=4, rot=-4, cls="wiggle", padx=16)
    s.add(m)
    m, yy = paragraph(s, 54, 136, "Building something for iOS, or a product that needs a full-stack hand?", 36, 700, INK, 780, lh=1.15, cls="rise", delay=0.1)
    s.add(m)
    s.add(s.text(54, yy + 10, "Drop me a line. I reply fastest on LinkedIn and email.", 22, 400, MUTED, cls="rise", extra='style="--dl:.25s"'))
    save("connect.svg", s.render())


def footer():
    W, H = 1200, 150
    s = Svg(W, H)
    for i, (shape, fill, x) in enumerate(
        [("star", YELLOW, 40), ("cloud", WHITE, 150), ("heart", ORANGE, 290), ("sparkle", BLUE, 400), ("blob", LIME, 1060), ("bolt", ORANGE, 960), ("sparkle", YELLOW, 880)]
    ):
        s.add(doodle(shape, x, 40, 60, fill, i * 0.3, 4 + i * 0.3, rot=i * 6, spin=shape == "sparkle"))
    m, w = pill(s, 0, 0, "Thanks for stopping by!", YELLOW, size=30, weight=700, h=66, r=22, shadow=7, padx=30, cls="pop", delay=0.1)
    m = m.replace("translate(0 0)", f"translate({(W - w) / 2} 40)")
    s.add(m)
    save("footer.svg", s.render(border=False))


# =========================================================================
if __name__ == "__main__":
    hero()
    section("heatmap", "Contribution heat map", LIME, shape="sparkle", shape_fill=BLUE)
    section("about", "About me", YELLOW, shape="cloud", shape_fill=WHITE)
    section("projects", "Featured projects", BLUE, color=WHITE, shape="bolt", shape_fill=ORANGE)
    section("stack", "Tech stack", VIOLET_SOFT, shape="ring", shape_fill="none")
    section("stats", "GitHub stats", ORANGE, color=WHITE, shape="star", shape_fill=YELLOW)
    section("connect", "Let's connect", LIME_SOFT, shape="heart", shape_fill=ORANGE)
    about()
    project(
        "gatetrack", "Gate Track", "Founder", YELLOW,
        "Never get stuck at a closed railway gate again. Live level-crossing status, crowdsourced gate timings, geofenced alerts as you approach a crossing, and a prediction of when the next gate will drop. Live on Android, iOS coming later.",
        ["Flutter", "Dart", "Firebase", "flutter_map", "Node.js", "MongoDB", "Geofencing"],
        "Get it on Google Play  ↗", LIME, W=1200, H=330, big=True, shape="bolt", shape_fill=ORANGE,
    )
    project(
        "leaseguard", "LeaseGuard", "AI product", VIOLET,
        "AI rental-agreement analyzer. Upload a lease, get red flags, a plain-English summary, a fairness score, and a chat that answers questions about your document.",
        ["Next.js 15", "FastAPI", "Groq", "Llama 3.3", "MongoDB"],
        "Case study  ↗", VIOLET, shape="sparkle", shape_fill=VIOLET,
    )
    project(
        "schoolmart", "SchoolMart", "MERN", LIME,
        "Marketplace connecting schools with verified vendors: role-based access, inventory, order tracking, and Razorpay payments.",
        ["React", "Node.js", "Express", "MongoDB", "Razorpay"],
        "View code  ↗", LIME, shape="star", shape_fill=YELLOW,
    )
    project(
        "codetoflow", "CodeToFlow", "Dev tool", BLUE,
        "Paste code, get an interactive Mermaid flowchart plus a spaghetti score for how tangled the logic is. Built for onboarding onto unfamiliar codebases.",
        ["React", "Vite", "Groq", "Mermaid.js"],
        "Prototype  ↗", BLUE, shape="ring", shape_fill="none",
    )
    project(
        "portfolio", "Portfolio v2", "Live", ORANGE,
        "My cartoon-style portfolio: ink outlines, hard shadows, letter-pop animations, floating doodles, and zero WebGL. Every word lives in one data file.",
        ["React 19", "Vite", "Framer Motion", "Lenis"],
        "Visit site  ↗", ORANGE, shape="cloud", shape_fill=WHITE,
    )
    project(
        "traffic", "Kerala Traffic Prediction", "ML", YELLOW,
        "Notebooks that forecast traffic density on Kerala routes from historical data, with feature engineering and model comparison.",
        ["Python", "Pandas", "scikit-learn", "Jupyter"],
        "View code  ↗", YELLOW, shape="bolt", shape_fill=ORANGE,
    )
    project(
        "ektha", "EKTHA 2025", "Live", BLUE_SOFT,
        "Festival site for UKF's techno-cultural fest: event discovery, schedule, and a high-energy visual design built for students.",
        ["React", "Netlify"],
        "Visit site  ↗", BLUE, shape="heart", shape_fill=ORANGE,
    )
    connect()
    footer()
