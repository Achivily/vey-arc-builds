<div align="center">

# Vey Arc Builds

**Small, runnable AI-agent projects from the Vey Arc Build series (VAT).**
One folder per episode · pinned versions · tested on real models before the video ships.

[![YouTube](https://img.shields.io/badge/YouTube-Vey%20Arc-FF0000?logo=youtube&logoColor=white)](https://www.youtube.com/channel/UCLV_kslwMQv05BqudyKRL5g)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Episodes](https://img.shields.io/badge/episodes-1-FF5A36)](#episodes)
[![No framework](https://img.shields.io/badge/framework-none-25313D)](#conventions)

</div>

---

## About

Each Vey Arc Build episode takes one idea from AI agent engineering and builds it in about six minutes of video, with code you can run the same day. This repository holds that code.

- **Self-contained.** Every episode lives in its own numbered folder with its own `README.md`, `requirements.txt`, demo files and tests. Nothing is shared between folders, so one episode never breaks another.
- **Pinned and verified.** Each episode lists the exact Python version, package versions, provider and model it was verified with, and the date.
- **Real runs, kept.** When a video shows the agent running, the raw logs of those runs are committed under the episode's `recordings/` folder, so you can check what the video shows.

## Episodes

| No. | Episode | Folder | Topics | Verified with | Video |
|:---:|---|---|---|---|---|
| **VAT001** | Every AI Agent Is the Same Loop | [`VAT001_agent-loop/`](VAT001_agent-loop/) | `agent-loop` `tool-calling` `harness` | Python 3.13.16 · openai 3.35.1 · deepseek-flash · 2026-10-19 | coming soon |

<sub>Numbering: `VAT` + three digits, in release order. Folder names are `VAT<NNN>_<short-slug>`.</sub>

## Quick start

```bash
git clone https://github.com/Achivily/vey-arc-builds.git
cd vey-arc-builds/VAT001_agent-loop
python -m venv .venv
# macOS / Linux:  source .venv/bin/activate
# Windows:        .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Then follow the episode's own `README.md`: provider settings, how to run the demo, and how to run the offline tests.

## Conventions

| Rule | Why |
|---|---|
| Plain Python, no agent framework | You can read every line that runs |
| Any OpenAI-compatible Chat Completions API | One code path works with OpenAI, DeepSeek and local Ollama |
| Offline tests with a scripted fake model | The logic is checked without an API key or network |
| Version pins in `requirements.txt` | The code you clone behaves like the code in the video |
| A **Verified** table in every episode README | You know exactly what was tested, and when |

## Safety

These projects give a language model tools that act on your computer.

- Run them in a **throwaway folder or a copy** of your project, never on the only copy of anything.
- Read the confirmation prompts. Agents in this repo ask before they write, but you are the last check.
- Never commit API keys. Pass them as environment variables (see each episode README).

## Issues and contributions

Found a bug, or a provider that behaves differently? [Open an issue](https://github.com/Achivily/vey-arc-builds/issues) with the episode number (for example `VAT001`), your Python and package versions, the provider and model, and the terminal output.
Pull requests that fix bugs are welcome. Feature additions usually belong in a later episode, so the code keeps matching its video.

## License

[MIT](LICENSE) © 2026 Vey Arc.

Product and company names (OpenAI, DeepSeek, Ollama, Anthropic and others) are trademarks of their respective owners and are used here only to identify compatible services. Vey Arc is not affiliated with them.
