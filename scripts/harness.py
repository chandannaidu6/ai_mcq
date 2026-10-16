"""
Shared harness code injected into every verification subprocess.
Order in the assembled file is always:
    1. student solution_code            (lines 1..N, as sampled)
    2. per-task harness_code            (e.g. Node/CustomStack/ListToSort class,
                                          only needed by a few tasks; placed AFTER
                                          the student code so student code's own
                                          line numbers are never shifted)
    3. TRACER_CODE (below)              (defines __trace_hits / __trace_var / __trace_lines)
    4. the question's verification_code (calls into student code, prints the
                                          ground-truth value)
"""

TRACER_CODE = '''
import sys as __sys
import copy as __copy

def __trace_hits(line_no, call_fn):
    count = [0]
    def tracer(frame, event, arg):
        if event == 'line' and frame.f_lineno == line_no:
            count[0] += 1
        return tracer
    old = __sys.gettrace()
    __sys.settrace(tracer)
    try:
        call_fn()
    finally:
        __sys.settrace(old)
    return count[0]

def __trace_lines(line_nos, call_fn):
    counts = {ln: 0 for ln in line_nos}
    def tracer(frame, event, arg):
        if event == 'line' and frame.f_lineno in counts:
            counts[frame.f_lineno] += 1
        return tracer
    old = __sys.gettrace()
    __sys.settrace(tracer)
    try:
        call_fn()
    finally:
        __sys.settrace(old)
    return counts

def __trace_var(line_no, var_name, occurrence, call_fn):
    state = {"count": 0, "value": None}
    def tracer(frame, event, arg):
        if event == 'line' and frame.f_lineno == line_no:
            state["count"] += 1
            if state["count"] == occurrence:
                state["value"] = __copy.deepcopy(frame.f_locals.get(var_name))
        return tracer
    old = __sys.gettrace()
    __sys.settrace(tracer)
    try:
        call_fn()
    finally:
        __sys.settrace(old)
    return state["value"]
'''

NETWORK_BLOCK_CODE = '''
import socket as __socket_mod

class __NoNetwork(__socket_mod.socket):
    def __init__(self, *a, **kw):
        raise OSError("network access is disabled during answer-key verification")

__socket_mod.socket = __NoNetwork
__socket_mod.create_connection = lambda *a, **kw: (_ for _ in ()).throw(
    OSError("network access is disabled during answer-key verification"))
'''

HARNESS_NODE = '''
class Node:
    def __init__(self):
        self.key = None
        self.parent = None
        self.left = None
        self.right = None
'''

HARNESS_STACK = '''
class CustomStack:
    def __init__(self):
        self._s = list()
    def push(self, i):
        self._s.append(i)
    def pop(self):
        return self._s.pop()
    def head(self):
        return self._s[-1]
    def emptystack(self):
        return len(self._s) == 0
'''

HARNESS_LISTTOSORT = '''
class ListToSort:
    def __init__(self, listInput):
        self._lst = listInput
        self._count = 0
    def Swap(self, x, y):
        self._count += 1
        tmp = self._lst[x]; self._lst[x] = self._lst[y]; self._lst[y] = tmp
    def Larger(self, x, y):
        self._count += 1
        return self._lst[x] > self._lst[y]
    def Smaller(self, x, y):
        self._count += 1
        return self._lst[x] < self._lst[y]
    def Equal(self, x, y):
        self._count += 1
        return self._lst[x] == self._lst[y]
    def Length(self):
        return len(self._lst)
    def count(self):
        return self._count
    def to_list(self):
        return list(self._lst)
'''

HARNESS_BY_INDEX = {
    1: HARNESS_NODE,
    3: HARNESS_NODE,
    14: HARNESS_STACK,
    19: HARNESS_LISTTOSORT,
    22: HARNESS_NODE,
    24: HARNESS_NODE,
}

# Code that must be placed BEFORE the student's solution_code (shifting its line
# numbers by exactly the number of lines below). Needed only when the student's
# code references a name at *def-time* (e.g. in a type annotation, which Python
# evaluates eagerly), so it can't simply be appended after like the other harnesses.
# index 19 (listSorter) annotates its parameter as `listToSort: ListToSort`, which
# raises NameError at `def` time unless `ListToSort` already exists.
PRE_HARNESS_BY_INDEX = {
    19: "ListToSort = object\n",
}
