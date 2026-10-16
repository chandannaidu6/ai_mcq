# Pilot results: Can AI models answer AI-generated MCQs about real student code?

## Hardware & runtime

- GPU: **NVIDIA RTX 4000 Ada Generation, 20475 MiB (~20 GB) VRAM**, driver CUDA 13.0

- Python 3.10.12, vLLM 0.31.0, PyTorch 2.13.0+cu130


| Model | Loaded? | Load time (s) | Generation time for 100 Q (s) | Total wall time (s) |
|---|---|---|---|---|
| Qwen2.5-Coder-3B-Instruct | yes | 23.2 | 1.3 | 24.4 |
| Qwen2.5-Coder-7B-Instruct-AWQ | yes | 26.5 | 3.1 | 29.5 |
| Qwen2.5-Coder-14B-Instruct-AWQ | yes | 54.0 | 6.0 | 60.0 |
| DeepSeek-Coder-6.7B-Instruct | yes | 45.0 | 4.0 | 49.0 |

## Dataset

- Source: *Dataset of Student Solutions to Algorithm and Data Structure Programming Assignments* (Petersen-Frey et al., LREC 2022, Universität Hamburg), Python solutions only.

- **25 student solutions** sampled (seed=42), spanning **21 distinct tasks** (21 of the 21 available Python tasks in the dataset were covered).

- **100 questions** generated (4 per solution x 25 solutions), split evenly across the 4 categories (25 each): output, variable_state, loop_trace, control_flow.


## Answer-key verification (Step 3)

- **100/100 (100.0%)** of generated questions had a verifiable execution ground truth (student code + verification snippet ran successfully and printed a value matching one of the 4 options).

- **2/100 (2.0%)** of the generator's (Claude's) own hand-written answer keys were WRONG when checked against execution -- i.e. the generator picked the wrong option as "correct" when first writing the question, one pass, no self-checking, by design (matching the AutoMCQ-style protocol). This was left uncorrected per the pilot's rules; accuracy below is scored against the execution ground truth, not the original answer key.

  - Example: `s05_q0` (output, task 20_21-3-1-python): generator's answer key was **B**, but execution showed the true answer is **A** (code printed `220`).

  - Example: `s15_q2` (loop_trace, task 21_22-1-2-python): generator's answer key was **A**, but execution showed the true answer is **C** (code printed `61`).


### Ground-truth verifiability by category

| Category | Questions | With verifiable ground truth |
|---|---|---|
| output | 25 | 25 (100%) |
| variable_state | 25 | 25 (100%) |
| loop_trace | 25 | 25 (100%) |
| control_flow | 25 | 25 (100%) |

## Model accuracy (Step 4, scored against execution ground truth)

| Model | Valid answers | Overall accuracy |
|---|---|---|
| Qwen2.5-Coder-3B-Instruct | 100/100 | 49.0% |
| Qwen2.5-Coder-7B-Instruct-AWQ | 100/100 | 62.0% |
| Qwen2.5-Coder-14B-Instruct-AWQ | 100/100 | 73.0% |
| DeepSeek-Coder-6.7B-Instruct | 92/100 | 26.0% |

### Accuracy per category per model

| Category | Qwen2.5-Coder-3B-Instruct | Qwen2.5-Coder-7B-Instruct-AWQ | Qwen2.5-Coder-14B-Instruct-AWQ | DeepSeek-Coder-6.7B-Instruct |
|---|---|---|---|---|
| output | 40.0% | 64.0% | 68.0% | 28.0% |
| variable_state | 32.0% | 52.0% | 72.0% | 8.0% |
| loop_trace | 36.0% | 40.0% | 52.0% | 24.0% |
| control_flow | 88.0% | 92.0% | 100.0% | 44.0% |

**Hardest category (lowest average accuracy across models): `loop_trace`** (38.0% avg)

**Easiest category (highest average accuracy across models): `control_flow`** (81.0% avg)


**Model size trend:** accuracy increased monotonically with model size within the Qwen2.5-Coder family (Qwen2.5-Coder-3B-Instruct=49.0%, Qwen2.5-Coder-7B-Instruct-AWQ=62.0%, Qwen2.5-Coder-14B-Instruct-AWQ=73.0%).


