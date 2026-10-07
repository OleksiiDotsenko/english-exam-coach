# Task-type slugs and area labels

Two fields on every logged attempt must be written exactly, because the
reports group by them: `--task-type` (which task) and `--skill` (which area
of practice). A task drilled today only lines up with the same task drilled
last week if both strings match.

## Area labels — `--skill`

| Label | Area |
|---|---|
| `writing-evaluator` | writing |
| `speaking-coach` | speaking |
| `reading-use-of-english` | reading and use of English |
| `listening-trainer` | listening |
| `vocabulary-builder` | vocabulary |
| `exam-router` | the level check only |

The labels are historical names and are kept as they are so that logs
written by earlier versions keep grouping with new ones.

## Task types — `--task-type`

Slugs are lowercase, hyphenated and stable. If a task type is genuinely
missing, coin a slug in the same style and add it here in the same change —
never invent a variant at log time.

## Writing

| Slug | Exams | Task |
|---|---|---|
| `ielts-task1-visual` | ielts-academic | Describe a graph/table/chart/process/map |
| `ielts-task1-letter` | ielts-general | Letter (formal/semi-formal/informal) |
| `ielts-task2-essay` | ielts-academic, ielts-general | Discursive essay |
| `toefl-build-a-sentence` | toefl-ibt | Build the reply to a sentence from word tiles |
| `toefl-write-email` | toefl-ibt | Write an email (three bullet points) |
| `toefl-academic-discussion` | toefl-ibt | Contribute to a class discussion |
| `essay` | cefr-b2…cefr-c2 | Compulsory essay (Part 1; B1 has no essay — its Part 1 is an email) |
| `article` | cefr-b1, cefr-b2, cefr-c2 | Article (C1 Advanced has no article task) |
| `email-letter` | cefr-b1…cefr-c2 | Email or letter |
| `report` | cefr-b2…cefr-c2 | Report |
| `review` | cefr-b2…cefr-c2 | Review |
| `proposal` | cefr-c1 | Proposal |
| `story` | cefr-b1 | Story |

## Speaking

| Slug | Exams | Task |
|---|---|---|
| `ielts-part1-interview` | ielts-academic, ielts-general | Part 1 interview |
| `ielts-part2-long-turn` | ielts-academic, ielts-general | Part 2 cue-card long turn |
| `ielts-part3-discussion` | ielts-academic, ielts-general | Part 3 discussion |
| `toefl-listen-and-repeat` | toefl-ibt | Repeat spoken sentences |
| `toefl-take-an-interview` | toefl-ibt | Answer interview questions |
| `speaking-interview` | cefr-b1…cefr-c2 | Part 1 interview |
| `speaking-long-turn` | cefr-b1…cefr-c2 | Individual long turn |
| `speaking-collaborative` | cefr-b1…cefr-c2 | Collaborative/paired task |
| `speaking-discussion` | cefr-b1…cefr-c2 | Discussion |

## Reading & Use of English

| Slug | Exams | Task |
|---|---|---|
| `ielts-matching-headings` | ielts-academic, ielts-general | Match headings to paragraphs |
| `ielts-tf-not-given` | ielts-academic, ielts-general | True/False/Not Given (facts) |
| `ielts-yn-not-given` | ielts-academic, ielts-general | Yes/No/Not Given (writer's views) |
| `ielts-matching-information` | ielts-academic, ielts-general | Locate information / match features |
| `ielts-sentence-completion` | ielts-academic, ielts-general | Sentence / note / table / summary completion |
| `ielts-short-answer` | ielts-academic, ielts-general | Short-answer questions |
| `toefl-complete-the-words` | toefl-ibt | Complete the Words (a paragraph with 10 half-deleted words) |
| `toefl-read-daily-life` | toefl-ibt | Practical short texts, MCQ |
| `toefl-read-academic` | toefl-ibt | Short academic passage, MCQ |
| `reading-multiple-choice` | cefr-b1…cefr-c2, ielts-academic, ielts-general | Long-text reading comprehension, multiple choice |
| `multiple-choice-cloze` | cefr-b1…cefr-c2 | Multiple-choice cloze (gap-fill) |
| `open-cloze` | cefr-b1…cefr-c2 | Open cloze |
| `word-formation` | cefr-b2…cefr-c2 | Word formation |
| `key-word-transformation` | cefr-b2…cefr-c2 | Key word transformation |
| `gapped-text` | cefr-b1…cefr-c2 | Gapped text |
| `cross-text-matching` | cefr-c1 | Cross-text multiple matching (compare four texts' opinions) |
| `multiple-matching` | cefr-b1…cefr-c2 | Multiple matching (locate information) |

## Listening

| Slug | Exams | Task |
|---|---|---|
| `ielts-listening-part1` | ielts-academic, ielts-general | Part 1 — everyday conversation |
| `ielts-listening-part2` | ielts-academic, ielts-general | Part 2 — everyday monologue |
| `ielts-listening-part3` | ielts-academic, ielts-general | Part 3 — study-context discussion |
| `ielts-listening-part4` | ielts-academic, ielts-general | Part 4 — academic monologue |
| `toefl-listen-choose-response` | toefl-ibt | Pick the natural reply |
| `toefl-listen-conversation` | toefl-ibt | Short conversation (everyday, workplace or campus) |
| `toefl-listen-announcement` | toefl-ibt | Announcement |
| `toefl-listen-academic-talk` | toefl-ibt | Academic talk (lecture or podcast style) |
| `listening-part1` | cefr-b1…cefr-c2 | Part 1 |
| `listening-part2` | cefr-b1…cefr-c2 | Part 2 |
| `listening-part3` | cefr-b1…cefr-c2 | Part 3 |
| `listening-part4` | cefr-b1…cefr-c2 | Part 4 |

## Vocabulary & diagnostics

| Slug | Area label | Task |
|---|---|---|
| `spaced-review` | vocabulary-builder | Leitner review round |
| `level-diagnostic` | exam-router | 15-minute level probe |
