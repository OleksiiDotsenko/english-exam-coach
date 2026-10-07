# TOEFL iBT — format facts (redesigned test, from 21 January 2026)

<!-- last-verified: 2026-10-07 | verified-against: the exam provider's "TOEFL iBT Test: 2026 Update — Test Blueprint and Specifications Document", its test-content pages, and its full-length practice test for the 2026 format. Re-verify every release cycle; exam formats change without notice. -->

Factual description of the test in use since 21 January 2026. No official
test content appears here, and the task instructions are described in our
own words rather than quoted. Where the exam provider publishes no figure, the
line says so rather than guessing: three earlier versions of this file
trusted prep-site summaries for task shapes and were wrong each time.

**Structure:** four sections in fixed order, **Reading → Listening → Writing
→ Speaking**; 120 items in all. Published test time is 1 h 23 min to
1 h 29 min (allow about two hours for the appointment). No breaks. Notes are
allowed throughout. Reading and Listening are **two-stage adaptive**:
everyone takes a first "router" module, then a lower or an upper second
module depending on how the first went. Writing and Speaking are linear —
everyone gets the same tasks. Reading and Listening contain some unscored
trial items, which are not marked as such.

**Scale (since Jan 2026):** each section is reported in **bands 1–6 in
half-band steps**; overall = the average of the four sections rounded to the
nearest half band. Score reports through about January 2028 also show a
comparable legacy 0–120 score. Scores post about 3 days after the test and
are valid for 2 years.

**Raw points behind the bands:** Reading 35 · Listening 35 · Writing 20
(ten sentences at 1 point, two written tasks at up to 5) · Speaking 55
(eleven responses at up to 5).

**Official CEFR alignment (overall and per section):**

| Band | 6.0 | 5.0–5.5 | 4.0–4.5 | 3.0–3.5 | 2.0–2.5 | 1.0–1.5 |
|---|---|---|---|---|---|---|
| CEFR | C2 | C1 | B2 | B1 | A2 | A1 |

**Legacy 0–120 concordance (overall, official):** 6.0 ≈ 114+, 5.5 ≈ 107+,
5.0 ≈ 95+, 4.5 ≈ 86+, 4.0 ≈ 72+, 3.5 ≈ 58+, 3.0 ≈ 44+.

## Reading — 30 min · 50 items · adaptive

Published timing: router module 18–21 min, second module 9 min. Every scored
item is worth 1 point. Texts stay on screen while you answer. Inside a
module you can move back and forth; once the second module starts you
cannot return to the first.

| Task type | Items | Mechanics |
|---|---|---|
| Complete the Words | 30 (three paragraphs of 10) | One paragraph of about 70–80 words with **exactly 10 gaps**. The first sentence is left whole. From the second sentence on, **the second half of every second word is removed**, beginning with the second word, until ten words are gapped; the rest of the paragraph is whole. A word of *n* letters keeps its first *n ÷ 2* letters, rounded down — "fruit" shows `fr` and loses 3, "of" shows `o` and loses 1 — so a visible stem can be a single letter. **One blank is shown for each missing letter.** Numbers, names and a term the context cannot supply are left whole, and the count passes over them. Spelling must be exact; no partial credit, no penalty for a wrong answer |
| Read in Daily Life | 5–15 | Short everyday texts — a notice, a sign, a menu, an email, a social-media post, a schedule — of about 15–150 words, each with a set of **2 or 3** four-option questions (purpose, detail, inference) |
| Read an Academic Passage | 5–15 | A titled passage of up to about 200 words with **5** four-option questions: main idea, detail, vocabulary in context, inference, why the author mentions something, and NOT/EXCEPT |

In the official practice test one module is 20 questions: 10 gaps, two Daily
Life texts (2 + 3 questions) and one academic passage (5).

Build Complete-the-Words items with `coach ctest make`, never by hand: the
rule above is mechanical, and a miscounted blank makes an item unanswerable.

The old long-passage format (2 × ~700 words, 10 questions each) is gone.

## Listening — 29 min · 47 items · adaptive

Published timing: router module 18 min, then 7 min (lower) or 11 min (upper).
Every scored item is worth 1 point. **Every recording plays once.** Each
question has its own clock, and **you cannot go back to an earlier
question**. Voices cover North American, British and Australian accents; a
picture of the speaker is shown.

