"""Small formatting helpers shared by the test and error reports.

Everything a report prints is plain Markdown, so the same text reads in a
terminal, in a notes app, and — through render.py — as a printable page.
"""

import math

DISCLAIMER = ("*Indicative self-practice estimates, not official scores. "
              "Not affiliated with any exam board.*")

MINUS = "\u2212"   # a real minus sign, so +0.5 and −0.5 line up in a table
BAR = "\u2588"
NO_VALUE = "\u2014"
NONE_IN_CELL = "\u00b7"


def fmt(value, places=2):
    """5.0 -> '5', 4.25 -> '4.25', None -> an em dash."""
    if value is None:
        return NO_VALUE
    if isinstance(value, bool):
        return str(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return NO_VALUE
    if number.is_integer():
        return str(int(number))
    return ("%.*f" % (places, number)).rstrip("0").rstrip(".")


def band(value):
    """Scores on a half-band scale read better with one decimal: 5 -> '5.0'."""
    if value is None:
        return NO_VALUE
    number = float(value)
    if abs(number) < 20 and abs(number * 2 - round(number * 2)) < 1e-9:
        return "%.1f" % number
    return fmt(number)


def signed(delta, places=2):
    """A change with its sign: '+0.5', '−0.5', '=' for no change."""
    if delta is None:
        return ""
    if abs(delta) < 1e-9:
        return "="
    return ("+" if delta > 0 else MINUS) + fmt(abs(delta), places)


def mean(values):
    values = [float(v) for v in values if v is not None]
    return sum(values) / len(values) if values else None


def plural(count, singular, suffix="s"):
    return "%d %s%s" % (count, singular, "" if count == 1 else suffix)


def bar(value, largest, width=16):
    """A proportional bar; anything above zero shows at least one block."""
    if not largest or value <= 0:
        return ""
    return BAR * max(1, int(round(width * float(value) / float(largest))))


def cell(text):
    """Make free text safe inside a Markdown table cell."""
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def table(headers, rows, align=None):
    """A Markdown table. `align` is one of 'l', 'r', 'c' per column."""
    align = align or ["l"] * len(headers)
    rule = {"l": ":---", "r": "---:", "c": ":---:"}
    lines = ["| " + " | ".join(cell(h) for h in headers) + " |",
             "| " + " | ".join(rule.get(a, ":---") for a in align) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(cell(c) for c in row) + " |")
    return "\n".join(lines)


def bold(text):
    return "**%s**" % text


def short_date(ts):
    """'2026-08-25T00:00:00' -> '2026-08-25'."""
    return str(ts or "")[:10]
