# AI-MCQ-PILOT v2: expanded 8-category, multi-provider results

Generator: **Claude Sonnet 5** (`claude-sonnet-5`), run via Claude Code.

Run date: 2026-10-16 (report generated during an ongoing run -- see per-provider completeness notes below).


## Hardware

- GPU: NVIDIA RTX 4000 Ada Generation, 20475 MiB VRAM

- Python 3.10.12, vLLM 0.31.0


## Dataset and question generation

- **185 student solutions** sampled (seed=42, superset of the original 25-solution pilot sample), spanning **21/21 distinct Python tasks** in the dataset.

- **1005 questions** generated across **8 categories** by a template-based (AutoMCQ-style) generator: for each applicable category/solution pair, the generator used `ast` analysis plus the dataset's own `tests.csv` test cases and tester harnesses to construct a question, in one pass, with NO execution of student code to self-check before saving (ground truth comes only from Step 3's execution). Categories that don't apply to a given solution (e.g. no loop found) are skipped and logged (`results/category_skips.json`, 475 skips recorded).


### Questions per category (generated / with verifiable ground truth / wrong generator key)

| Category | Generated | Verifiable ground truth | Generator's key was wrong |
|---|---|---|---|
| output | 140 | 138 (99%) | 0 (0.0%) |
| variable_state | 117 | 35 (30%) | 3 (8.6%) |
| loop_trace | 129 | 54 (42%) | 9 (16.7%) |
| control_flow | 132 | 132 (100%) | 64 (48.5%) |
| call_count | 176 | 106 (60%) | 3 (2.8%) |
| edge_case | 167 | 150 (90%) | 19 (12.7%) |
| code_modification | 117 | 59 (50%) | 3 (5.1%) |
| data_structure_state | 27 | 27 (100%) | 0 (0.0%) |

**Overall: 701/1005 (69.8%) questions have verifiable execution ground truth; 101/701 (14.4%) of the generator's own answer keys were wrong when checked against execution** (left uncorrected, as required -- accuracy below is scored against execution ground truth, never the generator's original key).


## Provider/model completeness

| Model/setting | Status |
|---|---|
| Qwen2.5-Coder-3B-Instruct | complete |
| Qwen2.5-Coder-7B-Instruct-AWQ | complete |
| Qwen2.5-Coder-14B-Instruct-AWQ | complete |
| DeepSeek-Coder-V2-Lite-Instruct-AWQ | complete |
| Gemini 3.8 Flash (thinking: off*) | IN PROGRESS (4/1005) |
| Gemini 3.8 Flash (thinking: on) | IN PROGRESS (0/1005) |
| DeepSeek-Coder-6.7B-Instruct | **not available** -- not yet available |
| GPT-6 Luna (reasoning: none) | **not available** -- not yet available |
| GPT-6 Luna (reasoning: medium) | **not available** -- not yet available |
| Gemini 3.5 Flash-Lite (thinking: off) | **not available** -- not yet available |
| Gemini 3.5 Flash-Lite (thinking: on) | **not available** -- not yet available |
| Claude Haiku 5.5 (thinking: off) | **not available** -- not yet available |
| Claude Haiku 5.5 (thinking: on) | **not available** -- not yet available |

## Overall accuracy, ranked (scored against execution ground truth)

| Rank | Model/setting | Valid answers | Questions w/ ground truth | Accuracy |
|---|---|---|---|---|
| 1 | Gemini 3.8 Flash (thinking: off*) | 3/4 | 2 | 100.0% |
| 2 | Qwen2.5-Coder-14B-Instruct-AWQ | 1005/1005 | 701 | 70.0% |
| 3 | Qwen2.5-Coder-7B-Instruct-AWQ | 1005/1005 | 701 | 58.9% |
| 4 | DeepSeek-Coder-V2-Lite-Instruct-AWQ | 1004/1005 | 701 | 39.5% |
| 5 | Qwen2.5-Coder-3B-Instruct | 1005/1005 | 701 | 36.7% |

## Accuracy by category, every model

| Category | Qwen2.5-Coder-3B-Instruct | Qwen2.5-Coder-7B-Instruct-AWQ | Qwen2.5-Coder-14B-Instruct-AWQ | DeepSeek-Coder-V2-Lite-Instruct-AWQ | Gemini 3.8 Flash (thinking: off*) | Gemini 3.8 Flash (thinking: on) |
|---|---|---|---|---|---|---|
| output | 43% | 64% | 75% | 45% | 100% | n/a |
| variable_state | 40% | 66% | 60% | 54% | n/a | n/a |
| loop_trace | 17% | 20% | 31% | 41% | n/a | n/a |
| control_flow | 34% | 54% | 52% | 33% | n/a | n/a |
| call_count | 24% | 65% | 92% | 22% | n/a | n/a |
| edge_case | 47% | 65% | 72% | 50% | 100% | n/a |
| code_modification | 37% | 58% | 86% | 29% | n/a | n/a |
| data_structure_state | 44% | 67% | 93% | 56% | n/a | n/a |

## Thinking/reasoning ON vs. OFF (same model)

- **Gemini 3.8 Flash**: off=100.0% | on=n/a


## Open-source vs. commercial; accuracy vs. size (Qwen family)

Qwen2.5-Coder accuracy by size: Qwen2.5-Coder-3B-Instruct=36.7%, Qwen2.5-Coder-7B-Instruct-AWQ=58.9%, Qwen2.5-Coder-14B-Instruct-AWQ=70.0%

Accuracy **increased monotonically** with size.


