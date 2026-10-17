# AI-MCQ-PILOT v2: expanded 8-category, multi-provider results

Generator: **Claude Sonnet 5** (`claude-sonnet-5`), run via Claude Code.

Run date: 2026-10-16 (all providers complete.)


## Hardware

- GPU: NVIDIA RTX 4000 Ada Generation, 20475 MiB VRAM

- Python 3.10.12, vLLM 0.31.0


## Dataset and question generation

- **185 student solutions** sampled (seed=42, superset of the original 25-solution pilot sample), spanning **21/21 distinct Python tasks** in the dataset.

- **996 questions** generated across **8 categories** by a template-based (AutoMCQ-style) generator: for each applicable category/solution pair, the generator used `ast` analysis plus the dataset's own `tests.csv` test cases and tester harnesses to construct a question, in one pass, with NO execution of student code to self-check before saving (ground truth comes only from Step 3's execution). Categories that don't apply to a given solution (e.g. no loop found) are skipped and logged (`results/category_skips.json`, 484 skips recorded).


### Questions per category (generated / with verifiable ground truth / wrong generator key)

| Category | Generated | Verifiable ground truth | Generator's key was wrong |
|---|---|---|---|
| output | 140 | 140 (100%) | 0 (0.0%) |
| variable_state | 117 | 62 (53%) | 4 (6.5%) |
| loop_trace | 129 | 80 (62%) | 16 (20.0%) |
| control_flow | 132 | 132 (100%) | 78 (59.1%) |
| call_count | 176 | 150 (85%) | 7 (4.7%) |
| edge_case | 158 | 123 (78%) | 19 (15.4%) |
| code_modification | 117 | 45 (38%) | 22 (48.9%) |
| data_structure_state | 27 | 27 (100%) | 0 (0.0%) |

**Overall: 759/996 (76.2%) questions have verifiable execution ground truth; 146/759 (19.2%) of the generator's own answer keys were wrong when checked against execution** (left uncorrected, as required -- accuracy below is scored against execution ground truth, never the generator's original key).


## Provider/model completeness

| Model/setting | Status |
|---|---|
| GPT-6 Luna (reasoning: none) | complete |
| GPT-6 Luna (reasoning: medium) | complete |
| GPT-6 Astra (reasoning: low) | complete |
| Claude Haiku 5.5 (thinking: off) | complete |
| Claude Haiku 5.5 (thinking: on) | complete |
| Claude Opus 5 (thinking: off) | complete |
| Claude Opus 5 (thinking: on) | complete |

## Overall accuracy, ranked (scored against execution ground truth)

| Rank | Model/setting | Valid answers | Questions w/ ground truth | Accuracy |
|---|---|---|---|---|
| 1 | GPT-6 Astra (reasoning: low) | 932/996 | 759 | 94.9% |
| 2 | Claude Haiku 5.5 (thinking: on) | 959/996 | 759 | 94.1% |
| 3 | GPT-6 Luna (reasoning: medium) | 956/995 | 759 | 93.0% |
| 4 | GPT-6 Luna (reasoning: none) | 994/996 | 759 | 79.1% |
| 5 | Claude Opus 5 (thinking: on) | 634/996 | 759 | 60.6% |
| 6 | Claude Haiku 5.5 (thinking: off) | 806/996 | 759 | 58.5% |
| 7 | Claude Opus 5 (thinking: off) | 601/996 | 759 | 58.1% |

## Accuracy by category, every model

| Category | GPT-6 Luna (reasoning: none) | GPT-6 Luna (reasoning: medium) | GPT-6 Astra (reasoning: low) | Claude Haiku 5.5 (thinking: off) | Claude Haiku 5.5 (thinking: on) | Claude Opus 5 (thinking: off) | Claude Opus 5 (thinking: on) |
|---|---|---|---|---|---|---|---|
| output | 71% | 100% | 100% | 46% | 99% | 60% | 64% |
| variable_state | 81% | 97% | 100% | 34% | 97% | 42% | 52% |
| loop_trace | 56% | 79% | 91% | 42% | 88% | 52% | 58% |
| control_flow | 73% | 81% | 81% | 56% | 82% | 48% | 53% |
| call_count | 95% | 95% | 95% | 93% | 95% | 75% | 75% |
| edge_case | 89% | 99% | 100% | 60% | 99% | 63% | 62% |
| code_modification | 76% | 100% | 100% | 53% | 100% | 29% | 24% |
| data_structure_state | 81% | 100% | 100% | 44% | 100% | 85% | 85% |

