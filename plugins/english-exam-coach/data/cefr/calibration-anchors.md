# Calibration anchors — leveled writing samples (original)

Four original excerpt-length answers to ONE shared prompt, each typical of
its CEFR level, with the reasoning that places it there. Use them to anchor
band judgments so that scoring stays consistent across sessions: place the
user's text next to the nearest anchor(s) per criterion BEFORE fixing a
range. These are demonstration texts written for this plugin — not official
samples, not model answers to teach from.

**Shared prompt:** *"Some people believe cities should reserve more streets
for walking and cycling. Do you agree or disagree?"*

## B1

> I think it is good idea to make more streets for walking and cycling.
> First reason, the air in city will be more clean. Many cars make smoke
> and it is bad for childrens and old people. Second reason, walking is
> healthy and people can do sport every day. But some people need car for
> work, so city must think also about them. In conclusion, I agree with
> this idea.

**Why B1:** the opinion is communicated clearly and the text is organised,
but with simple linkers (*first reason, but, so*), short simple sentences,
narrow lexical range, and frequent basic errors (missing articles,
*childrens*, *more clean*) that never block understanding.

## B2

> In my opinion, reserving more streets for pedestrians and cyclists would
> clearly improve urban life. The main advantage is environmental: fewer
> cars in the centre means less pollution and quieter neighbourhoods.
> Moreover, people who walk or cycle regularly tend to be healthier and
> less stressed. Critics argue that closing streets creates traffic
> problems elsewhere, which is partly true. However, if cities invest in
> good public transport at the same time, this disadvantage can be reduced
> significantly.

**Why B2:** clear paragraph logic with a range of linkers (*moreover,
however*), some complex sentences including a conditional, adequate
topic-appropriate lexis (*reserving, invest*), and only rare minor slips —
but the arguments stay general and the cohesion is visible rather than
effortless.

## C1

> Handing street space back to pedestrians and cyclists is often framed as
> an attack on drivers, yet the evidence points the other way. Cities that
> have pedestrianised their centres report not only cleaner air but also
> higher footfall for local businesses — the customers cars supposedly
> brought never really materialised. Admittedly, tradespeople and residents
> with limited mobility still need vehicle access, which is why successful
> schemes are selective rather than absolute. The question is not whether
> to reallocate space, but how quickly.

**Why C1:** flexible, controlled structures (fronted framing, *not only…
but also*, concession with *admittedly*), precise lexis (*footfall,
reallocate, materialised*), cohesion that feels invisible, a nuanced
position — and virtually no errors.

## C2

> That a city should have to justify letting people walk down its own
> streets says a great deal about how thoroughly the car has colonised our
> sense of what public space is for. Reclaiming even a handful of streets
> does more than cut emissions; it quietly renegotiates the contract
> between a city and its inhabitants. The objections — displaced traffic,
> inconvenienced deliveries — are real but soluble, and treating them as
> decisive mistakes friction for impossibility.

**Why C2:** full rhetorical control (the fronted subject that-clause, the weighed
parenthesis), metaphor deployed with purpose (*colonised, renegotiates the
contract*), meaning compressed with precision (*mistakes friction for
impossibility*) — the language shapes the argument rather than merely
carrying it.

## How to use the anchors

1. Read the user's text, then find the nearest anchor **per criterion**
   (task response / coherence / lexis / grammar) — a text can sit at B2
   for grammar and C1 for ideas; say so explicitly.
2. Derive the CEFR estimate from anchor proximity, then convert to the
   exam's scale via `data/exam-formats/<exam>.md`. Report a range, not a
   point.
3. Anchors are excerpts: judge length, task completion, and format
   separately against the task's requirements (see the writing-evaluator
   `task-anatomy.md`).
4. Never present anchor texts to the user as model answers to memorise;
   they exist to calibrate the evaluator, not to teach templates.