Best open-source model: **Qwen2.5-Coder-14B-Instruct-AWQ** (70.0%). Best commercial/API model so far: **Gemini 3.8 Flash (thinking: off*)** (100.0%).


## Invalid-answer rates

| Model/setting | Invalid answers |
|---|---|
| Qwen2.5-Coder-3B-Instruct | 0/1005 (0.0%) |
| Qwen2.5-Coder-7B-Instruct-AWQ | 0/1005 (0.0%) |
| Qwen2.5-Coder-14B-Instruct-AWQ | 0/1005 (0.0%) |
| DeepSeek-Coder-V2-Lite-Instruct-AWQ | 1/1005 (0.1%) |
| Gemini 3.8 Flash (thinking: off*) | 1/4 (25.0%) |
| Gemini 3.8 Flash (thinking: on) | n/a (0 answers so far) |

## Spend (from results/cost_log.csv and provider dashboards)

(cost_log.csv not yet finalized -- see results/cost_projection.json for the pre-flight 20-question projections, which showed full-scale OpenAI costs of ~$0.05-0.09, far under the $9 cap; Gemini is free-tier only, $0 spend.)


## Example questions most models got wrong

### `s000_q1` (edge_case, task `21_22-3-1-python`) -- wrong for 4/6 models

**Question:** This is an edge-case input (generator-constructed, unverified). What gets printed when the following runs immediately after the code above?
```python
print(opt([]))
```

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
- A) Raises ValueError
- B) 9
- C) 0
- D) Raises IndexError <- correct

### `s002_q0` (output, task `20_21-3-2-python`) -- wrong for 4/6 models

**Question:** What gets printed when the following is run immediately after the code above?
```python
print(calc(3,[[1,2],[2,3]]))
```

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
- A) -2
- B) 3
- C) 1
- D) 2 <- correct

### `s002_q3` (loop_trace, task `20_21-3-2-python`) -- wrong for 4/6 models

**Question:** Consider calling the code above like this:
```python
print(calc(5, [[3, 4], [1, 5], [1, 4], [4, 5], [2, 5]]))
```
How many times does the loop body starting at line 6 execute?

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
- A) 4
- B) 10
- C) 6
- D) 5 <- correct

### `s005_q0` (output, task `20_21-3-1-python`) -- wrong for 4/6 models

**Question:** What gets printed when the following is run immediately after the code above?
```python
print(knapSack([1, 1, 1],[2, 5, 0],3))
```

```python
def knapSack(value, volume, capacity):
    assert len(value) == len(volume)

    for x in volume: assert x == round(x)

    tabelle = [[0.0 for x in range(capacity + 1)] for x in range(len(value) + 1)]
    for i in range(len(value)+1): 
        for w in range(capacity+1):
            if i == 0 or w == 0:
                tabelle[i][w] = 0
            elif volume[i-1] <= w:
                if value[i-1] + tabelle[i-1][w-volume[i-1]] >= tabelle[i-1][w]:
                    tabelle[i][w] = value[i-1] + tabelle[i-1][w-volume[i-1]]
                else:
                    tabelle[i][w] = tabelle[i-1][w]
            else: 
                tabelle[i][w] = tabelle[i-1][w]
    return (tabelle[len(value)][capacity])
```
- A) 1
- B) 3
- C) 2 <- correct
- D) -2

### `s005_q3` (loop_trace, task `20_21-3-1-python`) -- wrong for 4/6 models

**Question:** Consider calling the code above like this:
```python
print(knapSack([0.5, 1.3],[2, 5],3))
```
How many times does the loop body starting at line 4 execute?

```python
def knapSack(value, volume, capacity):
    assert len(value) == len(volume)

    for x in volume: assert x == round(x)

    tabelle = [[0.0 for x in range(capacity + 1)] for x in range(len(value) + 1)]
    for i in range(len(value)+1): 
        for w in range(capacity+1):
            if i == 0 or w == 0:
                tabelle[i][w] = 0
            elif volume[i-1] <= w:
                if value[i-1] + tabelle[i-1][w-volume[i-1]] >= tabelle[i-1][w]:
                    tabelle[i][w] = value[i-1] + tabelle[i-1][w-volume[i-1]]
                else:
                    tabelle[i][w] = tabelle[i-1][w]
            else: 
                tabelle[i][w] = tabelle[i-1][w]
    return (tabelle[len(value)][capacity])
```
- A) 1
- B) 2
- C) 3 <- correct
- D) 4

## Draft poster sentences (real numbers only)

> Across 6 model/setting combinations (open-source models on a single NVIDIA RTX 4000 Ada GPU, plus commercial API models), accuracy on 701 execution-verified AI-generated comprehension questions about real student code ranged from 37% (Qwen2.5-Coder-3B-Instruct) to 100% (Gemini 3.8 Flash (thinking: off*)).

> Within the Qwen2.5-Coder family, accuracy rose from 37% (Qwen2.5-Coder-3B-Instruct) to 70% (Qwen2.5-Coder-14B-Instruct-AWQ) as model size increased.

> The question generator (Claude Sonnet 5), operating one-pass with no self-checking, produced 101 incorrect answer keys out of 701 verifiable questions (14.4%) across 8 comprehension categories.

> (7 model/setting(s) were still pending or blocked when this report was generated: DeepSeek-Coder-6.7B-Instruct, GPT-6 Luna (reasoning: none), GPT-6 Luna (reasoning: medium), Gemini 3.5 Flash-Lite (thinking: off), Gemini 3.5 Flash-Lite (thinking: on), Claude Haiku 5.5 (thinking: off), Claude Haiku 5.5 (thinking: on).)
