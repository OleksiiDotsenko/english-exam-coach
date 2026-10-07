#!/usr/bin/env python3
"""Turn a Markdown report or practice sheet into one printable HTML page.

Reports and worksheets are written as Markdown because it reads anywhere. A
learner or a tutor often wants paper, or a PDF to send. This writes a single
self-contained HTML file laid out for print: open it in any browser and print
it, or choose "Save as PDF" in the print dialog.

  render.py sheet.md                   -> sheet.html, next to it
  render.py sheet.md --no-key          the learner's copy, answer key left out
  render.py catalog.md --landscape     wide tables
  render.py sheet.md --lang uk -o out/sheet.html

The page loads nothing: no scripts, no fonts, no images, no links to style
sheets. Everything in the source is escaped, so raw HTML in a report can
never run. No PDF is produced here and no other program is started.

Markdown understood (deliberately a subset):

  # to ####          headings
  **bold** *italic* `code` ~~struck out~~ ==highlighted== [text](https://…)
  - item / 1. item   lists, nested by indentation; "- [ ]" is a tick box
  | a | b |          tables, with :--- / ---: / :---: alignment
  > note             a boxed note
  ```                a block kept exactly as typed (gapped texts, dialogues)
  ---                a rule            ____   (underscores only) a writing line
  <!-- pagebreak --> start a new page
  <!-- key -->       the answer key starts here: new page; --no-key drops it

Underscores are never emphasis, so a blank like ______ or fr_ _ _ survives.
A new line in the source is a new line on the page (use --wrap to reflow
text that was hard-wrapped instead).
"""

import argparse
import html
import re
import sys
from pathlib import Path

import fileguard

PAPER = {"a4": "A4", "letter": "letter"}
BODY_WIDTH = {("a4", False): "180mm", ("a4", True): "267mm",
              ("letter", False): "186mm", ("letter", True): "249mm"}

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d{1,9}[.)])\s+(.*)$")
RULE = re.compile(r"^\s*([-*])(\s*\1){2,}\s*$")
WRITE_LINE = re.compile(r"^\s*_{3,}\s*$")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
TABLE_RULE = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
COMMENT = re.compile(r"^\s*<!--(.*?)-->\s*$")
CHECKBOX = re.compile(r"^\[([ xX])\]\s+(.*)$", re.DOTALL)
PAGE_BREAK_WORDS = ("pagebreak", "page-break", "page break", "newpage")
KEY_OPEN_WORDS = ("key", "answers", "answer key")
KEY_CLOSE_WORDS = ("/key", "/answers", "/answer key")
SAFE_SCHEMES = ("http", "https", "mailto")


# ---- inline ------------------------------------------------------------

class Stash:
    """Finished fragments parked out of reach of the later substitutions."""

    def __init__(self):
        self.items = []

    def put(self, fragment):
        self.items.append(fragment)
        return "\x00%d\x00" % (len(self.items) - 1)

    def restore(self, text):
        return re.sub(r"\x00(\d+)\x00", lambda m: self.items[int(m.group(1))], text)


def safe_url(url):
    """Only ordinary web and mail links, and plain relative paths, become
    links; anything else stays text.

    Browsers are forgiving in ways that matter here: they strip control
    characters from the front of an address and read a backslash as a slash,
    so "\x01javascript:…" and "\\\\host\\share" are refused outright.
    """
    if not url or "\\" in url or any(ord(ch) < 0x21 or ord(ch) == 0x7F for ch in url):
        return False
    scheme = re.match(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):", url)
    if scheme:
        return scheme.group(1).lower() in SAFE_SCHEMES
    if url.startswith("//"):
        return False
    # No scheme: a colon before the first slash would still be read as one.
    return ":" not in re.split(r"[/?#]", url, 1)[0]


