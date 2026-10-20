"""Offline tests for agent.py: a scripted fake model, no API key, no network.

Run from the VAT001_agent-loop folder:
    python tests/test_agent.py
(The openai package must be installed because agent.py imports it, but these
tests never call the real API.)
"""
import builtins
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace as NS

HERE = Path(__file__).resolve().parent.parent
BUGGY = (HERE / "demo" / "stats.py").read_text(encoding="utf-8")


# ---------- helpers ----------

def call(i, name, **args):
    return NS(id=f"call_{i}", type="function", function=NS(name=name, arguments=json.dumps(args)))


def reply(content=None, calls=None):
    msg = NS(content=content, tool_calls=calls)
    msg.model_dump = lambda exclude_none=True: {
        k: v for k, v in {
            "role": "assistant",
            "content": content,
            "tool_calls": [{"id": c.id, "type": "function",
                            "function": {"name": c.function.name, "arguments": c.function.arguments}}
                           for c in calls] if calls else None,
        }.items() if v is not None or not exclude_none
    }
    return NS(choices=[NS(message=msg)])


class FakeClient:
    """Plays back a fixed list of model replies and records what it was sent."""
    def __init__(self, replies):
        self.replies, self.sent = list(replies), []
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kw):
        self.sent.append(json.loads(json.dumps(kw["messages"], default=str)))
        if not self.replies:
            return reply(calls=[call(99, "list_files", path=".")])   # keeps asking forever
        return self.replies.pop(0)


def answers(*typed):
    seq = list(typed)
    builtins.input = lambda prompt="": seq.pop(0)


def fresh_project():
    """A temp folder with the buggy demo file; agent.ROOT points at it."""
    d = Path(tempfile.mkdtemp())
    (d / "stats.py").write_text(BUGGY, encoding="utf-8")
    agent.ROOT = d.resolve()
    return d


sys.path.insert(0, str(HERE))
import agent  # noqa: E402

OLD = "    return total / (len(numbers) - 1)"
NEW = "    return total / len(numbers)"


# ---------- tests ----------

def test_full_run_with_a_recoverable_bad_edit():
    d = fresh_project()
    answers("y")
    client = FakeClient([
        reply(calls=[call(1, "list_files", path=".")]),
        reply(calls=[call(2, "read_file", path="stats.py")]),
        reply(calls=[call(3, "edit_file", path="stats.py", old_text="return total/(len(numbers)-1)", new_text=NEW)]),  # paraphrase
        reply(calls=[call(4, "read_file", path="stats.py")]),
        reply(calls=[call(5, "edit_file", path="stats.py", old_text=OLD, new_text=NEW)]),
        reply(content="Fixed: divide by len(numbers)."),
    ])
    assert agent.run_agent("Find and fix the bug in stats.py", client) == "Fixed: divide by len(numbers)."
    assert NEW in (d / "stats.py").read_text(encoding="utf-8")
    # the failed edit went back to the model as text, tagged with its call id
    tool_msgs = [m for m in client.sent[3] if m.get("role") == "tool"]
    assert tool_msgs[-1]["tool_call_id"] == "call_3"
    assert tool_msgs[-1]["content"].startswith("Error: old_text must appear exactly once")
    shutil.rmtree(d)


def test_user_refuses_the_edit():
    d = fresh_project()
    answers("N")
    client = FakeClient([
        reply(calls=[call(1, "edit_file", path="stats.py", old_text=OLD, new_text=NEW)]),
        reply(content="Left the file unchanged."),
    ])
    agent.run_agent("fix it", client)
    assert (d / "stats.py").read_text(encoding="utf-8") == BUGGY
    last_tool = [m for m in client.sent[1] if m.get("role") == "tool"][-1]
    assert last_tool["content"] == "The user said no. Do not retry this edit."
    shutil.rmtree(d)


def test_paths_outside_the_project_are_refused():
    d = fresh_project()
    for bad in ("../secret.txt", "/etc/passwd", "demo/../../x"):
        try:
            agent.safe_path(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{bad} was not refused")
    assert agent.safe_path("stats.py") == (d / "stats.py").resolve()
    shutil.rmtree(d)


def test_bad_tool_arguments_become_an_error_message():
    fresh_project()
    out = agent.run_tool(NS(id="x", function=NS(name="read_file", arguments='{"nope": 1}')))
    assert out.startswith("Error:")
    out = agent.run_tool(NS(id="y", function=NS(name="no_such_tool", arguments="{}")))
    assert out.startswith("Error:")


def test_create_file_and_step_limit():
    d = fresh_project()
    answers("y")
    assert agent.edit_file("notes.md", "", "hi") == "Edited notes.md"
    assert (d / "notes.md").read_text(encoding="utf-8") == "hi"
    client = FakeClient([])          # never answers, only asks for tools
    assert agent.run_agent("loop forever", client) is None
    assert len(client.sent) == agent.MAX_STEPS
    shutil.rmtree(d)


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
    print(f"\n{len(tests)} tests passed")
