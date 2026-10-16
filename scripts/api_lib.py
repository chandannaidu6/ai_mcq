"""
Shared library for Step 5 (API answerers: Anthropic, OpenAI, Gemini).
Reuses the exact same prompt format as the open-source (vLLM) answerers in
04_run_one_model_v2.py so all models are compared on an identical prompt.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# reuse build_prompt/parse_letter from the vLLM answerer -- no vllm import
# happens at module import time there, so this is safe without a GPU.
from importlib import util as _ilu
_spec = _ilu.spec_from_file_location("vllm_answerer_v2", os.path.join(HERE, "04_run_one_model_v2.py"))
_vllm_answerer = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_vllm_answerer)

build_prompt_messages = _vllm_answerer.build_prompt  # -> [{"role": "user", "content": ...}]
parse_letter = _vllm_answerer.parse_letter

ROOT = os.path.dirname(HERE)


def build_prompt_text(q):
    """Same content as build_prompt_messages but as a single string (for
    APIs/SDKs that want a plain user message string)."""
    msgs = build_prompt_messages(q)
    return msgs[0]["content"]
