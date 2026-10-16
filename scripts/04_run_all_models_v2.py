"""
Step 4 (v2) orchestrator: same subprocess-per-model design as the original
pilot, extended with a fallback chain for DeepSeek (try the quantized
DeepSeek-Coder-V2-Lite-Instruct first; if it fails to load/run, fall back to
deepseek-coder-6.7b-instruct, per the user's instructions) and checked
against HF for the largest Qwen coder that actually fits this GPU (20GB):
Qwen2.5-Coder-32B-Instruct-AWQ needs ~19.3GB of weights alone, which does
not leave room for KV cache/activations at gpu_memory_utilization=0.85 on
a 20GB card, so Qwen2.5-Coder-14B-Instruct-AWQ (~10GB) remains the largest
Qwen coder that fits; 3B and 7B-AWQ are also run for the size comparison.
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "04_run_one_model_v2.py")
RESULTS_DIR = os.path.join(ROOT, "results")
LOG_PATH = os.path.join(RESULTS_DIR, "model_run_log_v2.json")

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
    # DeepSeek fallback chain: try V2-Lite-Instruct-AWQ first (16B total / 2.4B
    # active MoE, ~9GB quantized weights); if it fails (community quant /
    # vLLM architecture support issues), fall back to deepseek-coder-6.7b-instruct.
    dict(slug="deepseek-coder-v2-lite-instruct-awq",
         model_id="TechxGenus/DeepSeek-Coder-V2-Lite-Instruct-AWQ",
         quantization="awq", dtype="float16", gpu_mem_util=0.85,
         fallback_slug="deepseek-coder-6.7b-instruct",
         fallback_model_id="deepseek-ai/deepseek-coder-6.7b-instruct",
         fallback_quantization=None, fallback_dtype="float16"),
]


def run_one(slug, model_id, quantization, dtype, gpu_mem_util):
    out_path = os.path.join(RESULTS_DIR, f"model_answers_v2_{slug}.json")
    cmd = [
        sys.executable, SCRIPT, model_id, out_path,
        "--dtype", dtype,
        "--gpu-mem-util", str(gpu_mem_util),
    ]
    if quantization:
        cmd += ["--quantization", quantization]

    print("=" * 80)
    print("Running:", " ".join(cmd))
    t0 = time.time()
    env = dict(os.environ)
    env["VLLM_USE_FLASHINFER_SAMPLER"] = "0"  # see README: system nvcc can't JIT the flashinfer sampler kernel
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    elapsed = time.time() - t0
    return {
        "slug": slug,
        "model_id": model_id,
        "returncode": proc.returncode,
        "wall_time_wrapper_seconds": elapsed,
        "stdout_tail": proc.stdout[-3000:],
        "stderr_tail": proc.stderr[-3000:],
        "success": proc.returncode == 0,
        "out_path": out_path,
    }


def main():
    log = []
    for m in MODELS:
        entry = run_one(m["slug"], m["model_id"], m["quantization"], m["dtype"], m["gpu_mem_util"])
        log.append(entry)
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)

        if entry["success"]:
            print(f"OK ({entry['wall_time_wrapper_seconds']:.1f}s). See {entry['out_path']}")
        else:
            print(f"FAILED (exit {entry['returncode']}) after {entry['wall_time_wrapper_seconds']:.1f}s.")
            print("--- stderr tail ---")
            print(entry["stderr_tail"])
            if "fallback_slug" in m:
                print(f"Falling back to {m['fallback_model_id']}...")
                fb = run_one(m["fallback_slug"], m["fallback_model_id"], m["fallback_quantization"],
                             m["fallback_dtype"], m["gpu_mem_util"])
                fb["fallback_for"] = m["slug"]
                log.append(fb)
                with open(LOG_PATH, "w", encoding="utf-8") as f:
                    json.dump(log, f, indent=2, ensure_ascii=False)
                if fb["success"]:
                    print(f"Fallback OK ({fb['wall_time_wrapper_seconds']:.1f}s). See {fb['out_path']}")
                else:
                    print(f"Fallback ALSO FAILED (exit {fb['returncode']}).")
                    print(fb["stderr_tail"])

    print("=" * 80)
    print("All models attempted. Summary:")
    for e in log:
        status = "OK" if e["success"] else "FAILED/SKIPPED"
        tag = f" (fallback for {e['fallback_for']})" if "fallback_for" in e else ""
        print(f"  {e['slug']}{tag}: {status} ({e['wall_time_wrapper_seconds']:.1f}s)")


if __name__ == "__main__":
    main()
