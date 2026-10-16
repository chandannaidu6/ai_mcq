"""
Step 1: Load the AD2022 dataset CSVs, filter to Python solutions that don't
need external files or input(), and randomly sample N solutions (seed=42,
fixed regardless of N so a larger N is a strict superset of a smaller one),
spread across as many distinct tasks as possible (round-robin over tasks).

Usage: 01_sample_solutions.py [data_dir] [out_path] [N]
Defaults (N=25) reproduce the original pilot's sample exactly.
"""
import csv
import json
import random
import sys
import os

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else "/s/chopin/b/grad/C837792936/ai-mcq-pilot/data_extracted/AD2022dataset"
OUT_PATH = sys.argv[2] if len(sys.argv) > 2 else "/s/chopin/b/grad/C837792936/ai-mcq-pilot/pilot_data/sampled_solutions.json"
N = int(sys.argv[3]) if len(sys.argv) > 3 else 25

SOL_FILES = ["19_20_solutions.csv", "20_21_solutions.csv", "21_22_solutions.csv"]
TASK_FILES = ["19_20_task_descriptions.csv", "20_21_task_descriptions.csv", "21_22_task_descriptions.csv"]

def load_tasks():
    tasks = {}
    for fn in TASK_FILES:
        path = os.path.join(DATA_DIR, fn)
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tasks[row["id"]] = row
    return tasks

def load_solutions():
    sols = []
    for fn in SOL_FILES:
        path = os.path.join(DATA_DIR, fn)
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["question_id"].endswith("-python"):
                    row["_source_file"] = fn
                    sols.append(row)
    return sols

def main():
    tasks = load_tasks()
    solutions = load_solutions()

    filtered = []
    skipped_input_open = 0
    for row in solutions:
        sol = row["solution"]
        if "input(" in sol or "open(" in sol:
            skipped_input_open += 1
            continue
        filtered.append(row)

    print(f"Total python solutions: {len(solutions)}")
    print(f"Skipped (input()/open()): {skipped_input_open}")
    print(f"Eligible solutions: {len(filtered)}")

    by_task = {}
    for row in filtered:
        by_task.setdefault(row["question_id"], []).append(row)

    print(f"Distinct eligible tasks: {len(by_task)}")

    rng = random.Random(42)
    # Shuffle task order, and shuffle solutions within each task
    task_ids = list(by_task.keys())
    rng.shuffle(task_ids)
    for tid in task_ids:
        rng.shuffle(by_task[tid])

    # Round-robin across tasks to maximize task coverage in the sample
    sample = []
    idx_per_task = {tid: 0 for tid in task_ids}
    while len(sample) < N:
        progressed = False
        for tid in task_ids:
            if len(sample) >= N:
                break
            i = idx_per_task[tid]
            if i < len(by_task[tid]):
                sample.append(by_task[tid][i])
                idx_per_task[tid] += 1
                progressed = True
        if not progressed:
            break  # exhausted all solutions (shouldn't happen, 687 eligible)

    print(f"Sampled: {len(sample)} solutions across {len(set(r['question_id'] for r in sample))} tasks")

    out = []
    for row in sample:
        qid = row["question_id"]
        task = tasks.get(qid, {})
        out.append({
            "question_id": qid,
            "student_id": row["student_id"],
            "source_file": row["_source_file"],
            "solution_code": row["solution"],
            "title_eng": task.get("title_eng", ""),
            "task_description_plain_eng": task.get("task_description_plain_eng", ""),
            "skeleton": task.get("skeleton", ""),
        })

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(out)} sampled solutions to {OUT_PATH}")
    task_counts = {}
    for r in out:
        task_counts[r["question_id"]] = task_counts.get(r["question_id"], 0) + 1
    print("Per-task counts:", task_counts)

if __name__ == "__main__":
    main()
