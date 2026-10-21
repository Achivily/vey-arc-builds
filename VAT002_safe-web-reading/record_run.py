"""Record one real run of the VAT002 agent for the video (Vey Arc's Tutorials).

Runs agent.py unchanged, but saves everything that happens with timestamps, so the
terminal can be re-drawn in the video exactly as it happened (Hack Nerd Font card):
  - every line the agent prints and every [y/N] answer you type
  - each model call: when it started, how long the model took, the tool calls it asked for, token usage
  - every page fetch: raw HTML size, cleaned text size, and what the model received
  - notes.md and stats.py before / after
Your API key is never written to the file.

Usage (from the demo folder, the same way the video runs it):
    cd demo
    set AGENT_WRITABLE=notes.md          (PowerShell: $env:AGENT_WRITABLE="notes.md")
    python ../record_run.py "Read <url> and write a five-bullet summary to notes.md"
Optional:  --agent ../agent.py   --out ../recordings   --keep-notes

Before each run notes.md is deleted (unless --keep-notes) and stats.py is restored from
recordings/stats.py.orig (saved on the first run), so every run starts from the same folder.
"""
import argparse, builtins, datetime, importlib.util, json, os, pathlib, platform, shutil, subprocess, sys, time

ap = argparse.ArgumentParser()
ap.add_argument("task")
ap.add_argument("--agent", default=str(pathlib.Path(__file__).resolve().parent / "agent.py"))
ap.add_argument("--out", default=str(pathlib.Path(__file__).resolve().parent / "recordings"))
ap.add_argument("--file", default="stats.py", help="the demo file to restore before the run")
ap.add_argument("--notes", default="notes.md", help="the file the agent is asked to write; deleted before the run")
ap.add_argument("--keep-notes", action="store_true", help="do not delete notes.md before the run")
ap.add_argument("--expect", default=None, help="optional text the demo file's output must contain before the run")
A = ap.parse_args()

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

demo = pathlib.Path.cwd()
target = demo / A.file
# the clean copy lives next to the recordings, NOT in the demo folder (the agent would see it when it lists files)
pathlib.Path(A.out).mkdir(parents=True, exist_ok=True)
orig = pathlib.Path(A.out) / (A.file + ".orig")
if target.exists() and not orig.exists():
    shutil.copy2(target, orig)
    print(f"[recording] saved the clean copy of {A.file} -> {orig}  (make sure it is still the BUGGY version)")
if orig.exists():
    shutil.copy2(orig, target)            # every run starts from the same file
notes = demo / A.notes
if notes.exists() and not A.keep_notes:
    notes.unlink()
    print(f"[recording] deleted the old {A.notes} so this run starts clean")
read = lambda p: p.read_text(encoding="utf-8") if p.exists() else None

def run_file():
    if not target.exists():
        return None
    r = subprocess.run([sys.executable, A.file], capture_output=True, text=True, cwd=demo)
    return (r.stdout + r.stderr).strip()

_before = run_file()
if A.expect and (_before is None or A.expect not in _before):
    print(f"[recording] WARNING: {A.file} prints {_before!r}, expected it to contain {A.expect!r}.")
    print(f"[recording] Restore the original {A.file} and delete {orig}, then run again.")
    sys.exit(1)

T0 = time.perf_counter()
now = lambda: round(time.perf_counter() - T0, 3)
events, calls = [], []
rec = {
    "task": A.task,
    "started": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    "python": platform.python_version(),
    "platform": platform.platform(),
    "base_url": os.environ.get("OPENAI_BASE_URL", "(default: api.openai.com)"),
    "model": os.environ.get("AGENT_MODEL", "(agent.py default)"),
    "writable": os.environ.get("AGENT_WRITABLE", ""),
    "file_before": read(target),
    "notes_before": read(notes),
    "run_before": _before,
    "events": events,
    "model_calls": calls,
}

