"""Tests for render.py: Markdown reports and sheets -> one printable page.

Two promises matter more than the layout. The page loads nothing and runs
nothing, whatever the source contains; and a blank written with underscores
reaches the paper as typed, because on a gapped-text sheet the number of
underscores IS the question.
"""

import re
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import SCRIPTS, coach

sys.path.insert(0, str(SCRIPTS))
import render  # noqa: E402


def body(markdown, **options):
    """The rendered fragments for a piece of Markdown, as one string."""
    return "\n".join(render.render_blocks(markdown.split("\n"), **options))


class InlineTests(unittest.TestCase):
    def test_emphasis_code_strike_and_highlight(self):
        self.assertEqual(render.inline("**a** *b* `c` ~~d~~ ==e=="),
                         "<strong>a</strong> <em>b</em> <code>c</code> "
                         "<del>d</del> <mark>e</mark>")
        self.assertEqual(render.inline("***both***"),
                         "<strong><em>both</em></strong>")

    def test_underscores_are_never_emphasis(self):
        for text in ("mi_ _ _", "write ______ here", "_not italic_",
                     "__not bold__", "th_ _ t_ _ w_ _"):
            self.assertEqual(render.inline(text), text)

    def test_a_lone_asterisk_is_not_emphasis(self):
        self.assertEqual(render.inline("2 * 3 * 4"), "2 * 3 * 4")
        self.assertEqual(render.inline("\\* a footnote"), "* a footnote")

    def test_everything_else_is_escaped(self):
        self.assertEqual(render.inline('<script>alert("x")</script> & <b>'),
                         '&lt;script&gt;alert("x")&lt;/script&gt; &amp; &lt;b&gt;')
        self.assertEqual(render.inline("`<img src=x onerror=y>`"),
                         "<code>&lt;img src=x onerror=y&gt;</code>")

    def test_only_web_and_mail_links_become_links(self):
        self.assertEqual(render.inline("[site](https://example.org/a?b=1&c=2)"),
                         '<a href="https://example.org/a?b=1&amp;c=2">site</a>')
        self.assertEqual(render.inline("[mail](mailto:a@example.org)"),
                         '<a href="mailto:a@example.org">mail</a>')
        self.assertEqual(render.inline("[local](notes/plan.md)"),
                         '<a href="notes/plan.md">local</a>')
        for url in ("javascript:alert(1)", "JaVaScRiPt:alert(1)",
                    "data:text/html,x", "file:///etc/passwd", "vbscript:x",
                    "//evil.example/x"):
            rendered = render.inline("[x](%s)" % url)
            self.assertNotIn("<a ", rendered, url)

    def test_addresses_a_browser_would_reinterpret_are_refused(self):
        # A browser strips leading control characters and reads \ as /.
        for url in ("\x01javascript:alert(1)", "\x1fjavascript:alert(1)",
                    "\\\\host\\share", "/\\evil.example", "java\x00script:x",
                    "x:y", "\x7fjavascript:x"):
            rendered = render.inline("[x](%s)" % url)
            self.assertNotIn("<a ", rendered, repr(url))
        # A character reference is not decoded twice: it stays an inert
        # relative address, escaped inside the attribute.
        entity = render.inline("[x](&#106;avascript:alert)")
        self.assertIn('href="&amp;#106;avascript:alert"', entity)
        self.assertFalse(render.safe_url(""))
        for url in ("https://example.org/a:b", "notes/plan.md", "#key",
                    "sheet.html?x=1", "a/b:c"):
            self.assertTrue(render.safe_url(url), url)

    def test_a_link_cannot_break_out_of_its_attribute(self):
        rendered = render.inline('[x](https://e.org/"onmouseover="alert(1))')
        self.assertNotIn('"onmouseover="', rendered)
        self.assertEqual(rendered.count("<a "), rendered.count("</a>"))

    def test_emphasis_inside_a_link_label(self):
        self.assertEqual(render.inline("[**bold** link](https://e.org)"),
                         '<a href="https://e.org"><strong>bold</strong> link</a>')

    def test_images_keep_only_their_description(self):
        rendered = render.inline("![a chart](https://example.org/c.png) after")
        self.assertEqual(rendered, "a chart after")

    def test_escaped_bar_and_code_with_bar(self):
        self.assertEqual(render.inline("a \\| b"), "a | b")
        self.assertEqual(render.inline("`a\\|b`"), "<code>a|b</code>")

    def test_a_run_of_block_characters_is_drawn_as_a_bar(self):
        rendered = render.inline("█" * 4)
        self.assertEqual(rendered, '<span class="bar" style="width:1.68em"></span>')

    def test_a_null_byte_cannot_forge_a_stashed_fragment(self):
        rendered = render.inline("\x000\x00 `code` \x001\x00")
        self.assertEqual(rendered.count("<code>"), 1)