def inline(text):
    """One line of Markdown text -> HTML. Everything not markup is escaped."""
    stash = Stash()
    text = text.replace("\x00", "")

    def code_span(match):
        body = match.group(2).replace("\\|", "|").strip()
        return stash.put("<code>%s</code>" % html.escape(body, quote=False))

    text = re.sub(r"(`+)(.+?)\1", code_span, text)
    text = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|~>=])",
                  lambda m: stash.put(html.escape(m.group(1), quote=False)), text)
    text = html.escape(text, quote=False)

    # An image would make the page load something: keep its description only.
    text = re.sub(r'!\[([^\]\n]*)\]\(([^)\s]+)(?:\s+"[^"\n]*")?\)', r"\1", text)

    def link(match):
        url = html.unescape(match.group(2))
        if not safe_url(url):
            return match.group(0)
        # Only the tags are parked, so emphasis inside the label still works.
        return (stash.put('<a href="%s">' % html.escape(url, quote=True))
                + match.group(1) + stash.put("</a>"))

    text = re.sub(r'\[([^\]\n]+)\]\(([^)\s]+)(?:\s+"[^"\n]*")?\)', link, text)
    text = re.sub(r"\*\*\*(?=\S)(.+?)(?<=\S)\*\*\*", r"<strong><em>\1</em></strong>", text)
    text = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![*\w])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![*\w])", r"<em>\1</em>", text)
    text = re.sub(r"~~(?=\S)(.+?)(?<=\S)~~", r"<del>\1</del>", text)
    text = re.sub(r"==(?=\S)(.+?)(?<=\S)==", r"<mark>\1</mark>", text)
    # A run of block characters is a bar chart in plain text; draw it as one.
    text = re.sub("\u2588+", lambda m: '<span class="bar" style="width:%.2fem">'
                  '</span>' % (0.42 * len(m.group(0))), text)
    return stash.restore(text)


def inline_lines(lines, wrap):
    """A paragraph's source lines -> HTML, honouring line breaks."""
    pieces = []
    for number, line in enumerate(lines):
        hard = line.endswith("  ") or line.endswith("\\")
        body = line.rstrip()
        if body.endswith("\\"):
            body = body[:-1].rstrip()
        pieces.append(inline(body.strip()))
        if number < len(lines) - 1:
            pieces.append("<br>\n" if (hard or not wrap) else "\n")
    return "".join(pieces)


# ---- blocks ------------------------------------------------------------

def comment_word(line):
    match = COMMENT.match(line)
    return match.group(1).strip().lower() if match else None


