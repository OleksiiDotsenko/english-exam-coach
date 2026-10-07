# Seed reading & use-of-english items (original examples)

All items are original, written for this plugin as format references. They
are NOT from any official exam. Answer keys are given here because these are
seeds; in a live drill, reveal answers only after the learner has responded.

## Open cloze (B2/C1 format: one word per gap)

> City beekeeping has grown rapidly (1) ____ the last decade. What began as
> a hobby for a handful of enthusiasts has turned (2) ____ a small industry,
> with hives now installed on office rooftops. Not everyone is convinced,
> (3) ____ . Some ecologists argue that honeybees compete with wild
> pollinators, which have (4) ____ harder time finding food in cities.

**Key:** 1 over/in/during · 2 into · 3 however/though · 4 a

## Key word transformations (B2: 2–5 words · C1: 3–6 · C2: 3–8, always including the key word)

> 1. "I regret selling my bicycle," said Marco. — **WISHES**
>    Marco ____ his bicycle.
>    *(key: wishes he had not / hadn't sold)*
> 2. Hardly anyone was interested in the concert, so it was cancelled. — **LACK**
>    The concert was cancelled ____ interest.
>    *(key: because of / due to / owing to a lack of)*
> 3. It was wrong of you to open that letter. — **OUGHT**
>    You ____ that letter.
>    *(key: ought not to have opened)*

## Word formation (B2/C1 format)

> 1. Her argument was so ____ that even the sceptics applauded. **PERSUADE**
>    *(key: persuasive)*
> 2. The committee questioned the ____ of the new policy. **EFFECTIVE**
>    *(key: effectiveness)*
> 3. He was criticised for acting ____ in a moment of pressure. **RESPONSIBLE**
>    *(key: irresponsibly)*

## True / False / Not Given (IELTS reading format)

> **Passage (extract):** The community orchard was planted in 2019 on a strip
> of unused railway land. Volunteers maintain the trees, and the fruit is
> free to anyone who picks it. The council provides water access but no
> funding; a local bakery donates tools.
>
> 1. The orchard occupies land that once belonged to a railway. *(True)*
> 2. The council pays part of the orchard's running costs. *(False)*
> 3. The volunteers sell most of the fruit at a weekly market. *(Not Given —
>    the passage says fruit is free to pickers but says nothing about a market
>    or selling.)*

*T/F/NG tests statements against **facts** in the text. Contrast with the
next task, which tests statements against the **writer's views** — note the
opinion-bearing passage and the Yes/No labels.*

## Yes / No / Not Given (IELTS reading format)

> **Passage (extract):** In my view, cities have been far too timid about
> rooftop gardens. The engineering objections are real but soluble, and the
> benefits — cooler buildings, stronger neighbourhoods — plainly outweigh the
> cost. What holds councils back, I suspect, is simple caution rather than any
> serious doubt about the idea.
>
> 1. The writer believes cities should do more to promote rooftop gardens.
>    *(Yes — "far too timid" expresses that view.)*
> 2. The writer thinks the engineering problems cannot be overcome. *(No —
>    the writer calls them "real but soluble".)*
> 3. The writer argues rooftop gardens increase property values. *(Not Given —
>    no claim about property values is made.)*

## Complete the Words (TOEFL iBT, 2026 format)

A C-test: the second half of every second word is removed. The shape is
mechanical, so **build it with `coach ctest make` — never by hand.** You write
an ordinary paragraph; the script cuts it and prints the key.

What to write: one paragraph of about 70–80 words on an everyday or
general-academic topic, in plain sentences. Make the first sentence a real
topic sentence (it is the only context the learner gets), and leave a full
sentence or two after the tenth gap. Avoid words that only a specialist could
restore; if one is unavoidable, pass it with `--keep`.

**Source paragraph (what you write — 76 words):**

```text
Community gardens have become a common sight in many large cities. Local
people rent a small plot there and grow vegetables, fruit, or flowers for
their own use. Most gardeners say that the fresh food is only a small part
of the reward. They enjoy working outside, and they often become friends
with the people who garden next to them. Some gardens also give part of each
harvest to families in the neighbourhood who need it.
```

**What the learner sees (`coach ctest make --file paragraph.txt`):**

```text
Complete each gapped word: type the letters that are missing.

Community gardens have become a common sight in many large cities. Local
peo_ _ _ rent a sm_ _ _ plot th_ _ _ and gr_ _ vegetables, fr_ _ _, or
flo_ _ _ _ for th_ _ _ own u_ _. Most gard_ _ _ _ _ say th_ _ the fresh food
is only a small part of the reward. They enjoy working outside, and they
often become friends with the people who garden next to them. Some gardens
also give part of each harvest to families in the neighbourhood who need it.
```

**Key (missing letters):** ple · all · ere · ow · uit · wers · eir · se · eners · at

**Whole words:** people · small · there · grow · fruit · flowers · their · use · gardeners · that

How the rule produced this item — check any generated item against it:

1. The first sentence is whole.
2. In the rest, one-letter words (*a*) are not counted. Counting the others,
   every second one is cut: Local **people** rent (a) **small** plot **there**
   and **grow** vegetables, **fruit**, or **flowers** for **their** own
   **use**. Most **gardeners** say **that** — ten gaps, then nothing more.
3. A word keeps the first half of its letters, rounded down: *use* → `u`,
   *that* → `th`, *people* → `peo`, *gardeners* → `gard`.
4. One blank per missing letter: `gard_ _ _ _ _` is *gard* + 5 = *gardeners*.
   (The script joins the blanks of one gap with non-breaking spaces, so a
   gap is never split across two lines.)

The same item with `--style dash` prints `peo---`, `sm---`, `gard-----`; the
official material uses both styles.

Mark answers with `coach ctest check` (it rebuilds the key from the same
paragraph): the missing letters or the whole word are both accepted, spelling
must be exact, and there is no partial credit. There is no penalty for a
wrong answer, so tell the learner to fill every gap.

## Inference multiple choice (TOEFL reading format)

> **Passage (extract):** Early lighthouse keepers rarely kept written logs of
> minor repairs, an omission historians now regret. When a lamp mechanism at
> the Point Harrow light failed in 1861, the replacement was recorded only
> because the part had to be ordered from the mainland.
>
> What can be inferred about repairs at Point Harrow before 1861?
> A. They were usually carried out by mainland engineers.
> B. Most were done with materials already at the lighthouse. ✅
> C. They were documented in detail by historians.
> D. They rarely involved the lamp mechanism.
>
> *(B: the repair was logged only because a part came from the mainland,
> implying ordinary repairs used on-site materials and went unrecorded.)*