## Thinking/reasoning ON vs. OFF (same model)

- **GPT-6 Luna**: off=79.1% | on=93.0%

- **Claude Haiku 5.5**: off=58.5% | on=94.1%


## Provider / family comparison

- **GPT-6**: GPT-6 Luna (reasoning: none)=79.1%, GPT-6 Luna (reasoning: medium)=93.0%, GPT-6 Astra (reasoning: low)=94.9%

- **Claude Haiku**: Claude Haiku 5.5 (thinking: off)=58.5%, Claude Haiku 5.5 (thinking: on)=94.1%

- **Claude Opus**: Claude Opus 5 (thinking: off)=58.1%, Claude Opus 5 (thinking: on)=60.6%


Best overall: **GPT-6 Astra (reasoning: low)** (94.9%). Lowest: **Claude Opus 5 (thinking: off)** (58.1%).


**Caveat:** Claude Haiku is in the same model family as the question generator (Claude Sonnet 5). It may have an advantage the other answering models don't have (e.g. shared conventions in how Anthropic models phrase/parse this kind of question), so its ranking above should be read with that in mind, not as a clean apples-to-apples result.


## Invalid-answer rates

| Model/setting | Invalid answers |
|---|---|
| GPT-6 Luna (reasoning: none) | 2/996 (0.2%) |
| GPT-6 Luna (reasoning: medium) | 39/995 (3.9%) |
| GPT-6 Astra (reasoning: low) | 64/996 (6.4%) |
| Claude Haiku 5.5 (thinking: off) | 190/996 (19.1%) |
| Claude Haiku 5.5 (thinking: on) | 37/996 (3.7%) |
| Claude Opus 5 (thinking: off) | 395/996 (39.7%) |
| Claude Opus 5 (thinking: on) | 362/996 (36.3%) |

## Spend (from results/cost_log.csv and provider dashboards)

```
provider,model_setting,n_calls,input_tokens,output_tokens,thinking_or_reasoning_tokens,cost_usd_this_setting,running_total_usd_this_provider
openai,gpt-6-luna (reasoning: none),996,381332,3984,0,0.0201,0.0201
openai,gpt-6-luna (reasoning: medium),995,380903,281745,270781,0.0895,0.1095
openai,gpt-6-astra (reasoning: low),996,381332,22889,16310,2.4789,2.5884
anthropic,claude-haiku-5.5 (thinking: off),996,513971,103689,0,0.0516,0.0516
anthropic,claude-haiku-5.5 (thinking: on),996,515963,411288,408001,0.1286,0.1802
anthropic,claude-opus-5 (thinking: off),996,513971,21225,0,1.5502,1.7305
anthropic,claude-opus-5 (thinking: on),996,513971,93996,92094,2.4599,4.1904

TOTALS,,,,,,openai=2.5884,anthropic=4.1904
,,,,,,"gemini=0.0000 (free tier, dropped before any token usage was billable)",
GRAND TOTAL (all providers),,,,,,$6.7788,
COMBINED BUDGET CAP,,,,,,$10.00,margin=$3.2212
```

## Example questions most models got wrong

**Note on `loop_trace`/`call_count`/`control_flow` examples below:** the verifier traces a specific source line's exact hit count or which of two lines fires first. This is accurate to what that line literally did, but can diverge from the more intuitive question text when that line is itself a nested loop header (inflating the count) or when an enclosing loop/condition means neither branch is ever reached (the verifier then defaults to reporting 'else'). See `results/results_summary.md` and `results/metadata.json` (`known_measurement_caveat`) for the full explanation -- this does not affect `output`, `edge_case`, or `data_structure_state` examples.

