"""List real, currently-available model IDs from each provider's own API.
Never guesses/hardcodes model names -- this is the source of truth used to
pick which exact model IDs Step 5 calls."""
import os
import json

from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
load_dotenv(os.path.join(ROOT, ".env"))

out = {}

# --- Anthropic ---
try:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["CLAUDE_API_KEY"])
    models = client.models.list(limit=1000)
    out["anthropic"] = [{"id": m.id, "display_name": getattr(m, "display_name", None)} for m in models.data]
except Exception as e:
    out["anthropic_error"] = repr(e)

# --- OpenAI ---
try:
    import openai
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    models = client.models.list()
    out["openai"] = sorted([m.id for m in models.data])
except Exception as e:
    out["openai_error"] = repr(e)

# --- Gemini ---
try:
    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    models = client.models.list()
    out["gemini"] = []
    for m in models:
        out["gemini"].append({
            "name": m.name,
            "display_name": getattr(m, "display_name", None),
            "supported_actions": list(getattr(m, "supported_actions", []) or []),
            "input_token_limit": getattr(m, "input_token_limit", None),
            "output_token_limit": getattr(m, "output_token_limit", None),
        })
except Exception as e:
    out["gemini_error"] = repr(e)

out_path = os.path.join(ROOT, "pilot_data", "provider_models.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print(f"Wrote {out_path}")

print("\n=== ANTHROPIC ===")
if "anthropic_error" in out:
    print("ERROR:", out["anthropic_error"])
else:
    for m in out["anthropic"]:
        print(" ", m["id"], "|", m["display_name"])

print("\n=== OPENAI ===")
if "openai_error" in out:
    print("ERROR:", out["openai_error"])
else:
    for m in out["openai"]:
        print(" ", m)

print("\n=== GEMINI ===")
if "gemini_error" in out:
    print("ERROR:", out["gemini_error"])
else:
    for m in out["gemini"]:
        print(" ", m["name"], "|", m["display_name"], "| actions:", m["supported_actions"])
