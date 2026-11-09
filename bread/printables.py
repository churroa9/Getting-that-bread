"""Printable product generator.

Generates print-ready SVG pages (US Letter or A4) for digital downloads you
can sell on Etsy, Gumroad, Payhip, etc.: habit trackers, weekly planners,
budget sheets and monthly calendars. Open any SVG in a browser and print
to PDF, or bundle them as-is.

Each generator takes a theme, so one design becomes many listings
(e.g. "Sage Habit Tracker", "Blush Habit Tracker", ...).
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

# Page sizes in points (1/72 inch).
PAGES = {"letter": (612, 792), "a4": (595, 842)}


@dataclass(frozen=True)
class Theme:
    name: str
    ink: str
    accent: str
    soft: str
    font: str = "Georgia, 'Times New Roman', serif"


THEMES: dict[str, Theme] = {
    "minimal": Theme("minimal", "#222222", "#222222", "#f2f2f2", "Helvetica, Arial, sans-serif"),
    "sage": Theme("sage", "#2f3b33", "#7d9a83", "#e8efe9"),
    "blush": Theme("blush", "#4a3337", "#d29a9f", "#f8eaeb"),
    "ocean": Theme("ocean", "#1e3346", "#4f86a8", "#e5eff5", "Helvetica, Arial, sans-serif"),
    "sand": Theme("sand", "#3e352a", "#c19a6b", "#f5eee4"),
}


class _Svg:
    def __init__(self, page: str, theme: Theme):
        self.w, self.h = PAGES[page]
        self.t = theme
        self.parts: list[str] = []

    def rect(self, x, y, w, h, fill="none", stroke=None, sw=0.75, rx=0):
        s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"{s}/>')

    def line(self, x1, y1, x2, y2, stroke=None, sw=0.5):
        self.parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                          f'stroke="{stroke or self.t.accent}" stroke-width="{sw}"/>')

    def circle(self, cx, cy, r, stroke=None):
        self.parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="none" '
                          f'stroke="{stroke or self.t.accent}" stroke-width="0.75"/>')

    def text(self, x, y, s, size=10, anchor="start", weight="normal", fill=None, spacing=0):
        self.parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" '
            f'font-weight="{weight}" letter-spacing="{spacing}" fill="{fill or self.t.ink}">{escape(s)}</text>')

    def title(self, s, sub=""):
        self.text(self.w / 2, 70, s.upper(), size=22, anchor="middle", spacing=4)
        self.line(self.w / 2 - 40, 82, self.w / 2 + 40, 82, sw=1.5)
        if sub:
            self.text(self.w / 2, 100, sub, size=10, anchor="middle", fill=self.t.accent, spacing=1.5)

    def render(self) -> str:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}pt" height="{self.h}pt" '
                f'viewBox="0 0 {self.w} {self.h}" font-family="{self.t.font}">'
                f'<rect width="100%" height="100%" fill="#ffffff"/>' + "".join(self.parts) + "</svg>")


def habit_tracker(theme: Theme, page: str = "letter", habits: int = 15, days: int = 31,
                  title: str = "Habit Tracker") -> str:
    s = _Svg(page, theme)
    s.title(title, "MONTH: ________________")
    m = 40
    label_w = 120
    top = 130
    cell = (s.w - 2 * m - label_w) / days
    row_h = (s.h - top - 110) / habits
    for d in range(days):
        s.text(m + label_w + cell * d + cell / 2, top - 6, str(d + 1), size=6.5, anchor="middle")
    for r in range(habits):
        y = top + r * row_h
        if r % 2 == 0:
            s.rect(m, y, s.w - 2 * m, row_h, fill=theme.soft)
        s.line(m + 4, y + row_h - 5, m + label_w - 8, y + row_h - 5, sw=0.4)
        for d in range(days):
            s.circle(m + label_w + cell * d + cell / 2, y + row_h / 2, min(cell, row_h) * 0.32)
    s.text(m, s.h - 70, "NOTES", size=9, weight="bold", spacing=2)
    for i in range(2):
        s.line(m, s.h - 50 + i * 18, s.w - m, s.h - 50 + i * 18)
    return s.render()


def weekly_planner(theme: Theme, page: str = "letter", title: str = "Weekly Planner") -> str:
    s = _Svg(page, theme)
    s.title(title, "WEEK OF: ________________")
    m, top, gap = 40, 125, 10
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    col_w = (s.w - 2 * m - gap) / 2
    box_h = (s.h - top - m - 3 * gap) / 4
    boxes = days + ["Priorities"]
    for i, name in enumerate(boxes):
        x = m + (i % 2) * (col_w + gap)
        y = top + (i // 2) * (box_h + gap)
        s.rect(x, y, col_w, box_h, fill=theme.soft if name == "Priorities" else "none",
               stroke=theme.accent, rx=6)
        s.text(x + 10, y + 18, name.upper(), size=9, weight="bold", spacing=2)
        ly = y + 36
        while ly < y + box_h - 8:
            if name == "Priorities":
                s.rect(x + 10, ly - 8, 8, 8, stroke=theme.accent)
                s.line(x + 24, ly, x + col_w - 10, ly, sw=0.4)
            else:
                s.line(x + 10, ly, x + col_w - 10, ly, sw=0.4)
            ly += 18
    return s.render()


def budget_sheet(theme: Theme, page: str = "letter", title: str = "Monthly Budget") -> str:
    s = _Svg(page, theme)
    s.title(title, "MONTH: ________________")
    m, top = 40, 125
    sections = [("Income", 4), ("Fixed Expenses", 8), ("Variable Expenses", 8), ("Savings & Debt", 4)]
    row = 18
    cols = [("Item", 0), ("Planned", 0.58), ("Actual", 0.79)]
    width = s.w - 2 * m
    y = top
    for name, rows in sections:
        s.rect(m, y, width, row + 2, fill=theme.accent)
        for label, frac in cols:
            s.text(m + 8 + width * frac, y + 14, (name if label == "Item" else label).upper(),
                   size=8.5, weight="bold", fill="#ffffff", spacing=1.5)
        y += row + 2
        for r in range(rows):
            if r % 2:
                s.rect(m, y, width, row, fill=theme.soft)
            for _, frac in cols[1:]:
                s.line(m + width * frac, y, m + width * frac, y + row, sw=0.4)
            y += row
        s.line(m, y, m + width, y, sw=0.75)
        y += 12
    s.rect(m, y, width, 40, stroke=theme.accent, rx=6)
    s.text(m + 12, y + 24, "LEFT OVER  =  INCOME  −  EXPENSES  −  SAVINGS:", size=9, weight="bold", spacing=1)
    s.line(m + width * 0.62, y + 26, m + width - 14, y + 26, sw=0.6)
    return s.render()


def monthly_calendar(theme: Theme, year: int, month: int, page: str = "letter",
                     sunday_first: bool = True) -> str:
    s = _Svg(page, theme)
    s.title(calendar.month_name[month], str(year))
    m, top = 36, 140
    cal = calendar.Calendar(firstweekday=6 if sunday_first else 0)
    weeks = cal.monthdayscalendar(year, month)
    names = list(calendar.day_abbr)
    names = names[6:] + names[:6] if sunday_first else names
    cw = (s.w - 2 * m) / 7
    ch = (s.h - top - m) / len(weeks)
    for i, n in enumerate(names):
        s.text(m + cw * i + cw / 2, top - 10, n.upper(), size=8.5, anchor="middle", weight="bold", spacing=2)
    for wi, week in enumerate(weeks):
        for di, day in enumerate(week):
            x, y = m + cw * di, top + ch * wi
            s.rect(x, y, cw, ch, fill=theme.soft if day == 0 else "none", stroke=theme.accent, sw=0.5)
            if day:
                s.text(x + 6, y + 14, str(day), size=10)
    return s.render()


PRODUCTS = {
    "habit-tracker": habit_tracker,
    "weekly-planner": weekly_planner,
    "budget": budget_sheet,
}


def build_bundle(out_dir: str | Path, themes: list[str] | None = None, page: str = "letter",
                 year: int | None = None) -> list[Path]:
    """Write every product in every theme, plus a 12-month calendar if year is given."""
    out = Path(out_dir)
    written: list[Path] = []
    for tname in themes or list(THEMES):
        theme = THEMES[tname]
        tdir = out / tname
        tdir.mkdir(parents=True, exist_ok=True)
        for pname, fn in PRODUCTS.items():
            p = tdir / f"{pname}-{page}.svg"
            p.write_text(fn(theme, page=page))
            written.append(p)
        if year:
            for mo in range(1, 13):
                p = tdir / f"calendar-{year}-{mo:02d}-{page}.svg"
                p.write_text(monthly_calendar(theme, year, mo, page=page))
                written.append(p)
    return written
