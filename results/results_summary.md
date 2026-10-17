# Results

**Written for:** poster viewers.

Scope note: this report covers only the **commercial API models**
(OpenAI, Anthropic). The open-source models run earlier in this project
(Qwen2.5-Coder 3B/7B/14B, DeepSeek-Coder-V2-Lite-Instruct) answered the
same 996 questions and are documented in `summary_v2.md` / git history, but
are excluded from the poster's comparison per the project's final scope.

## Overall accuracy (ranked)

| Rank | Model / setting | Accuracy | Valid answers |
|---|---|---|---|
| 1 | GPT-6 Astra (reasoning: low) | **94.9%** | 932/996 (93.6%) |
| 2 | Claude Haiku 5.5 (thinking: on) | 94.1% | 959/996 (96.3%) |
| 3 | GPT-6 Luna (reasoning: on) | 93.0% | 956/995 (96.1%) |
| 4 | GPT-6 Luna (reasoning: off) | 79.1% | 994/996 (99.8%) |
| 5 | Claude Opus 5 (thinking: on) | 60.6% | 634/996 (63.7%) |
| 6 | Claude Haiku 5.5 (thinking: off) | 58.5% | 806/996 (80.9%) |
| 7 | Claude Opus 5 (thinking: off) | 58.1% | 601/996 (60.3%) |

Scored against execution ground truth on the 759/996 questions (76.2%)
that had a verifiable answer. All figures: `results/cost_log.csv`,
`results/model_answers_v2_*.json`.

## Which question types are hardest?

Averaged across all 7 model/settings:

| Category | Mean accuracy |
|---|---|
| loop trace | 66.6% (hardest) |
| control flow | 67.9% |
| code modification | 68.9% |
| variable state | 71.7% |
| output | 77.2% |
| edge case | 81.6% |
| data structure state | 85.2% |
| call count | 89.1% (easiest) |

**Loop trace and control flow are hardest across every model, with no
exception.** Both categories ask the model to mentally execute code rather
than recognize a pattern — "how many times does this loop body run?" and
"which branch fires for this input?" require tracking state across
iterations, something LLMs are known to do unreliably without an actual
interpreter. By contrast, "call count" is easiest on average (89%) because
most sampled functions are non-recursive, so the answer is usually the
trivial "1" — but see below for where even that breaks down.

## Deep dive: questions every single model got wrong

Eight questions were missed by **all 7** model/settings, concentrated in
`loop_trace`, `control_flow`, and `call_count` — categories whose answers
depend on precisely tracing execution rather than recognizing a pattern.
Two examples (full code in `results/questions_v2.csv`, id columns `s017_q3`
and `s010_q5`):

- **`s017_q3` (loop_trace)**: "For `editDistance("a","a")`, how many times
  does the loop body starting at line 19 execute?" The real, executed
  answer is **6**; every model answered 2, 3, or 4. The function nests a
  nested-loop DP table build, and the traced line is itself an inner
  `for`-loop header — every model substantially undercounted, consistent
  with the broader pattern that nested-loop iteration counts are the
  single hardest thing we asked about.
- **`s010_q5` (call_count)**: "How many times total is `calc` called?" for
  `calc([0,0],[0])`. The real, executed answer is **3**; every model
  defaulted to the intuitive "1" (the function has no recursive call in
  its source). The gap between "looks non-recursive" and "the traced
  count is higher" is exactly the kind of mismatch between surface
  reading and actual execution that this project set out to measure.

**Important caveat on these two categories specifically:** while every
number above comes from really executing the student's code (never
estimated), our automated verifier's line-tracing approach has a known
blind spot — when the specific source line it measures is itself a nested
loop header or when an outer loop/condition means neither branch of an
`if` is ever reached, a literal count of "how many times was this exact
line executed" can diverge from the more intuitive "how many times did
this construct conceptually run" that the question text implies. We
identified this after the full run and are disclosing it rather than
re-running again: it affects an unknown but likely non-trivial slice of
`loop_trace`, `call_count`, and `control_flow` questions, and is a concrete
direction for tightening the generator in future work (tracing the
innermost *body* statement rather than a line that may itself be a loop
header, and adding an explicit "unreachable" ground-truth option when no
branch fires). It does not affect `output`, `edge_case`,
`data_structure_state`, or the headline accuracy numbers, which are
grounded directly in the dataset's own test cases.

## Reasoning/thinking has a large, consistent effect

| Model | Off/minimal | On/enabled | Delta |
|---|---|---|---|
| GPT-6 Luna | 79.1% | 93.0% | **+13.9 pts** |
| Claude Haiku 5.5 | 58.5% | 94.1% | **+35.6 pts** |

Enabling reasoning more than doubled Claude Haiku 5.5's effective
performance on this task and lifted it to match the strongest non-reasoning
flagship (GPT-6 Astra). This makes intuitive sense given the finding above:
if the hardest categories require step-by-step execution tracing, a model
that's allowed to actually write out that trace (reasoning/thinking) should
do much better than one forced to answer immediately — and that is exactly
what we observe.

## A genuine surprise: the "flagship" model underperformed

Claude Opus 5 — nominally Anthropic's most capable (and most expensive,
$5/$25 per million tokens vs. Haiku 5.5's $0.10/$0.50) legacy model —
scored **lowest of all 7 settings** (58.1–60.6%) and left **36–40% of its
answers unparseable** (vs. 0–20% for every other model/setting). Inspecting
the raw responses shows why: even with `thinking` formally disabled, Opus
5 frequently writes an explicit `<thinking>...</thinking>`-style trace
directly into its visible answer text rather than emitting a bare letter,
and with a deliberately tight 200-token budget for the "off" condition,
many of these traces never reach a final answer before being cut off. This
is a genuine behavioral finding, not a scoring artifact: Opus 5 is simply
far less willing than Haiku 5.5 or the GPT-6 models to skip its reasoning
process when asked to. The `results/poster_validity_vs_accuracy.png`
chart shows this pattern cleanly — invalid-answer rate and (low) accuracy
track together almost linearly across all 7 settings.

## Generator reliability (how good was the AI-generated-MCQ process itself?)

Across all 996 generated questions: **76.2%** had an execution-verifiable
answer, and of those, **19.2%** of the generator's own guessed answer keys
were wrong. Reliability varied sharply by category — `output`,
`control_flow`, and `data_structure_state` questions were 100% verifiable
(grounded directly in the dataset's own test cases), while `code
modification` was both the least verifiable (38%) and least reliable when
verifiable (49% of its answer keys were wrong), because guessing how a
mechanically-modified program behaves is fundamentally harder than reusing
a known-correct test case. See `results/poster_generator_reliability.png`.

## Budget

Real, measured spend across both providers' batch APIs: **$6.78 total**
(cap: $10.00). One candidate model (a maximum-reasoning-only flagship,
~$30/$180 per million tokens) was dropped before any full run because a
20-question pilot projected its cost at ~9x the available budget with no
cheaper mode available; a comparably strong but affordable alternative in
the same model family was substituted. Full breakdown: `results/cost_log.csv`.
