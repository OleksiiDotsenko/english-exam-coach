# Tagging examples — how to turn a mistake into a re-testable point

Consult this when you are unsure which tag an error takes. The tags
themselves — the closed list, with what each one means — are in
`data/error-taxonomy.md`. Consistency is the whole value: everything
downstream groups by `category/subtype`, so the same weakness tagged three
ways is scheduled three times and never resolved.

The rule behind every row: **the tag says what kind of thing went wrong; the
point says what a fresh item must test.** If a point could not be turned into
a new question, it is not a point — it is a complaint.

| Learner's error | category | subtype | `--point` |
|---|---|---|---|
| "the informations were useful" | grammar | countability | information as an uncountable noun |
| "I have seen him yesterday" | grammar | verb-form | present perfect vs past simple with a finished time |
| "By the time I arrived, he left" | grammar | verb-form | past perfect after "by the time" |
| "Each of the students have a laptop" | grammar | agreement | agreement with "each of the" |
| "I look forward to meet you" | grammar | verb-form | gerund after "look forward to" |
| "She is married with a doctor" | grammar | preposition | married to, not married with |
| "It depends of the weather" | grammar | preposition | depend on, not depend of |
| "Never I have seen such a thing" | grammar | word-order | inversion after a fronted negative |
| "The book which I told you about it" | grammar | clause | no resumptive pronoun in a relative clause |
| "You must to finish by Friday" | grammar | modality | bare infinitive after modal verbs |
| "I cannot concentrate myself" | grammar | pronoun | no reflexive after concentrate |
| "Is important to check the date" | grammar | omission | dummy subject it before is + adjective |
| "She very tired after the trip" | grammar | omission | the verb be before an adjective |
| "I did a mistake" | lexis | collocation | make vs do collocations |
| "a strong rain fell" | lexis | collocation | heavy rain, not strong rain |
| "The results were very good, so the hypothesis is confirmed" (in a formal report) | lexis | register | hedging in academic conclusions |
| "economical growth" | lexis | word-formation | economic vs economical |
| "I recieved the letter" | lexis | spelling | i before e after c |
| "Also… Also… Also…" across a paragraph | lexis | range | varying additive linkers |
| "borrow me your pen" | lexis | word-choice | borrow vs lend |
| "It will actualize the problem" | lexis | non-word | raise or highlight a problem, not actualize |
| "In my opinion, I think that" | lexis | redundancy | one opinion marker per sentence |
| Every sentence opens with "Moreover" | discourse | cohesion | overusing additive linkers as sentence openers |
| One 300-word block with no breaks | discourse | paragraphing | one idea per paragraph with a topic sentence |
| "Firstly… Thirdly… Secondly…" | discourse | coherence | ordering signposts to match the argument |
| A claim made and immediately abandoned | discourse | development | supporting a claim with a reason and an example |
| Essay argues "both views" when asked "to what extent do you agree" | task | task-response | answering the question actually asked |
| Email covers 2 of the 3 required points | task | content-point | covering every bullet in the prompt |
| 180 words for a 250-word task | task | length | reaching the minimum word count |
| Informal contractions in a formal proposal | task | audience | register for an unknown senior reader |
| Chose an option restating the text's wording | comprehension | distractor | word-match traps in multiple choice |
| Missed that "declined" paraphrased "fell sharply" | comprehension | paraphrase | recognising paraphrases of trend verbs |
| Answered TRUE where the text was silent | comprehension | inference | True vs Not Given when the text does not say |
| Wrote three words where the limit was two | comprehension | instruction | obeying the word limit in completion tasks |
| Heard "fifty" as "fifteen" | comprehension | detail | -teen vs -ty in spoken numbers |
| Asked why the speaker mentions a film, answered what the film is about | comprehension | purpose | purpose questions answered with the topic |
| Asked what the passage is mainly about, chose a detail from one paragraph | comprehension | main-idea | main-idea questions answered with a detail |
| "Didn't you send it yet?" answered as if it were "Did you send it?" | comprehension | negation | negative questions answered backwards |
| Chose the one true statement in an EXCEPT question | comprehension | negation | EXCEPT and NOT questions read as ordinary ones |
| Put a sentence where it broke the link between "this" and its noun | comprehension | structure | following reference words when placing a sentence |
| Could not answer because "curating" was unknown | comprehension | vocabulary | working out an unknown word from its sentence |
| Repeated "on the shelves by the window" as "on the shelf near window" | delivery | repetition | keeping articles and plurals when repeating a long sentence |
| Long silence before starting each answer | delivery | fluency | starting with a stalling phrase, not silence |
| Ran out of time with two items unanswered | strategy | timing | pacing a section against its item count |
| Started writing with no plan and repeated a point | strategy | planning | two-minute plan before writing |

## Judgement calls

- **One error, one tag.** "The informations were useful" is a countability
  error, not also a spelling and agreement error. Tag the cause, not the
  symptoms.
- **Grammar or lexis?** If the word is right but its form or structure is
  wrong, it is grammar. If the choice of word is wrong, it is lexis.
- **Task or discourse?** Task is about the prompt's requirements (what was
  asked, how long, for whom). Discourse is about how the text holds together
  regardless of the prompt.
- **Comprehension covers reading and listening alike** — what went wrong is
  the same family of thing whether the input was read or heard.
- **Purpose or main idea?** "Why does the speaker mention X?" answered with
  what X is → `purpose`. "What is it mainly about?" answered with one of its
  details → `main-idea`.
- **Word-choice or non-word?** A real English word used wrongly is
  `word-choice`; a form that is not an English word at all (often a word
  from the first language given an English ending) is `non-word`.
- **Omission or article?** A missing article is `article`. `omission` is
  for a missing verb, subject or auxiliary.
- **Carried over from the first language?** The tag stays what it is; add
  `--transfer` to say what the first language does.
- **`strategy` is for the process, not the language.** Use it when the
  language was available but the approach lost the marks.
- If two tags genuinely fit, pick the one whose drill you would actually
  build, and put the detail in `--point`.
