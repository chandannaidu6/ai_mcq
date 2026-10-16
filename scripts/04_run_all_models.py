"""
Step 4 orchestrator: run each model in its OWN subprocess (so GPU memory is
fully released by the OS between models -- no reliance on in-process vLLM
teardown), one at a time, in increasing size order. Records success/failure
and skip reasons. Results for each model are saved as they complete
(results/model_answers_<slug>.json), and a run log is kept too.
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "04_run_one_model.py")
RESULTS_DIR = os.path.join(ROOT, "results")
LOG_PATH = os.path.join(RESULTS_DIR, "model_run_log.json")

MODELS = [
    dict(slug="qwen2.5-coder-3b-instruct",
         model_id="Qwen/Qwen2.5-Coder-3B-Instruct",
         quantization=None, dtype="bfloat16", gpu_mem_util=0.85),
    dict(slug="qwen2.5-coder-7b-instruct-awq",
         model_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
         quantization="awq", dtype="float16", gpu_mem_util=0.85),
    dict(slug="qwen2.5-coder-14b-instruct-awq",
         model_id="Qwen/Qwen2.5-Coder-14B-Instruct-AWQ",
         quantization="awq", dtype="float16", gpu_mem_util=0.85),
    dict(slug="deepseek-coder-6.7b-instruct",
         model_id="deepseek-ai/deepseek-coder-6.7b-instruct",
         quantization=None, dtype="float16", gpu_mem_util=0.85),
]


def main():
    log = []
    for m in MODELS:
        out_path = os.path.join(RESULTS_DIR, f"model_answers_{m['slug']}.json")
        cmd = [
            sys.executable, SCRIPT, m["model_id"], out_path,
            "--dtype", m["dtype"],
            "--gpu-mem-util", str(m["gpu_mem_util"]),
        ]
        if m["quantization"]:
            cmd += ["--quantization", m["quantization"]]

        print("=" * 80)
        print("Running:", " ".join(cmd))
        t0 = time.time()
        env = dict(os.environ)
        # the system's default nvcc (11.3) can't JIT-compile flashinfer's sampling
        # kernel for this GPU/driver combo (CUDA 13.0 driver) -- fall back to the
        # built-in PyTorch sampler, which works fine and costs negligible speed
        # at these batch sizes.
        env["VLLM_USE_FLASHINFER_SAMPLER"] = "0"
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
        elapsed = time.time() - t0

        entry = {
            "slug": m["slug"],
            "model_id": m["model_id"],
            "returncode": proc.returncode,
            "wall_time_wrapper_seconds": elapsed,
            "stdout_tail": proc.stdout[-3000:],
            "stderr_tail": proc.stderr[-3000:],
            "success": proc.returncode == 0,
        }
        log.append(entry)

        # persist the log after every model, in case a later model crashes
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)

        if proc.returncode == 0:
            print(f"OK ({elapsed:.1f}s wrapper time). See {out_path}")
        else:
            print(f"FAILED (exit {proc.returncode}) after {elapsed:.1f}s. Skipping and continuing.")
            print("--- stderr tail ---")
            print(proc.stderr[-3000:])

    print("=" * 80)
    print("All models attempted. Summary:")
    for e in log:
        status = "OK" if e["success"] else "FAILED/SKIPPED"
        print(f"  {e['slug']}: {status} ({e['wall_time_wrapper_seconds']:.1f}s)")


if __name__ == "__main__":
    main()