class BlockTests(unittest.TestCase):
    def test_headings_are_capped_at_four_levels(self):
        out = body("# A\n## B\n### C\n#### D\n###### F")
        self.assertEqual(re.findall(r"<h(\d)>", out), ["1", "2", "3", "4", "4"])
        self.assertIn("<h1>A</h1>", out)

    def test_a_new_line_is_a_new_line_unless_wrapping_is_asked_for(self):
        self.assertEqual(body("**Woman:** Hi.\n**Man:** Hello."),
                         "<p><strong>Woman:</strong> Hi.<br>\n<strong>Man:</strong> Hello.</p>")
        self.assertEqual(body("one\ntwo", wrap=True), "<p>one\ntwo</p>")
        self.assertEqual(body("one  \ntwo", wrap=True), "<p>one<br>\ntwo</p>")

    def test_table_with_alignment_padding_and_escaped_bars(self):
        out = body("| # | Point | n |\n| ---: | :--- | :---: |\n"
                   "| 1 | a \\| an | 3 |\n| 2 | short |\n")
        self.assertIn('<th class="r">#</th><th>Point</th><th class="c">n</th>', out)
        self.assertIn('<td class="r">1</td><td>a | an</td><td class="c">3</td>', out)
        self.assertIn('<td class="r">2</td><td>short</td><td class="c"></td>', out)
        self.assertEqual(out.count("<tr>"), 3)

    def test_a_bar_in_prose_is_not_a_table(self):
        out = body("either this | or that\n---\nnext")
        self.assertNotIn("<table>", out)
        self.assertIn("<hr>", out)

    def test_lists_nest_by_indentation_and_keep_their_numbering(self):
        out = body("3. three\n4. four\n   - inner\n   - inner two\n5. five")
        self.assertIn('<ol start="3">', out)
        self.assertEqual(out.count("<ul>"), 1)
        self.assertLess(out.index("<ul>"), out.index("five"))
        self.assertEqual(out.count("<li>"), 5)
        self.assertEqual(out.count("</li>"), 5)

    def test_a_change_of_list_type_starts_a_new_list(self):
        out = body("- a\n- b\n1. one\n2. two")
        self.assertEqual((out.count("<ul>"), out.count("<ol>")), (1, 1))

    def test_tick_boxes(self):
        out = body("- [ ] to do\n- [x] done")
        self.assertIn('<ul class="checks">', out)
        self.assertIn('<li class="check"><span class="box"></span>', out)
        self.assertIn('<li class="check"><span class="box on"></span>', out)
        self.assertNotIn("[ ]", out)

    def test_an_item_can_hold_a_second_paragraph(self):
        out = body("1. Rewrite the sentence.\n\n   She is doctor.\n2. Next")
        self.assertIn("<p>Rewrite the sentence.</p>", out)
        self.assertIn("<p>She is doctor.</p>", out)
        self.assertEqual(out.count("<ol"), 1)

    def test_a_block_ends_a_list(self):
        out = body("- item\n## Heading\n- [ ] box\n____\ntext")
        self.assertLess(out.index("</ul>"), out.index("<h2>"))
        self.assertIn('<div class="write-line"></div>', out)
        self.assertIn("<p>text</p>", out)

    def test_underscores_alone_are_a_writing_line_not_a_rule(self):
        out = body("____\n\n---\n\n***")
        self.assertEqual(out.count('<div class="write-line"></div>'), 1)
        self.assertEqual(out.count("<hr>"), 2)

    def test_a_fenced_block_is_kept_exactly_as_typed(self):
        out = body("```\nTh_ _ cool  t_ _ air\n  <b>&\n```\nafter")
        self.assertIn("<pre>Th_ _ cool  t_ _ air\n  &lt;b&gt;&amp;</pre>", out)
        self.assertIn("<p>after</p>", out)

    def test_an_unclosed_fence_does_not_lose_the_text(self):
        out = body("```\nkept")
        self.assertIn("<pre>kept</pre>", out)

    def test_a_quote_is_a_note_and_can_hold_blocks(self):
        out = body("> **Why.** One rule.\n> - a\n> - b\n\nafter")
        self.assertIn("<blockquote>", out)
        self.assertLess(out.index("<ul>"), out.index("</blockquote>"))
        self.assertGreater(out.index("<p>after</p>"), out.index("</blockquote>"))

    def test_page_break_and_other_comments(self):
        out = body("a\n<!-- pagebreak -->\nb\n<!-- a private note -->\nc")
        self.assertEqual(out.count('<div class="page-break"></div>'), 1)
        self.assertNotIn("private note", out)

    def test_raw_html_blocks_are_shown_not_run(self):
        out = body("<script>alert(1)</script>\n\n<div onclick=\"x()\">hi</div>")
        self.assertNotIn("<script", out)
        self.assertNotIn("<div onclick", out)
        self.assertIn("&lt;script&gt;", out)