def split_row(line):
    """Cells of one table row; \\| is a literal bar, not a separator."""
    row = line.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|") and not row.endswith("\\|"):
        row = row[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", row)]


def is_table_start(lines, index):
    return ("|" in lines[index] and index + 1 < len(lines)
            and "-" in lines[index + 1] and TABLE_RULE.match(lines[index + 1])
            and len(split_row(lines[index + 1])) == len(split_row(lines[index])))


def starts_block(lines, index):
    """Would this line begin something other than paragraph text?"""
    line = lines[index]
    return bool(HEADING.match(line) or FENCE.match(line) or RULE.match(line)
                or WRITE_LINE.match(line) or line.lstrip().startswith(">")
                or LIST_ITEM.match(line) or COMMENT.match(line)
                or is_table_start(lines, index))


def render_table(lines, index, out):
    header = split_row(lines[index])
    align = []
    for spec in split_row(lines[index + 1]):
        left, right = spec.startswith(":"), spec.endswith(":")
        align.append("c" if left and right else "r" if right else "")
    index += 2

    def cells(tag, values):
        row = []
        for position in range(len(header)):
            value = values[position] if position < len(values) else ""
            css = ' class="%s"' % align[position] if align[position] else ""
            row.append("<%s%s>%s</%s>" % (tag, css, inline(value), tag))
        return "<tr>%s</tr>" % "".join(row)

    out.append("<table>")
    out.append("<thead>%s</thead>" % cells("th", header))
    out.append("<tbody>")
    while index < len(lines) and lines[index].strip() and "|" in lines[index]:
        out.append(cells("td", split_row(lines[index])))
        index += 1
    out.append("</tbody></table>")
    return index


def collect_list(lines, index):
    """Gather one list's items: [indent, ordered, number, [paragraphs]]."""
    items = []
    while index < len(lines):
        line = lines[index]
        match = LIST_ITEM.match(line)
        if match and not RULE.match(line):
            marker = match.group(2)
            ordered = marker[0].isdigit()
            items.append([len(match.group(1).expandtabs(4)), ordered,
                          int(marker[:-1]) if ordered else None,
                          [[match.group(3)]]])
            index += 1
        elif not line.strip():
            ahead = index + 1
            while ahead < len(lines) and not lines[ahead].strip():
                ahead += 1
            if ahead >= len(lines):
                break
            following = lines[ahead]
            if LIST_ITEM.match(following) and not RULE.match(following):
                index = ahead
            elif following.startswith(("  ", "\t")):
                items[-1][3].append([])      # a further paragraph in the item
                index = ahead
            else:
                break
        elif line.startswith(("  ", "\t")) or not starts_block(lines, index):
            items[-1][3][-1].append(line.strip())
            index += 1
        else:
            break
    return items, index


def render_list(items, position, wrap, out):
    """Emit the list that starts at items[position]; returns the next position."""
    indent, ordered = items[position][0], items[position][1]
    if ordered:
        start = items[position][2]
        out.append("<ol%s>" % (' start="%d"' % start if start != 1 else ""))
    else:
        first = items[position][3][0]
        ticks = bool(first and CHECKBOX.match(first[0]))
        out.append('<ul class="checks">' if ticks else "<ul>")
    open_item = False
    while position < len(items):
        item = items[position]
        if item[0] >= indent + 2:
            position = render_list(items, position, wrap, out)   # a nested list
            continue
        if item[0] < indent or item[1] != ordered:
            break
        if open_item:
            out.append("</li>")
        paragraphs = [p for p in item[3] if p]
        box = CHECKBOX.match(paragraphs[0][0]) if paragraphs else None
        if box:
            paragraphs[0][0] = box.group(2)
            ticked = box.group(1) != " "
            out.append('<li class="check"><span class="box%s"></span>'
                       % (" on" if ticked else ""))
        else:
            out.append("<li>")
        if len(paragraphs) == 1:
            out.append(inline_lines(paragraphs[0], wrap))
        else:
            out.extend("<p>%s</p>" % inline_lines(p, wrap) for p in paragraphs)
        open_item = True
        position += 1
    if open_item:
        out.append("</li>")
    out.append("</ol>" if ordered else "</ul>")
    return position


def render_blocks(lines, wrap=False, include_key=True):
    """Markdown lines -> a list of HTML fragments."""
    out, index, in_key = [], 0, False
    while index < len(lines):
        line = lines[index]

        word = comment_word(line)
        if word is not None:
            if word in PAGE_BREAK_WORDS:
                out.append('<div class="page-break"></div>')
            elif word in KEY_OPEN_WORDS:
                if include_key:
                    out.append('<div class="page-break"></div>')
                    in_key = True
                else:
                    # Skip to the end of the key: its close marker, or the end.
                    index += 1
                    while index < len(lines) and comment_word(lines[index]) not in KEY_CLOSE_WORDS:
                        index += 1
            elif word in KEY_CLOSE_WORDS and in_key:
                out.append('<div class="page-break"></div>')
                in_key = False
            index += 1        # any other comment is dropped, not printed
            continue

        if not line.strip():
            index += 1
            continue

        fence = FENCE.match(line)
        if fence:
            closing = fence.group(1)[0] * 3
            body, index = [], index + 1
            while index < len(lines) and not lines[index].strip().startswith(closing):
                body.append(lines[index])
                index += 1
            index += 1
            out.append("<pre>%s</pre>" % html.escape("\n".join(body), quote=False))
            continue

        heading = HEADING.match(line)
        if heading:
            level = min(len(heading.group(1)), 4)
            out.append("<h%d>%s</h%d>" % (level, inline(heading.group(2)), level))
            index += 1
            continue

        if WRITE_LINE.match(line):
            out.append('<div class="write-line"></div>')
            index += 1
            continue

        if RULE.match(line):
            out.append("<hr>")
            index += 1
            continue

        if is_table_start(lines, index):
            index = render_table(lines, index, out)
            continue

        if line.lstrip().startswith(">"):
            quoted = []
            while index < len(lines) and lines[index].lstrip().startswith(">"):
                quoted.append(re.sub(r"^\s*>\s?", "", lines[index]))
                index += 1
            out.append("<blockquote>")
            out.extend(render_blocks(quoted, wrap, include_key))
            out.append("</blockquote>")
            continue

        if LIST_ITEM.match(line):
            items, index = collect_list(lines, index)
            position = 0
            while position < len(items):
                position = render_list(items, position, wrap, out)
            continue

        paragraph = [line]
        index += 1
        while index < len(lines) and lines[index].strip() \
                and not starts_block(lines, index):
            paragraph.append(lines[index])
            index += 1
        out.append("<p>%s</p>" % inline_lines(paragraph, wrap))
    return out


# ---- document ----------------------------------------------------------

def split_front_matter(text):
    """(metadata, body lines). A leading '---' block of `key: value` lines is
    metadata, not content; anything else that starts with a rule is content."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, lines
    for end in range(1, min(len(lines), 60)):
        if lines[end].strip() != "---":
            continue
        meta = {}
        for raw in lines[1:end]:
            if not raw.strip() or raw.startswith((" ", "\t", "- ", "#")):
                continue
            key, sep, value = raw.partition(":")
            if not sep or not re.fullmatch(r"[A-Za-z_][\w -]*", key.strip()):
                return {}, lines
            meta[key.strip().lower()] = value.strip().strip("\"'")
        return meta, lines[end + 1:]
    return {}, lines


def find_title(lines):
    for line in lines:
        heading = HEADING.match(line)
        if heading and len(heading.group(1)) == 1:
            return re.sub(r"[*`~=]", "", heading.group(2)).strip()
    return None


CSS = """
:root { --ink: #1b1d21; --muted: #5d6470; --rule: #cfd4db; --tint: #f3f5f8;
        --accent: #1d4f7c; }
@page { size: %(paper)s%(orientation)s; margin: 15mm 15mm 17mm;
        @bottom-right { content: counter(page) " / " counter(pages);
                        font: 8pt system-ui, sans-serif; color: #7a808a; } }
* { box-sizing: border-box; }
html { font-size: %(font)s; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0 auto; padding: 12mm 6mm; max-width: %(width)s; color: var(--ink);
       font-family: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial,
                    "Noto Sans", "Liberation Sans", sans-serif;
       line-height: 1.45; }
h1, h2, h3, h4 { line-height: 1.2; break-after: avoid; page-break-after: avoid; }
h1 { font-size: 1.65rem; margin: 0 0 .5em; padding-bottom: .25em;
     border-bottom: 2px solid var(--accent); }
h2 { font-size: 1.22rem; margin: 1.5em 0 .5em; color: var(--accent); }
h3 { font-size: 1.04rem; margin: 1.25em 0 .4em; }
h4 { font-size: .86rem; margin: 1.1em 0 .3em; color: var(--muted);
     text-transform: uppercase; letter-spacing: .05em; }
p { margin: .5em 0; orphans: 3; widows: 3; }
a { color: var(--accent); }
table { border-collapse: collapse; width: 100%%; margin: .6em 0 1.1em; font-size: .9rem; }
thead { display: table-header-group; }
tr { break-inside: avoid; page-break-inside: avoid; }
th, td { border: 1px solid var(--rule); padding: .3em .55em; vertical-align: top;
         text-align: left; }
th { background: var(--tint); font-weight: 600; }
tbody tr:nth-child(even) td { background: #fafbfc; }
th.r, td.r { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
th.c, td.c { text-align: center; }
.bar { display: inline-block; height: .72em; background: var(--accent); opacity: .8;
       border-radius: 1px; vertical-align: -.02em; }
blockquote { margin: .8em 0; padding: .5em .9em; background: var(--tint);
             border-left: 4px solid var(--accent); break-inside: avoid; }
blockquote > :first-child { margin-top: .15em; }
blockquote > :last-child { margin-bottom: .15em; }
code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas,
                         "Liberation Mono", monospace; }
code { font-size: .92em; background: var(--tint); padding: .05em .3em; border-radius: 3px; }
pre { margin: .7em 0; padding: .7em .9em; background: var(--tint); border-radius: 4px;
      font-size: .95rem; line-height: 1.75; white-space: pre-wrap;
      overflow-wrap: anywhere; break-inside: avoid; }
ul, ol { margin: .4em 0 .7em; padding-left: 1.5em; }
li { margin: .18em 0; }
li > p { margin: .25em 0; }
ul.checks { padding-left: .2em; }
ul.checks ul.checks { padding-left: 1.6em; }
li.check { list-style: none; }
.box { display: inline-block; width: .85em; height: .85em; margin-right: .5em;
       border: 1.2px solid var(--ink); border-radius: 2px; vertical-align: -.08em;
       text-align: center; line-height: .8em; font-size: .9em; }
.box.on::after { content: "\\2713"; }
del { color: #a3352b; }
mark { background: #fff1a8; padding: 0 .15em; }
hr { border: 0; border-top: 1px solid var(--rule); margin: 1.3em 0; }
.write-line { height: 2.2em; border-bottom: 1px solid #8a9099; }
.page-break { break-before: page; page-break-before: always; height: 0; }
.hint { margin: 0 0 1.2em; padding: .45em .75em; font-size: .82rem; color: var(--muted);
        background: #fffbe8; border: 1px solid #efe2a4; border-radius: 4px; }
@media print { body { max-width: none; padding: 0; } .hint { display: none; } }
"""

HINT = ("To get paper or a PDF: print this page (Ctrl+P, or Cmd+P on a Mac) "
        "and choose “Save as PDF”. This note is not printed.")


def render_document(text, title=None, lang="en", paper="a4", landscape=False,
                    compact=False, include_key=True, wrap=False, hint=True):
    """A whole Markdown document -> one self-contained HTML page."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    meta, lines = split_front_matter(text)
    title = title or meta.get("title") or find_title(lines) or "Untitled"
    body = render_blocks(lines, wrap, include_key)
    # A break with nothing before or after it would print an empty page.
    page_break = '<div class="page-break"></div>'
    while body and body[0] == page_break:
        body.pop(0)
    while body and body[-1] == page_break:
        body.pop()
    css = CSS % {
        "paper": PAPER[paper],
        "orientation": " landscape" if landscape else "",
        "font": "9.5pt" if compact else "11pt",
        "width": BODY_WIDTH[(paper, landscape)],
    }
    lang = re.sub(r"[^A-Za-z0-9-]", "", lang or "") or "en"
    parts = [
        "<!DOCTYPE html>",
        '<html lang="%s">' % lang,
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="generator" content="%s">' % fileguard.GENERATOR,
        "<title>%s</title>" % html.escape(title, quote=False),
        "<style>%s</style>" % css,
        "</head>",
        "<body>",
    ]
    if hint:
        parts.append('<p class="hint">%s</p>' % html.escape(HINT, quote=False))
    parts += body
    parts += ["</body>", "</html>", ""]
    return "\n".join(parts)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", help="the Markdown file to render, or - for stdin")
    parser.add_argument("-o", "--output", default=None,
                        help="the HTML file to write (default: next to the "
                             "source, same name with .html)")
    parser.add_argument("--title", default=None,
                        help="page title (default: the first # heading)")
    parser.add_argument("--lang", default="en",
                        help="language of the text, e.g. en, uk, es (default en)")
    parser.add_argument("--paper", choices=sorted(PAPER), default="a4")
    parser.add_argument("--landscape", action="store_true",
                        help="turn the page sideways, for wide tables")
    parser.add_argument("--compact", action="store_true",
                        help="smaller type, to fit more on a page")
    parser.add_argument("--no-key", action="store_true", dest="no_key",
                        help="leave out everything after <!-- key --> "
                             "(the learner's copy)")
    parser.add_argument("--wrap", action="store_true",
                        help="reflow hard-wrapped text: a single new line "
                             "becomes a space instead of a line break")
    parser.add_argument("--no-hint", action="store_true", dest="no_hint",
                        help="leave out the on-screen note about printing")
    # Accepted so one prefix works for every command; a render needs neither.
    parser.add_argument("--base", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--learner", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    try:
        text = fileguard.read_text(args.source, (".md", ".markdown", ".txt"))
    except fileguard.Refused as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    except (OSError, UnicodeDecodeError) as exc:
        print("error: could not read %s: %s" % (args.source, exc), file=sys.stderr)
        return 2
    source = None if args.source == "-" else Path(args.source).expanduser()

    page = render_document(text, args.title, args.lang, args.paper,
                           args.landscape, args.compact, not args.no_key,
                           args.wrap, not args.no_hint)

    if args.output:
        target = Path(args.output).expanduser()
    elif source is None:
        sys.stdout.write(page)
        return 0
    else:
        target = source.with_suffix(".html")
    try:
        target = fileguard.check_html_target(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
    except fileguard.Refused as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    except OSError as exc:
        print("error: could not write %s: %s" % (target, exc), file=sys.stderr)
        return 1
    print("written: %s" % target)
    print("Open it in a browser and print it, or choose “Save as PDF” in the "
          "print dialog.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
