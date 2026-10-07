# Printable practice sheets and handouts

Read this when someone wants something on paper or as a PDF: a worksheet
aimed at a learner's known mistakes, a sheet of exam-format practice with a
key, or a printed copy of a report. `coach <command>` is defined in
`SKILL.md`; in tutor mode every command carries `--learner <name>`.

The route is always the same: write Markdown → `coach render` makes one
self-contained page laid out for print → the user opens it in a browser and
prints it, or chooses "Save as PDF" in the print dialog. No PDF is produced
here, so never say one was.

## 1. Choose what the sheet is for

One sheet, one target — at most two or three points that belong together.
A sheet that covers everything teaches nothing.

- From the error catalog (`coach catalog`): **chronic and returned points
  first**, then recurring ones.
- From the queue: `coach queue due`.
- Or whatever the tutor or learner names.

Plan for 15–20 minutes of work: one or two pages, plus the key.

## 2. Collect the learner's own evidence

`coach catalog --json --full` lists every logged mistake under its point,
with the learner's words and the correction. Correcting one's *own*
sentences is the strongest exercise there is — take five to eight of them
for the sheet. Use the count from the catalog ("in 6 of 6 tests") to say
why the sheet exists; do not estimate it.

## 3. Write the sheet

Everything on the sheet is original. Items are new sentences in contexts
the exam uses — emails, campus life, short academic prose — at the
learner's level; never items from an exam or a coursebook.

A shape that works:

```markdown
# Articles before singular count nouns

**Name:** ______________________  **Date:** ____________  **Time:** 20 minutes

> **Why this sheet.** *a/an* was missing before a singular count noun in 6 of 6 tests — 8 times in all. One rule; say each answer aloud first.

## The rule

A singular count noun never stands alone: it takes *a/an*, *the*, or a word like *my* or *this*.

| Written | Should be |
|:---|:---|
| ~~I am student~~ | I am **a** student |
| ~~in such company~~ | in such **a** company |

## A. Choose

1. She works as ___ engineer.  (a / an / —)
2. It was ___ good idea.  (a / an / —)

## B. Correct your own sentences

1. it turns into life-changer
____
2. the ability of company
____

## C. Write

Three sentences about your first week at university. Use a singular count noun in each.
____
____
____

- [ ] I read every sentence aloud before checking the key.

<!-- key -->
## Key

**A.** 1 an · 2 a
**B.** 1 it turns into **a** life-changer · 2 the ability of **the** company
```

Build it from four kinds of exercise, easiest first:

1. **Recognise** — choose or tick the correct form.
2. **Produce under control** — fill a gap, transform, put in order.
3. **Correct your own** — the learner's logged sentences, uncorrected.
4. **Produce freely** — a few sentences of their own, with writing lines.

For a mistake carried over from the first language, replace the rule box
with **contrast pairs**: how the first language says it, how English says
it. These errors are translated, not mis-learned; another explanation of
the rule does not reach them.

Instructions may be written in the learner's own language if that is what
the tutor wants; the English being practised stays English.

**Exam-format tasks on a sheet.** For TOEFL Complete the Words and Build a
Sentence, build the items with `coach ctest make` and `coach sentence
make`, and paste what they print into a fenced block (three backticks), so
that every blank reaches the paper exactly as generated. Put what they
print under "KEEP BACK" in the key.

## 4. What the renderer understands

| Write | Get |
|---|---|
| `#` to `####` | headings |
| `**bold**` `*italic*` `` `code` `` `~~struck out~~` `==highlighted==` | emphasis; struck-out text prints in red |
| `- item`, `1. item`, indented to nest | lists; numbering is kept as typed |
| `- [ ] task` | a tick box |
| a table with `:---`, `---:`, `:---:` | a table, aligned as marked |
| `> note` | a boxed note |
| a fenced block | text kept exactly as typed, in a fixed-width face |
| a line of underscores only: `____` | a full-width writing line |
| `---` | a rule |
| `<!-- pagebreak -->` | a new page |
| `<!-- key -->` | the answer key starts here, on a new page |

Underscores are never emphasis, so a blank written `______` or `fr_ _ _`
survives. **A new line in the source is a new line on the page**, so write
each paragraph on one line, as in the example above (or pass `--wrap` for
text that was wrapped by hand). Raw HTML is shown as text, images are not
loaded, and only ordinary web and mail links become links — the page loads
nothing.

## 5. Save and render

Save the Markdown where the learner's other files are — `<base>/sheets/`
(`coach state show` prints `<base>`), named by date and topic — unless the
user wants it elsewhere.

```bash
coach render sheet.md                                 # sheet.html, key on its own page
coach render sheet.md --no-key -o sheet-learner.html  # the learner's copy
```

| Option | For |
|---|---|
| `--no-key` | leave out everything after `<!-- key -->` |
| `--lang uk` | the language of the instructions (hyphenation, screen readers) |
| `--landscape` | wide tables, such as the catalog's point-by-test matrix |
| `--compact` | smaller type, to fit a page |
| `--paper letter` | US Letter instead of A4 |
| `--title "…"` | the page title (default: the first heading) |

Give the user the HTML file, and say how to get paper or a PDF from it:
open it in a browser and print, or choose "Save as PDF" in the print
dialog. Reports are rendered the same way — `coach render
<base>/reports/error-catalog.md --landscape`.

## 6. When the sheet comes back

Mark it against the key and go through what was missed. Then record the
result where it counts — on the points the sheet was for:

```bash
coach queue review --id <id> --result pass     # or: --result fail
```

A pass means the new items for that point were right and the learner's own
sentences were corrected without help. Log anything new that went wrong
with `coach log-error`, then `coach queue sync`. A sheet is not a task type
of the exam, so it is not logged as an attempt.

A point is not closed by a good sheet. It is closed by staying out of four
tests in a row (`references/test-review.md`).

## Boundaries

- Original items only; a learner's own sentences may be quoted back to
  them, nothing from an exam or a published book may.
- A learner's name and mistakes are private: a sheet goes to the tutor and
  the learner, nowhere else.
- No PDF is made here. Say what was written — an HTML page — and how to
  print it.
