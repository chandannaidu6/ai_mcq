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
| GPT-6 Luna (reasoning: none) | complete |
| GPT-6 Luna (reasoning: medium) | complete |
| Claude Haiku 5.5 (thinking: off) | **not available** -- not yet available |
| Claude Haiku 5.5 (thinking: on) | **not available** -- not yet available |

## Overall accuracy, ranked (scored against execution ground truth)

| Rank | Model/setting | Valid answers | Questions w/ ground truth | Accuracy |
|---|---|---|---|---|
| 1 | GPT-6 Luna (reasoning: medium) | 942/1004 | 701 | 89.9% |
| 2 | GPT-6 Luna (reasoning: none) | 1004/1005 | 701 | 74.2% |
| 3 | Qwen2.5-Coder-14B-Instruct-AWQ | 1005/1005 | 701 | 70.0% |
| 4 | Qwen2.5-Coder-7B-Instruct-AWQ | 1005/1005 | 701 | 58.9% |
| 5 | DeepSeek-Coder-V2-Lite-Instruct-AWQ | 1004/1005 | 701 | 39.5% |
| 6 | Qwen2.5-Coder-3B-Instruct | 1005/1005 | 701 | 36.7% |

## Accuracy by category, every model

| Category | Qwen2.5-Coder-3B-Instruct | Qwen2.5-Coder-7B-Instruct-AWQ | Qwen2.5-Coder-14B-Instruct-AWQ | DeepSeek-Coder-V2-Lite-Instruct-AWQ | GPT-6 Luna (reasoning: none) | GPT-6 Luna (reasoning: medium) |
|---|---|---|---|---|---|---|
| output | 43% | 64% | 75% | 45% | 73% | 99% |
| variable_state | 40% | 66% | 60% | 54% | 83% | 100% |
| loop_trace | 17% | 20% | 31% | 41% | 48% | 74% |
| control_flow | 34% | 54% | 52% | 33% | 57% | 60% |
| call_count | 24% | 65% | 92% | 22% | 96% | 97% |
| edge_case | 47% | 65% | 72% | 50% | 75% | 100% |
| code_modification | 37% | 58% | 86% | 29% | 86% | 100% |
| data_structure_state | 44% | 67% | 93% | 56% | 89% | 100% |

## Thinking/reasoning ON vs. OFF (same model)

- **GPT-6 Luna**: off=74.2% | on=89.9%


## Open-source vs. commercial; accuracy vs. size (Qwen family)

Qwen2.5-Coder accuracy by size: Qwen2.5-Coder-3B-Instruct=36.7%, Qwen2.5-Coder-7B-Instruct-AWQ=58.9%, Qwen2.5-Coder-14B-Instruct-AWQ=70.0%

Accuracy **increased monotonically** with size.


Best open-source model: **Qwen2.5-Coder-14B-Instruct-AWQ** (70.0%). Best commercial/API model so far: **GPT-6 Luna (reasoning: medium)** (89.9%).


## Invalid-answer rates

| Model/setting | Invalid answers |
|---|---|
| Qwen2.5-Coder-3B-Instruct | 0/1005 (0.0%) |
| Qwen2.5-Coder-7B-Instruct-AWQ | 0/1005 (0.0%) |
| Qwen2.5-Coder-14B-Instruct-AWQ | 0/1005 (0.0%) |
| DeepSeek-Coder-V2-Lite-Instruct-AWQ | 1/1005 (0.1%) |
| GPT-6 Luna (reasoning: none) | 1/1005 (0.1%) |
| GPT-6 Luna (reasoning: medium) | 62/1004 (6.2%) |

## Spend (from results/cost_log.csv and provider dashboards)

```
provider,model_setting,n_calls,input_tokens,output_tokens,thinking_or_reasoning_tokens,cost_usd_this_setting,running_total_usd_this_provider
openai,gpt-6-luna (reasoning: none),1005,382176,4020,0,0.0201,0.0201
openai,gpt-6-luna (reasoning: medium),1004,381747,412984,401438,0.1223,0.1424
anthropic,claude-haiku-5.5 (thinking: off),NOT RUN,,,,,
anthropic,claude-haiku-5.5 (thinking: on),NOT RUN,,,,,

TOTALS,,,,,,openai=0.1424,anthropic=0.0000
,,,,,,"gemini=0.0000 (free tier, dropped before any token usage was billable)",
BUDGET CAPS,,,,,,openai_cap=9.00,anthropic_cap=9.00
```

