#!/usr/bin/env python3
"""
End-to-end pilot: "Can AI models correctly answer AI-generated multiple-choice
comprehension questions about real student code?"

Re-runs the whole pipeline in order. Each step is also a standalone script
under scripts/ and can be re-run individually.

    0. (manual) environment check -- see README.md
    1. scripts/01_sample_solutions.py    -- download/parse the AD2022 dataset,
                                             sample 25 Python solutions (seed=42)
    2. scripts/02_generate_questions.py  -- hand-authored 4 MCQs/solution (100 total)
    3. scripts/03_verify_answer_keys.py  -- execute student code + verification
                                             snippets to get ground truth, check
                                             the generator's own answer keys
    4. scripts/04_run_all_models.py      -- run each open-source model (vLLM, GPU)
                                             on all 100 questions, one subprocess
                                             per model so GPU memory is released
                                             cleanly between models
    5. scripts/05_analyze.py             -- questions.csv, summary.md, PNG charts

Step 1 requires the AD2022dataset.zip already downloaded to data_raw/ and
extracted to data_extracted/ (see README.md for the exact URL used).
Step 4 requires a CUDA GPU and the packages in requirements.txt (vLLM).
"""
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    "scripts/01_sample_solutions.py",
    "scripts/02_generate_questions.py",
    "scripts/03_verify_answer_keys.py",
    "scripts/04_run_all_models.py",
    "scripts/05_analyze.py",
]


def main():
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    for step in STEPS:
        if only and step not in only and os.path.basename(step) not in only:
            continue
        print("=" * 80)
        print("STEP:", step)
        print("=" * 80)
        result = subprocess.run([sys.executable, "-I", os.path.join(ROOT, step)], cwd=ROOT)
        if result.returncode != 0:
            print(f"Step {step} failed with exit code {result.returncode}. Stopping.")
            sys.exit(result.returncode)


if __name__ == "__main__":
    main()
