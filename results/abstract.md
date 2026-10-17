# Abstract

**Written for:** poster viewers.

Can AI models correctly answer AI-generated multiple-choice comprehension
questions about real student code — and which kinds of questions are
hardest? We sampled 185 real, grader-passed Python solutions (seed 42,
spanning all 21 tasks) from a published student-submissions dataset
(Petersen-Frey et al., LREC 2022) and used a template-based, AutoMCQ-style
generator (built on Python AST analysis and the dataset's own test cases,
never executing student code to self-check) to produce 996 multiple-choice
questions across 8 comprehension categories: output, variable state, loop
trace, control flow, call count, edge case, code modification, and
data-structure state. Every answer key was then verified by actually
running the student's code — 76% of questions had an execution-verified
ground truth, and 19.2% of the generator's own answer keys were wrong when
checked this way, itself a finding about automated question generation at
scale. We evaluated 7 commercial-model/setting combinations (OpenAI GPT-6
Luna and GPT-6 Astra; Anthropic Claude Haiku 5.5 and Claude Opus 5, each at
a minimal and an enabled reasoning/thinking setting) against execution
ground truth, spending under $7 total via each provider's batch API with
real per-call cost tracked throughout. Accuracy ranged from 58.1% to 94.9%
across models and settings. Reasoning/thinking mattered: GPT-6 Luna rose
from 79.1% to 93.0% and Claude Haiku 5.5 from 58.5% to 94.1% when enabled.
Tracing loop iterations and branch execution were the hardest categories
(67–68% average accuracy) across every model; tracking how many times a
function is called and reading simple data-structure state were easiest
(85–89%). Surprisingly, Claude Opus 5 — despite being a larger, costlier
model — underperformed every other commercial model (58–61%) and left
36–40% of answers unparseable, writing out visible step-by-step reasoning
text even with "thinking" formally disabled, instead of answering directly.