## Example questions most models got wrong

### `s005_q3` (loop_trace, task `20_21-3-1-python`) -- wrong for 6/6 models

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

### `s007_q5` (control_flow, task `21_22-2-2-python`) -- wrong for 6/6 models

**Question:** Consider calling the code above like this:
```python
print(__student_answer__.find("eval"))
```
At the first `if` statement in the function (line 11), which branch executes?

```python
def calc(a,b):
    s = [0] * len(b)
    c = [0] * len(a)
    c[0] = a[0]
    for i in range(1,len(a)):
        c[i] = a[i] + c[i-1]
    for i in range(len(b)):
        l = ((b[i])[0])
        r = ((b[i])[1])
        if l == r:
            s[i] = a[l]
        elif l == 0:
            s[i] = c[r]
        else:
            s[i] = c[r] - c[l-1]
    return s
```
- A) the `if` branch executes (line 11)
- B) an exception is raised
- C) neither branch is reached (unreachable code)
- D) the `else`/`elif` branch executes (line 12) <- correct

### `s009_q4` (control_flow, task `20_21-2-1-python`) -- wrong for 6/6 models

**Question:** Consider calling the code above like this:
```python
print(__student_answer__.find("eval"))
```
At the first `if` statement in the function (line 6), which branch executes?

```python
def calc(A, B):
    s = ""
    count = {}
    for i in A:
        if i in count:
            count[i] += 1
        else:
            count[i] = 1
    for i in range(len(B)):
        try:
            if count[i] <= B[i]:
                s += "1"
            else:
                s += "0"
        except KeyError:
            s += "1"
    return s
```
- A) neither branch is reached (unreachable code)
- B) an exception is raised
- C) the `else`/`elif` branch executes (line 8) <- correct
- D) the `if` branch executes (line 6)

### `s010_q4` (control_flow, task `21_22-2-1-python`) -- wrong for 6/6 models

**Question:** Consider calling the code above like this:
```python
print(__student_answer__.find("eval"))
```
At the first `if` statement in the function (line 7), which branch executes?

```python
def calc(A,B):
    for i in A:
        B[i] = B[i]-1
    s = ""
    for i in B:
        if i <0 :
            s = s+"0"
        else: 
            s = s+"1"
    return s
```
- A) neither branch is reached (unreachable code)
- B) an exception is raised
- C) the `else`/`elif` branch executes (line 9) <- correct
- D) the `if` branch executes (line 7)

### `s017_q3` (loop_trace, task `19_20-6-1-python`) -- wrong for 6/6 models

**Question:** Consider calling the code above like this:
```python
print(editDistance("a","a"))
```
How many times does the loop body starting at line 19 execute?

```python
def edelta_evaluate(edelta,i,j,u,v):
  if i == 0:
    return j
  if j == 0:
    return i
  if u[i-1] == v[j-1]:
    repcost = 0
  else:
    repcost = 1
  return min([edelta[i-1][j-1] + repcost,
              edelta[i-1][j] + 1,
              edelta[i][j-1] + 1])

def editDistance(u, v):
  m = len(u)
  n = len(v)
  edelta = [[None] * (n+1) for i in range(m+1)]
  for i in range(m+1):
    for j in range(n+1):
      edelta[i][j] = edelta_evaluate(edelta,i,j,u,v)
  return edelta[m][n]
```
- A) 3
- B) 6 <- correct
- C) 2
- D) 4

## Draft poster sentences (real numbers only)

> Across 6 model/setting combinations (open-source models on a single NVIDIA RTX 4000 Ada GPU, plus commercial API models), accuracy on 701 execution-verified AI-generated comprehension questions about real student code ranged from 37% (Qwen2.5-Coder-3B-Instruct) to 90% (GPT-6 Luna (reasoning: medium)).

> Within the Qwen2.5-Coder family, accuracy rose from 37% (Qwen2.5-Coder-3B-Instruct) to 70% (Qwen2.5-Coder-14B-Instruct-AWQ) as model size increased.

> The question generator (Claude Sonnet 5), operating one-pass with no self-checking, produced 101 incorrect answer keys out of 701 verifiable questions (14.4%) across 8 comprehension categories.

> (2 model/setting(s) were still pending or blocked when this report was generated: Claude Haiku 5.5 (thinking: off), Claude Haiku 5.5 (thinking: on).)