## Example questions the models got wrong

### `s00_q0` (output, task `21_22-3-1-python`) -- wrong for 4/4 models

**Question:** Given `opt([3, 2, 5, 10, 7])`, what value does the function return?

```python
def opt(W):
    if len(W) < 2:
        return W[0]
    
    a = W[0]
    b = max(W[0],W[1])
    for i in range(2,len(W)):
        c = max(W[i]+a, b)
        a = b
        b = c
            
    return b
```
- A) 13
- B) 17
- C) 15 <- correct (execution ground truth)
- D) 12

Model answers: Qwen2.5-Coder-3B-Instruct=A, Qwen2.5-Coder-7B-Instruct-AWQ=B, Qwen2.5-Coder-14B-Instruct-AWQ=B, DeepSeek-Coder-6.7B-Instruct=B

### `s00_q2` (loop_trace, task `21_22-3-1-python`) -- wrong for 4/4 models

**Question:** How many times does the loop body line `c = max(W[i]+a, b)` execute when calling `opt([3, 2, 5, 10, 7])`?

```python
def opt(W):
    if len(W) < 2:
        return W[0]
    
    a = W[0]
    b = max(W[0],W[1])
    for i in range(2,len(W)):
        c = max(W[i]+a, b)
        a = b
        b = c
            
    return b
```
- A) 2
- B) 3 <- correct (execution ground truth)
- C) 4
- D) 5

Model answers: Qwen2.5-Coder-3B-Instruct=C, Qwen2.5-Coder-7B-Instruct-AWQ=D, Qwen2.5-Coder-14B-Instruct-AWQ=C, DeepSeek-Coder-6.7B-Instruct=C

### `s02_q1` (variable_state, task `20_21-3-2-python`) -- wrong for 4/4 models

**Question:** Trace `calc(4, [[1, 2], [2, 3], [1, 3], [3, 4]])`. What is the value of the `Lengths` list right after the outer loop has fully processed `e=1` (i.e. at the start of the `e=2` iteration of `for e in range(len(Connections))`)?

```python
def calc(N,A):
    Lengths = []
    Connections = []

    for i in range(N):
        Lengths += [0]
        Connections += [[]]

    for e in A:
        assert e[0] < e[1]
        Connections[e[0]-1] += [e[1]-1]

    for e in range(len(Connections)):
        for u in Connections[e]:
            Lengths[u] = max(Lengths[e] + 1, Lengths[u])

    return max(Lengths)
```
- A) [0, 1, 2, 3]
- B) [0, 1, 1, 0]
- C) [1, 1, 2, 0]
- D) [0, 1, 2, 0] <- correct (execution ground truth)

Model answers: Qwen2.5-Coder-3B-Instruct=A, Qwen2.5-Coder-7B-Instruct-AWQ=A, Qwen2.5-Coder-14B-Instruct-AWQ=C, DeepSeek-Coder-6.7B-Instruct=B

## Draft abstract sentences (real numbers only)

> In a pilot of 100 AI-generated multiple-choice comprehension questions (100 with execution-verified ground truth, 100%) about 25 real student Python solutions to 21 distinct algorithms/data-structures assignments, open-source code models (Qwen2.5-Coder-3B-Instruct, Qwen2.5-Coder-7B-Instruct-AWQ, Qwen2.5-Coder-14B-Instruct-AWQ, DeepSeek-Coder-6.7B-Instruct, 4 model(s), 3B-14B parameters) run locally on a single NVIDIA RTX 4000 Ada (20GB) answered 26-73% of verifiable questions correctly.

> Questions about **loop trace** were hardest (38% average accuracy) and questions about **control flow** were easiest (81% average accuracy) across models.

> Qwen2.5-Coder-14B-Instruct-AWQ achieved the highest overall accuracy at 73%; the pilot's own one-pass question generator produced 2 incorrect answer key(s) out of 100 verifiable questions (2%), itself a finding about automated MCQ generation.