| Task type | Items | Mechanics |
|---|---|---|
| Listen and Choose a Response | 15–19 | One short utterance — a question or a remark, at most about six stressed syllables — with no transcript; pick the best reply from 4 printed options |
| Listen to a Conversation | 10 | Two speakers, about 35–100 words, in an everyday, workplace or campus setting; **2 questions** each |
| Listen to an Announcement | 6–10 | One speaker in a classroom or campus setting, about 35–100 words; **2 questions** each |
| Listen to an Academic Talk | 8–16 | One speaker — a short lecture or a podcast-style talk — of up to 250 words; **4 questions** each (topic, detail, why the speaker mentions something, inference, what comes next) |

In the official practice test a module opens with 8 Choose-a-Response items,
then one or two conversations, an announcement and a talk (16–18 questions).

## Writing — 23 min · 12 items · linear

| Task | Items | Time | Mechanics |
|---|---|---|---|
| Build a Sentence | 10 (1 point each) | about 6 min for all ten (see note) | **Every item shows two sentences.** You read one complete sentence — a question, a piece of news, a plan — and build the reply to it from word tiles. The reply appears as a row of blanks, one per tile, **5 to 7 blanks**, sometimes with a word or two already printed in it, and always with its closing full stop or question mark. The tiles are lower-case words and short phrases. A few items carry **one extra tile that is not used**. Most replies are questions, often indirect ("Do you know if…", "Can you tell me whether…"); the rest are statements with a relative or passive clause. All-or-nothing: every tile must be in the right place |
| Write an Email | 1 (up to 5 points) | 7 min | A situation in two or three sentences, then who to write to and **three bullet points** saying what the email must do. The To and Subject lines are already filled in. The instruction is to write as much as you can, in complete sentences; no word count is set |
| Write for an Academic Discussion | 1 (up to 5 points) | 10 min | A professor's post that ends in a question (about 60–80 words) and two students' posts that take different sides (about 40–50 words each). You express and support your own opinion and add to the discussion in your own words. **An effective response contains at least 100 words** |

*Note on Build a Sentence timing:* no separate figure is published. The
section is 23 minutes, the email takes 7 and the discussion 10, which leaves
about 6 for the ten sentences; the task runs on its own clock.

Build these items with `coach sentence make`: it cuts the reply into the
frame and the tiles, so the blanks always match.

The old integrated reading–listening essay is gone; there are no integrated
tasks anywhere in the redesigned test.

## Speaking — 8 min · 11 items · linear

Each response is scored 0–5. Both tasks open with a scenario that is heard
and shown on screen, and **neither gives any preparation time**.

| Task | Items | Mechanics |
|---|---|---|
| Listen and Repeat | 7 | **All seven sentences belong to ONE scenario**, set by a line that gives you a role and a speaker (in our words: "You are starting a job at a campus bookshop. Listen to your supervisor and repeat what she says."). One speaker throughout. Each sentence plays once and you repeat it at once, on a short clock. They grow in length and complexity: from one short clause of about 5–7 words to sentences of about 11–14 words with a list, a relative clause or a dependent clause. The growth is loose, not strict — the official practice set runs 6, 9, 11, 12, 9, 11, 13 words — and the sentences do **not** reach the high teens |
| Take an Interview | 4 | A simulated interview, **opened by a brief scenario** (in our words: "You are taking part in a study about how people use libraries. A researcher will ask you some questions."). One interviewer, one everyday topic. The interviewer thanks you, names the topic and asks the first question; **each later question is led into by one to three sentences**, so the turns you hear run about 35–60 words rather than one line. The four move from a factual question about you → your own reaction, and why → whether you agree with a view the interviewer states → your opinion on a policy or proposal ("Why or why not?"). The answer clock is not published; about 45 seconds per answer is the commonly reported figure |

All four old speaking tasks (independent opinion + three integrated tasks)
are gone.

## Delivery

Test centres and the TOEFL iBT Home Edition worldwide, both using this
format. The Paper Edition was discontinued in January 2024. One legacy
carve-out: **TOEFL iBT Australia** — a separate test-centre administration
that keeps the pre-2026 format and 0–30/0–120 scoring, currently the only
TOEFL accepted for Australian visa purposes. (For that legacy format:
sections were Reading/Listening/Speaking/Writing at 0–30 each, ~2 h total.)
