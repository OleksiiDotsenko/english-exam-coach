# Canonical task-type slugs

The progress log groups attempts by the exact `--task-type` string, and the
"weakest task type" recommendation (used by `/daily-drill` and `/start-prep`)
depends on that grouping. **Always log with the slug from this table** so a
task drilled today aggregates with the same task drilled last week. Slugs are
lowercase-kebab-case, stable, and shared across skills.

If a task type is genuinely missing here, coin a slug in the same style
(lowercase, hyphenated, exam-neutral where possible) and add it to this file
in the same PR — never invent an ad-hoc variant at log time.

## Writing

| Slug | Exams | Task |
|---|---|---|
| `ielts-task1-visual` | ielts-academic | Describe a graph/table/chart/process/map |
| `ielts-task1-letter` | ielts-general | Letter (formal/semi-formal/informal) |
| `ielts-task2-essay` | ielts-academic, ielts-general | Discursive essay |
| `toefl-build-a-sentence` | toefl-ibt | Arrange words into a sentence |
| `toefl-write-email` | toefl-ibt | Write an email (3 content points) |
| `toefl-academic-discussion` | toefl-ibt | Contribute to a class discussion |
| `essay` | cefr-b1…cefr-c2 | Compulsory essay (Part 1) |
| `article` | cefr-b1…cefr-c2 | Article |
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
| `toefl-complete-the-words` | toefl-ibt | C-test cloze |
| `toefl-read-daily-life` | toefl-ibt | Practical short texts, MCQ |
| `toefl-read-academic` | toefl-ibt | Short academic passage, MCQ |
| `reading-multiple-choice` | cefr-b1…cefr-c2, ielts | Long-text reading comprehension, multiple choice |
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
| `ielts-listening-part1`…`part4` | ielts-academic, ielts-general | Parts 1–4 |
| `toefl-listen-choose-response` | toefl-ibt | Pick the natural reply |
| `toefl-listen-conversation` | toefl-ibt | Campus conversation |
| `toefl-listen-announcement` | toefl-ibt | Announcement |
| `toefl-listen-academic-talk` | toefl-ibt | Academic talk |
| `listening-part1`…`part4` | cefr-b1…cefr-c2 | Parts 1–4 |

## Vocabulary & diagnostics

| Slug | Skill | Task |
|---|---|---|
| `spaced-review` | vocabulary-builder | Leitner review round |
| `level-diagnostic` | exam-router | 15-minute level probe |