SHEET = """# Sheet

1. She is ___ engineer.

<!-- key -->
## Answer key

1. an
"""


class AnswerKeyTests(unittest.TestCase):
    def test_the_key_starts_a_new_page(self):
        out = body(SHEET)
        self.assertLess(out.index("page-break"), out.index("Answer key"))

    def test_the_learners_copy_has_no_key(self):
        out = body(SHEET, include_key=False)
        self.assertNotIn("Answer key", out)
        self.assertNotIn("<li>\nan", out)
        self.assertIn("She is ___ engineer.", out)

    def test_a_closed_key_lets_the_sheet_continue(self):
        text = "one\n<!-- key -->\nsecret\n<!-- /key -->\ntwo"
        without = body(text, include_key=False)
        self.assertNotIn("secret", without)
        self.assertIn("<p>one</p>", without)
        self.assertIn("<p>two</p>", without)
        self.assertEqual(body(text).count("page-break"), 2)

    def test_no_empty_page_at_either_end(self):
        page = render.render_document("<!-- pagebreak -->\n# T\n\nx\n<!-- key -->\n"
                                      "k\n<!-- /key -->\n")
        inside = page[page.index("<body>"):]
        self.assertEqual(inside.count('<div class="page-break"></div>'), 1)


class DocumentTests(unittest.TestCase):
    def test_the_page_is_self_contained(self):
        page = render.render_document(SHEET + "\n![x](https://e.org/x.png)\n"
                                      "<link rel=stylesheet href=//e.org/x.css>\n")
        self.assertTrue(page.startswith("<!DOCTYPE html>"))
        for needle in ("<script", "<link", "<img", "<iframe", "@import", "url(",
                       "src=", "http-equiv"):
            self.assertNotIn(needle, page, needle)
        self.assertIn('<meta charset="utf-8">', page)

    def test_title_comes_from_the_flag_then_metadata_then_the_heading(self):
        self.assertIn("<title>Sheet</title>", render.render_document(SHEET))
        self.assertIn("<title>Mine</title>",
                      render.render_document("---\ntitle: Mine\n---\n" + SHEET))
        self.assertIn("<title>A &amp; B</title>",
                      render.render_document(SHEET, title="A & B"))
        self.assertIn("<title>Untitled</title>", render.render_document("plain"))

    def test_front_matter_is_not_printed(self):
        page = render.render_document("---\ntitle: T\nsession: 2026-07-01-am\n---\n# H\n")
        self.assertNotIn("session:", page)
        self.assertNotIn("<hr>", page)

    def test_a_rule_at_the_top_is_not_mistaken_for_front_matter(self):
        page = render.render_document("---\nA real first line.\n---\nmore")
        self.assertIn("A real first line.", page)

    def test_page_options(self):
        page = render.render_document("x", paper="letter", landscape=True,
                                      compact=True, lang="uk", hint=False)
        self.assertIn("size: letter landscape", page)
        self.assertIn("font-size: 9.5pt", page)
        self.assertIn('<html lang="uk">', page)
        self.assertNotIn('class="hint"', page)
        default = render.render_document("x")
        self.assertIn("size: A4;", default)
        self.assertIn('class="hint"', default)

    def test_a_hostile_language_code_cannot_inject_markup(self):
        page = render.render_document("x", lang='en"><script>alert(1)</script>')
        self.assertNotIn("<script", page)

    def test_non_latin_text_survives(self):
        page = render.render_document("# Аркуш 3\n\nВстав артикль: ___ engineer — так.")
        self.assertIn("<h1>Аркуш 3</h1>", page)
        self.assertIn("Встав артикль: ___ engineer — так.", page)

    def test_windows_line_endings(self):
        page = render.render_document("# T\r\n\r\n- a\r\n- b\r\n")
        self.assertEqual(page.count("<li>"), 2)
        self.assertNotIn("\r", page)


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.source = self.dir / "sheet.md"
        self.source.write_text(SHEET, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_writes_next_to_the_source_by_default(self):
        result = coach(self.dir, "render", self.source)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (self.dir / "sheet.html").read_text(encoding="utf-8")
        self.assertIn("Answer key", page)
        self.assertIn("written:", result.stdout)

    def test_learner_copy_to_a_chosen_file(self):
        target = self.dir / "out" / "student.html"
        result = coach(self.dir, "render", self.source, "--no-key", "-o", target,
                       "--lang", "uk", "--landscape")
        self.assertEqual(result.returncode, 0, result.stderr)
        page = target.read_text(encoding="utf-8")
        self.assertNotIn("Answer key", page)
        self.assertIn('<html lang="uk">', page)

    def test_a_missing_source_is_an_error_not_a_crash(self):
        result = coach(self.dir, "render", self.dir / "nope.md")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_it_refuses_to_overwrite_its_own_source(self):
        page = self.dir / "page.html"
        page.write_text("# already html-named\n", encoding="utf-8")
        result = coach(self.dir, "render", page)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(page.read_text(encoding="utf-8"), "# already html-named\n")

    def test_a_real_report_renders(self):
        base = self.dir / "progress"
        coach(base, "log-test", "--name", "Alpha", "--date", "2026-07-01", "--exam",
              "toefl-ibt", "--reading", "4", "--listening", "5", "--writing", "4",
              "--speaking", "3")
        coach(base, "log-error", "--category", "grammar", "--subtype", "article",
              "--point", "a before a job", "--evidence", "she is doctor",
              "--fix", "she is a doctor", "--session", "test-alpha-20260701")
        self.assertEqual(coach(base, "catalog").returncode, 0)
        result = coach(base, "render", base / "reports" / "error-catalog.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (base / "reports" / "error-catalog.html").read_text(encoding="utf-8")
        self.assertIn("<h1>Error catalog</h1>", page)
        self.assertIn('<span class="bar"', page)
        self.assertIn("<em>she is doctor</em> → she is a doctor", page)
        self.assertEqual(page.count("<table>"), page.count("</table>"))


if __name__ == "__main__":
    unittest.main()
