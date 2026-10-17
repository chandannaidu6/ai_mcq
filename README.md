# AI-generated MCQ comprehension pilot

Research question: **Can AI models correctly answer AI-generated multiple-choice
comprehension questions about real student code?**

Claude (this session) acted as the **question generator**. Open-source models
downloaded from Hugging Face and run locally on this machine's GPU acted as
the **answerers**, via vLLM. No paid API was used anywhere in this pipeline.

## Environment

- GPU: NVIDIA RTX 4000 Ada Generation, 20475 MiB (~20 GB) VRAM
- Driver/CUDA: driver reports CUDA 13.0 (`nvidia-smi`)
- Python: 3.10.12 (venv at `venv/`)
- Key packages: `vllm==0.31.0`, `torch==2.13.0+cu130`, `matplotlib`
- Note: the system's default `nvcc` (CUDA 11.3, from the Anaconda install) cannot
  JIT-compile vLLM's FlashInfer sampling kernel against this driver/GPU combo.
  All model runs set `VLLM_USE_FLASHINFER_SAMPLER=0` to fall back to the
  built-in PyTorch sampler (no effect on correctness, negligible effect on speed
  at these batch sizes/lengths).

## Dataset

*Dataset of Student Solutions to Algorithm and Data Structure Programming
Assignments* (Fynn Petersen-Frey, Marcus Soll, Louis Kobras, Melf Johannsen,
Peter Kling, Chris Biemann — LREC 2022, Universität Hamburg).
License: CC BY-NC 4.0.

Download page: https://www.inf.uni-hamburg.de/en/inst/ab/lt/resources/data/ad-lrec
Direct zip found on that page: `ad2022dataset.zip`
(saved to `data_raw/ad2022dataset.zip`, extracted to `data_extracted/AD2022dataset/`).

The dataset contains 3 years of CSVs (`*_solutions.csv`, `*_task_descriptions.csv`,
`*_tests.csv`) covering 21 distinct tasks, each with both Java and Python student
submissions (687 total Python solutions, 0 of which needed `input()` or `open()`).

## Pipeline

```
python pilot.py                 # runs all 5 steps in order
# or individually:
python scripts/01_sample_solutions.py
python scripts/02_generate_questions.py
python scripts/03_verify_answer_keys.py
python scripts/04_run_all_models.py     # needs a CUDA GPU; ~10-15 min total
python scripts/05_analyze.py
```

1. **`01_sample_solutions.py`** -- loads all Python solutions from the 3 years'
   CSVs, filters out any using `input()`/`open()` (none needed filtering out, in
   practice), and randomly samples 25 solutions with `seed=42`, round-robin
   across tasks to maximize task coverage. Output: `pilot_data/sampled_solutions.json`.
   Result: 25 solutions spanning **all 21** distinct Python tasks in the dataset.

2. **`02_generate_questions.py`** -- for each of the 25 solutions, 4
   hand-authored multiple-choice questions (one per category: `output`,
   `variable_state`, `loop_trace`, `control_flow`), each with 4 options and a
   `verification_code` snippet. Written in a single pass, AutoMCQ-style, with
   **no execution-based self-checking before saving** (per the pilot's
   protocol) -- any wrong answer keys are caught and reported, not silently
   fixed, in step 3. Output: `results/questions.json` (100 questions).

3. **`03_verify_answer_keys.py`** -- for every question, assembles
   `student_solution_code + task harness (if any) + tracer helpers +
   verification_code`, runs it in a subprocess with a 5s timeout, and matches
   the printed output to one of the 4 options to get `ground_truth_option`.
   Flags any mismatch between the generator's `answer_key` and the execution
   ground truth as `key_is_correct: false` (left uncorrected, as required).
   Output: `results/questions_verified.json`.

4. **`04_run_all_models.py`** -- runs each of the 4 target models, **one per
   OS subprocess** (`04_run_one_model.py <model_id> <out.json>`), so GPU memory
   is fully released by the OS between models rather than relying on
   in-process vLLM teardown. Settings: `max_model_len=4096`,
   `gpu_memory_utilization=0.85`, `temperature=0`, `max_tokens=10`, using each
   model's chat template via `vllm.LLM.chat`. Any model that fails to load is
   skipped and the reason recorded in `results/model_run_log.json`; the run
   continues with the remaining models. Output:
   `results/model_answers_<slug>.json` per model + `results/model_run_log.json`.

5. **`05_analyze.py`** -- builds `results/questions.csv`, `results/summary.md`,
   `results/accuracy_by_category.png`, `results/accuracy_by_size.png`.

## Files

- `scripts/harness.py` -- shared code: the generic line-tracer helpers
  (`__trace_hits`, `__trace_var`, `__trace_lines`, built on `sys.settrace`) used
  by `verification_code` to pull ground-truth values straight out of a real
  execution of the student's code (not a re-implementation), plus the few
  task-specific support classes (`Node`, `CustomStack`, `ListToSort`) that a
  handful of solutions need as callers/collaborators, not written by the
  student.
- `pilot_data/sampled_solutions.json` -- the 25 sampled solutions + metadata.
- `pilot_data/numbered_code.txt` -- line-numbered listing used while authoring
  the `verification_code` snippets (line numbers must match exactly for the
  tracer to work).
