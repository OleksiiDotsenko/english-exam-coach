# Error taxonomy

Every mistake logged with `coach log-error` carries one tag from this closed
list — `category/subtype` — plus a free-text **point** naming the specific
thing to re-test. The list is closed on purpose: free-form tags drift
("articles", "article", "determiners") until nothing groups, and a mis-tagged
mistake drills the wrong thing for weeks. The script rejects anything else.

Choosing a tag:

- Tag the **cause**, not the place. A wrong answer to a reading question is
  `comprehension/…`; the same learner's article slip in an email is
  `grammar/article`.
- One mistake, one tag. If two fit, take the one a drill would target.
- If nothing fits, do not force it and do not invent a tag: leave the mistake
  in the feedback and out of the ledger.
- The **point** carries the detail ("past perfect after *by the time*"). Before
  coining a new point, run `coach catalog --points` and reuse an existing label
  when it is the same thing — the catalog counts by label.

This file is checked against the script by the test suite; they cannot drift.

## grammar

The sentence is built wrongly.

| Tag | Use it when |
|---|---|
| `grammar/verb-form` | tense, aspect or voice wrong, or the wrong verb form after another word (look forward to meet) |
| `grammar/agreement` | subject-verb or number agreement |
| `grammar/article` | a/an/the/zero article: missing, extra or the wrong one |
| `grammar/preposition` | wrong or missing preposition |
| `grammar/word-order` | constituents in the wrong order, including inversion |
| `grammar/clause` | relative, subordinate or conditional clause structure |
| `grammar/countability` | countable/uncountable treatment of a noun |
| `grammar/modality` | the wrong modal for the meaning, or the wrong form after a modal (must to go) |
| `grammar/pronoun` | wrong, missing or unnecessary pronoun, reflexives included |
| `grammar/omission` | a required word left out: be, a subject, an auxiliary |
| `grammar/punctuation` | punctuation that changes or obscures meaning |

## lexis

The words are wrong for the job, in a text the learner wrote or said.

| Tag | Use it when |
|---|---|
| `lexis/word-choice` | a real word, wrong for this meaning |
| `lexis/collocation` | words that do not go together in natural English |
| `lexis/register` | formality that does not fit the task or reader |
| `lexis/word-formation` | wrong derived form (noun/adjective/adverb) |
| `lexis/non-word` | a form that is not an English word at all |
| `lexis/spelling` | misspelling, including exam-relevant variants |
| `lexis/range` | over-repetition where the level expects variation |
| `lexis/redundancy` | words that repeat what has already been said |

## discourse

The sentences are fine; the text does not hold together.

| Tag | Use it when |
|---|---|
| `discourse/cohesion` | linkers and referencing across sentences |
| `discourse/paragraphing` | paragraph boundaries or internal structure |
| `discourse/coherence` | ideas ordered so the reader loses the thread |
| `discourse/development` | a point asserted but not developed or supported |

## task

The language may be fine; the task was not done.

| Tag | Use it when |
|---|---|
| `task/task-response` | did not answer the question that was asked |
| `task/content-point` | a required content point missing or half-covered |
| `task/length` | under or over the word count the task sets |
| `task/format` | wrong genre conventions for the text type |
| `task/audience` | tone or stance wrong for the stated reader |

## comprehension

A reading or listening item answered wrongly — tag the reason, not the topic.

| Tag | Use it when |
|---|---|
| `comprehension/detail` | explicit information missed or misread |
| `comprehension/inference` | an inference the text supports but the learner missed |
| `comprehension/paraphrase` | did not recognise a restatement of the text |
| `comprehension/distractor` | chose a deliberate trap option |
| `comprehension/purpose` | why something is said, answered as if asked what is said |
| `comprehension/main-idea` | chose a detail when the main point or topic was asked |
| `comprehension/negation` | a negative question or a NOT/EXCEPT item read backwards |
| `comprehension/structure` | how parts relate: paragraph roles, sentence insertion |
| `comprehension/vocabulary` | did not know a word the item depended on |
| `comprehension/location` | could not find where the answer was |
| `comprehension/instruction` | broke the item's own rules (word limit, letter, form) |

## delivery

Speaking only: how it was said, where that got in the way.

| Tag | Use it when |
|---|---|
| `delivery/fluency` | hesitation or self-correction that breaks the message |
| `delivery/pace` | too fast or too slow for the task |
| `delivery/intelligibility` | a word or sound that a listener genuinely misheard |
| `delivery/repetition` | words dropped, replaced or mangled when repeating |
| `delivery/interaction` | turn-taking, responding, or holding the floor |

## vocabulary

A studied word or phrase, in vocabulary review, that did not come back correctly.

| Tag | Use it when |
|---|---|
| `vocabulary/recall` | could not produce a studied item when needed |
| `vocabulary/meaning` | recalled the item with the wrong meaning |
| `vocabulary/form` | right item, wrong grammatical form |
| `vocabulary/usage` | right meaning, wrong context or collocation |

## strategy

Marks lost to how the task was handled, not to language.

| Tag | Use it when |
|---|---|
| `strategy/timing` | ran out of time or spent it in the wrong place |
| `strategy/planning` | started producing without a usable plan |
| `strategy/checking` | an error the learner could have caught by checking |
| `strategy/technique` | did not use the method the task type rewards |
