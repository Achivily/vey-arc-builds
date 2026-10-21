"""A tiny coding agent: one model, three tools, one loop.

Vey Arc's Tutorial, VAT001. Works with any OpenAI-compatible Chat Completions API
(OpenAI, DeepSeek, a local Ollama server, ...). See README.md.
"""
import json
import os
import sys
from pathlib import Path

from openai import OpenAI

MODEL = os.environ.get("AGENT_MODEL", "deepseek-flash")
MAX_STEPS = 20
ROOT = Path.cwd().resolve()

SYSTEM_PROMPT = (
    "You are a coding agent working inside the user's project folder. "
    "Use the tools to look at files before you change them. "
    "Make small, exact edits. When the task is done, say what you changed."
)


# ---------- tools: plain Python functions ----------

def safe_path(path):
    """Resolve a path and refuse anything outside the project folder."""
    full = (ROOT / path).resolve()
    if full != ROOT and ROOT not in full.parents:
        raise ValueError(f"{path} is outside the project folder")
    return full


def list_files(path="."):
    folder = safe_path(path)
    names = sorted(p.name + ("/" if p.is_dir() else "") for p in folder.iterdir())
    return "\n".join(names) or "(empty folder)"


def read_file(path):
    return safe_path(path).read_text(encoding="utf-8")


def edit_file(path, old_text, new_text):
    file = safe_path(path)
    content = "" if old_text == "" else file.read_text(encoding="utf-8")
    if old_text and content.count(old_text) != 1:
        return "Error: old_text must appear exactly once in the file. Read it again."
    if not confirm(f"edit {path}"):
        return "The user said no. Do not retry this edit."
    new_content = content.replace(old_text, new_text) if old_text else new_text
    file.write_text(new_content, encoding="utf-8")
    return f"Edited {path}"


def confirm(action):
    answer = input(f"\n  Allow the agent to {action}? [y/N] ")
    return answer.strip().lower() == "y"


TOOLS = {"list_files": list_files, "read_file": read_file, "edit_file": edit_file}


# ---------- tool descriptions: what the model sees ----------

def tool(name, description, **params):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {k: {"type": "string", "description": v} for k, v in params.items()},
                "required": list(params),
            },
        },
    }


TOOL_SPECS = [
    tool("list_files", "List files and folders at a path.", path="Folder path, e.g. ."),
    tool("read_file", "Read a text file.", path="File path"),
    tool(
        "edit_file",
        "Replace old_text with new_text in a file. old_text must match exactly once. "
        "Use an empty old_text to create a new file.",
        path="File path",
        old_text="Exact text to replace",
        new_text="Replacement text",
    ),
]


# ---------- the loop ----------

def run_tool(call):
    name = call.function.name
    try:
        args = json.loads(call.function.arguments or "{}")
        print(f"  -> {name}({', '.join(f'{k}={v!r:.40}' for k, v in args.items())})")
        return str(TOOLS[name](**args))
    except Exception as error:  # the model sees the error and can try again
        return f"Error: {error}"


def run_agent(task, client):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]
    for step in range(1, MAX_STEPS + 1):
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOL_SPECS
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        if not message.tool_calls:  # no tool requests: the model is done
            print(f"\n{message.content}")
            return message.content

        for call in message.tool_calls:
            result = run_tool(call)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

    print(f"\nStopped after {MAX_STEPS} steps.")
    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('Usage: python agent.py "describe the task"')
    run_agent(" ".join(sys.argv[1:]), OpenAI())