- `results/` -- all deliverables (see `summary.md` for the final report).

## Poster materials (final scope)

The final deliverable is the **commercial-model-only** comparison. See:

- `results/abstract.md` — poster abstract
- `results/procedure.md` — methods/procedure section
- `results/results_summary.md` — full findings write-up, including a
  "which questions are hardest" deep dive and two honestly-disclosed
  measurement caveats found during fact-checking
- `results/summary_v2.md` — the same data as machine-generated tables
- `results/accuracy_all_models.png`, `accuracy_by_category_all.png`,
  `thinking_effect.png`, `poster_*.png` (4 additional charts: category
  difficulty ranking, category x model heatmap, generator reliability,
  validity-vs-accuracy) — built with the dataviz skill's validated palette
- `results/cost_log.csv`, `results/prices.json` — real per-call spend

7 commercial model/settings were evaluated (OpenAI GPT-6 Luna x2 settings
and GPT-6 Astra; Anthropic Claude Haiku 5.5 x2 and Claude Opus 5 x2),
scored against the same 996-question, execution-verified set built in the
v2 pipeline below. **Open-source model results (Qwen2.5-Coder, DeepSeek)
and the original 25-solution/4-category v1 pilot's output files were
removed from `results/`** per explicit user instruction once the full
commercial comparison was complete (recoverable from git history; the
pipeline scripts that produced them are untouched and still re-runnable).
Run `python scripts/07_poster_plots.py` to regenerate the 4 poster-specific
charts, or `python scripts/06_analyze_v2.py` for the tables/machine-written
summary.

## v2: expanded 8-category, multi-provider pilot

A second, larger run reuses everything above and extends it. See
`results/summary_v2.md` for the final report. Research question: can AI
models answer AI-generated comprehension questions across 8 categories
(adding `call_count`, `edge_case`, `code_modification`, `data_structure_state`
to the original 4), and which categories/providers are hardest?

```
python scripts/01_sample_solutions.py data_extracted/AD2022dataset pilot_data/sampled_solutions_v2.json 185
python scripts/02_generate_questions_v2.py
python scripts/03_verify_answer_keys_v2.py
python scripts/04_run_all_models_v2.py          # GPU, ~4 models, one subprocess each
python scripts/05c_openai_batch.py submit       # then: poll
python scripts/05d_anthropic_batch.py submit    # then: poll
python scripts/05e_build_cost_log.py
python scripts/06_analyze_v2.py
```

Key differences from v1:
- **185 solutions** (seed=42, strict superset of the original 25), all 21 tasks.
- **Template-based (AutoMCQ-style) generator** (`scripts/gen_lib.py`,
  `scripts/02_generate_questions_v2.py`) instead of hand-authoring every
  question -- uses `ast` analysis of each solution plus the dataset's own
  `tests.csv` test cases and `tester` harness preambles as grounding, in one
  pass, with no execution-based self-checking (same rule as v1). Produced
  **1005 questions**; **701 (70%)** have execution-verified ground truth;
  **101 (14%)** of the generator's own answer keys were wrong when checked
  (left uncorrected, reported as a finding, broken down by category).
- A tester's preamble can bundle a full **reference solution** (used
  internally for comparison-based grading) alongside genuinely-needed
  support classes. `gl.filter_harness_to_needed` strips anything not
  referenced by name in the student's code or the dataset's own tests,
  so what's shown to answering models (`harness_code_display`) never
  leaks a reference solution, while the full harness (`harness_code`) is
  still used for execution/verification.
- Network access is disabled inside the Step 3 verification subprocess
  (`harness.NETWORK_BLOCK_CODE`).
- **Answerers**: Qwen2.5-Coder 3B/7B-AWQ/14B-AWQ (confirmed via the HF API
  that 32B-class quantizations need ~19GB+ weights alone and don't fit this
  20GB GPU, so 14B-AWQ is genuinely the largest that fits),
  DeepSeek-Coder-V2-Lite-Instruct-AWQ, GPT-6 Luna (OpenAI Batch API,
  reasoning none/medium), Claude Haiku 5.5 (Anthropic Message Batches,
  thinking disabled/adaptive-high). Real model IDs and prices were looked
  up from each provider's own API/docs, never assumed (`scripts/00_list_models.py`,
  `results/prices.json`).
- **Gemini was dropped** (gemini-3.8-flash / gemini-3.5-flash-lite) after
  confirming via live calls that the free tier enforces a ~5
  requests/minute per-model quota, which would have taken ~7 hours for
  full coverage; the user asked not to use it once that became clear. The
  runner (`scripts/05b_run_gemini.py`) is resumable and kept in the repo
  in case it's revisited.
- Every paid call's real token usage (never estimated) is logged to
  `results/cost_log.csv`; both OpenAI and Anthropic stayed at a few cents
  total, far under the $9/provider cap.
- **Caveat**: Claude Haiku 5.5 is in the same model family as the question
  generator (Claude Sonnet 5), which may give it an advantage the other
  models don't have -- noted in `summary_v2.md`.