### `s010_q5` (call_count, task `21_22-2-1-python`) -- wrong for 7/7 models

**Question:** Consider calling the code above like this:
```python
print(calc([0,0],[0]))
```
How many times total is `calc` called (including any recursive calls)?

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
- A) 1
- B) 2
- C) 5
- D) 3 <- correct

### `s017_q3` (loop_trace, task `19_20-6-1-python`) -- wrong for 7/7 models

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

### `s025_q3` (loop_trace, task `19_20-6-2-python`) -- wrong for 7/7 models

**Question:** Consider calling the code above like this:
```python
print(knapSack([6, 8],[6, 8],0))
```
How many times does the loop body starting at line 6 execute?

```python
def knapSack(value, volume, capacity):
    if len(value) == 0 or len(volume) == 0:
        return 0
    matrix = [[0 for col in range(capacity+1)] for row in range(len(volume))]
    for row in range(len(volume)):  # going through the matrix we set up
        for col in range(capacity+1):
            if volume[row] > col:  # this is the check to see if the item can go into our knap-sack
                matrix[row][col] = matrix[row-1][col]  # get the item above and place
            else:
                matrix[row][col] = max(matrix[row-1][col], matrix[row-1][col-volume[row]]+ value[row])
    packed = []
    col = capacity
    for row in range(len(volume)-1,-1,-1): 
        if row == 0 and matrix[row][col] != 0:
            packed.insert(0,row)
        if matrix[row][col] != matrix[row-1][col]:
            packed.insert(0,row)
            col -= volume[row]
    return matrix[len(volume)-1][capacity]
```
- A) 3
- B) 1
- C) 4 <- correct
- D) 2

### `s028_q4` (loop_trace, task `21_22-2-2-python`) -- wrong for 7/7 models

**Question:** Consider calling the code above like this:
```python
print(calc([1,2],[(0,0),(1,1)]))
```
How many times does the loop body starting at line 5 execute?

```python
def calc(a,b):
    k=1
    c=b
    for i in range(len(b)):
        while k <= b[i][1]:
            a[k]=a[k]+a[k-1]
            k=k+1
        if b[i][0]>0:
            c[i]=a[b[i][1]]-a[b[i][0]-1]
        else:
            c[i]=a[b[i][1]]
    return c
```
- A) 2
- B) 4
- C) 3 <- correct
- D) 1

### `s038_q4` (control_flow, task `19_20-6-1-python`) -- wrong for 7/7 models

**Question:** Consider calling the code above like this:
```python
print(editDistance("",""))
```
At the first `if` statement in the function (line 16), which branch executes?

```python
def editDistance(a, b):
    m = len(a)
    n = len(b)
    edit_matrix = [[0]*(n+1) for _ in range(m+1)]
    for i in range(1, m+1):
        edit_matrix[i][0] = edit_matrix[i-1][0] + 1
    for j in range(1, n+1):
        edit_matrix[0][j] = edit_matrix[0][j-1] + 1
        for i in range(1, m+1):

            insert = edit_matrix[i][j-1] + 1
            delete = edit_matrix[i-1][j] + 1

            
            if a[i-1] == b[j-1]:
                replace = edit_matrix[i-1][j-1]
            else:
                replace = edit_matrix[i-1][j-1] + 1

            edit_matrix[i][j] = min(insert, delete, replace)
    return edit_matrix[m][n]
```
- A) the `if` branch executes (line 16)
- B) neither branch is reached (unreachable code)
- C) the `else`/`elif` branch executes (line 18) <- correct
- D) an exception is raised

## Draft poster sentences (real numbers only)

> Across 7 commercial model/setting combinations (OpenAI and Anthropic, via each provider's batch API), accuracy on 759 execution-verified AI-generated comprehension questions about real student code ranged from 58% (Claude Opus 5 (thinking: off)) to 95% (GPT-6 Astra (reasoning: low)).

> The question generator (Claude Sonnet 5), operating one-pass with no self-checking, produced 146 incorrect answer keys out of 759 verifiable questions (19.2%) across 8 comprehension categories.