# ---- capture the terminal ----
_print, _input = builtins.print, builtins.input
def rec_print(*args, sep=" ", end="\n", file=None, flush=False):
    if file in (None, sys.stdout):
        events.append({"t": now(), "kind": "out", "text": sep.join(str(a) for a in args) + end})
    _print(*args, sep=sep, end=end, file=file, flush=flush)
def rec_input(prompt=""):
    events.append({"t": now(), "kind": "prompt", "text": str(prompt)})
    answer = _input(prompt)
    events.append({"t": now(), "kind": "typed", "text": answer + "\n"})
    return answer
builtins.print, builtins.input = rec_print, rec_input

# ---- load agent.py unchanged ----
spec = importlib.util.spec_from_file_location("agent", A.agent)
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)
rec["model"] = agent.MODEL
try:
    import openai
    rec["openai_version"] = openai.__version__
except Exception:
    pass

# tool results go back to the model, not to the screen — record them too (this is where the edit error shows up)
_run_tool = agent.run_tool
def rec_run_tool(call):
    result = _run_tool(call)
    events.append({"t": now(), "kind": "tool_result", "name": call.function.name, "text": result})
    return result
agent.run_tool = rec_run_tool

# page sizes: how much HTML came in, how much clean text the model got
fetches = rec["fetches"] = []
_clean = agent.clean_html
def rec_clean(html):
    text = _clean(html)
    fetches.append({"t": now(), "raw_html_chars": len(html), "clean_text_chars": len(text)})
    return text
agent.clean_html = rec_clean

client = agent.OpenAI()
_create = client.chat.completions.create
def rec_create(**kw):
    c = {"t_start": now()}
    events.append({"t": c["t_start"], "kind": "model_wait_start"})
    try:
        resp = _create(**kw)
    except Exception as e:
        c.update(t_end=now(), error=repr(e)); calls.append(c)
        events.append({"t": c["t_end"], "kind": "model_error", "text": repr(e)})
        raise
    c["t_end"] = now()
    m = resp.choices[0].message
    c["model"] = getattr(resp, "model", None)
    c["content"] = m.content
    c["tool_calls"] = [{"name": tc.function.name, "arguments": tc.function.arguments} for tc in (m.tool_calls or [])]
    u = getattr(resp, "usage", None)
    if u is not None:
        c["usage"] = u.model_dump() if hasattr(u, "model_dump") else dict(u)
    calls.append(c)
    events.append({"t": c["t_end"], "kind": "model_wait_end"})
    return resp
client.chat.completions.create = rec_create

# ---- run ----
_print(f"\n[recording] {A.task}\n")
try:
    rec["final_answer"] = agent.run_agent(A.task, client)
    rec["status"] = "finished"
except KeyboardInterrupt:
    rec["status"] = "interrupted"
except Exception as e:
    rec["status"] = "crashed: " + repr(e)
finally:
    builtins.print, builtins.input = _print, _input
    rec["duration"] = now()
    rec["file_after"] = read(target)
    rec["notes_after"] = read(notes)
    rec["run_after"] = run_file()
    out = pathlib.Path(A.out); out.mkdir(parents=True, exist_ok=True)
    f = out / f"run_{datetime.datetime.now():%Y%m%d_%H%M%S}.json"
    f.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    tok = sum((c.get("usage") or {}).get("total_tokens", 0) for c in calls)
    errs = sum(1 for e in events if e["kind"] == "tool_result" and e["text"].startswith("Error"))
    _print(f"\n[recording] saved {f}")
    _print(f"[recording] {rec['status']} · {len(calls)} model calls · {errs} tool errors · {tok} tokens · {rec['duration']:.1f}s")
    for x in fetches:
        _print(f"[recording] page: {x['raw_html_chars']} chars of HTML -> {x['clean_text_chars']} chars of text")
    _print(f"[recording] {A.notes}: {'written' if rec['notes_after'] else 'not written'} · "
           f"{A.file} {'unchanged' if rec['file_after'] == rec['file_before'] else 'CHANGED'}")
