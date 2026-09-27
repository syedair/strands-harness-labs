# The video diagrams: an intro, the lab map, and one diagram per lab with the code that sets it up.
# Built with the excalidraw-diagrams skill (github.com/syedair/syedair-skills). From the repo root:
#   uv run --with fonttools --with brotli --with playwright python docs/diagrams/make_diagrams.py
# Every fact comes from the labs' code, a measurement in this repo, or a source printed on the diagram.
import os
import sys
from pathlib import Path

SKILL = Path(os.environ.get("EXCALIDRAW_DIAGRAMS", Path.home() / ".claude/skills/excalidraw-diagrams")) / "scripts"
sys.path.insert(0, str(SKILL))
from excalidraw_lib import CODE, KINDS, MUTED, SOFT, Diagram, X, Y  # noqa: E402

OUT = Path(__file__).resolve().parent
problems = 0


def done(d):
    global problems
    problems += len(d.save(OUT))


# =====================================================================================================================
# INTRO 1 — What is an agent harness?
d = Diagram("00a-what-is-a-harness")
d.header("What is an agent harness?", None, "intro")
d.text(100, 128, "“An agent harness is the software around a model that turns it into an agent.”  — Strands docs [1]",
       20, color=SOFT)
d.zone("AGENT HARNESS · everything around the loop", box=(100, 210, 1180, 900), kind="harness", opacity=30)
d.zone("AGENT · model → tools → results → model", box=(380, 380, 1030, 760), kind="llm", opacity=45)
d.node("llm", 410, 450, "Model", "llm", "an LLM on its own:\none prompt in, text out", icon="Sparkles")
d.node("tools", 780, 640, "Tools", "tool", icon="Wrench", size=19)
d.arrow("llm", "tools", "tool call", color=KINDS["tool"][0], bend=-50)
d.arrow("tools", "llm", "result", color=KINDS["tool"][0], bend=-50)
chips = [("Sessions", "History", "memory", 130, 262), ("Memory", "Brain", "memory", 400, 262),
         ("Skills", "BookOpenText", "memory", 660, 262), ("Context\nmanagement", "Layers", "harness", 900, 255),
         ("Interventions", "ShieldCheck", "harness", 130, 800), ("Built-in tools", "Wrench", "tool", 410, 800),
         ("MCP servers", "Plug", "tool", 680, 800), ("Sandbox & shell", "Box", "harness", 920, 800),
         ("Observability", "Eye", "app", 130, 520)]
for i, (t, ic, k, x, y) in enumerate(chips):
    d.node(f"chip{i}", x, y, t, k, icon=ic, size=18)
d.bars(1250, 230, "Same model, better harness\n(Terminal Bench 2.0, reported by LangChain [2])",
       [("before", 52.8, "app"), ("after", 66.5, "harness")], vmax=80, width=280, fmt="{:.1f}%",
       note="LangChain moved its agent from outside the top 30\nto the top 5 by changing only the harness.")
d.note(1250, 600, "A model answers.\nAn agent loops and uses tools.\nA harness makes it dependable:\nstate, memory, skills, guardrails,\ncontext and a safe place to run.")
d.text(100, 940, "[1] strandsagents.com/docs/user-guide/sdk    [2] medium.com/@phansiri (citing LangChain); langchain.com/deep-agents",
       14, CODE, MUTED)
done(d)

# INTRO 2 — Strands Harness
d = Diagram("00b-strands-harness")
d.header("Strands Harness", "agent = create_harness(model=..., instructions=...)", "intro")
d.node("call", X(0), Y(0.35), "create_harness(…)", "code", "one call, opinionated defaults", icon="Code", size=20)
d.node("agent", X(0), Y(1.7), "a plain Strands Agent", "harness", "nothing wraps it: the full\nStrands SDK still works",
       icon="Bot")
d.arrow("call", "agent", "returns", color=KINDS["harness"][0])
defaults = [("System prompt", "ScrollText", "benchmarked default", "app"), ("Built-in tools", "Wrench", "Lab 2", "tool"),
            ("Sessions", "History", "Lab 3", "memory"), ("Memory", "Brain", "Lab 3", "memory"),
            ("Skills", "BookOpenText", "Lab 4", "memory"), ("Interventions", "ShieldCheck", "Labs 5, 7, 8", "harness"),
            ("Model router", "Split", "Lab 9", "harness"), ("MCP servers", "Plug", "Lab 11", "tool"),
            ("Context management", "Layers", "keeps long chats in budget", "harness")]
for i, (t, ic, s, k) in enumerate(defaults):
    r, c = divmod(i, 3)
    d.node(f"def{i}", X(1.25) + c * 330, Y(0.1) + r * 150, t, k, s, icon=ic, size=19, w=290)
d.zone("DEFAULTS · every one overridable", [f"def{i}" for i in range(9)], "harness", pad=28)
d.arrow("call", "def0", "sets up", dashed=True, color=KINDS["harness"][0])
d.table(X(0), Y(3.1), [("", 110), ("The Strands toolkit", 220), ("What it's for", 520)],
        [["START", "/harness", "a fully assembled agent harness (this series)"],
         ["BUILD", "/harness-sdk", "build your own harness: you own the loop"],
         ["CONTROL", "/shell", "a virtual shell designed for agents to use safely"],
         ["VALIDATE", "/evals", "validate your agent before you ship"],
         ["EXPLORE", "/labs", "experimental projects: robotics, world models"]], kind="harness",
        title="strandsagents.com · Explore by Toolkit")
d.note(X(2.4), Y(3.2), "Open source, model-agnostic.\nStart with the defaults,\noverride what you need.")
done(d)

# INTRO 3 — the harness landscape
d = Diagram("00c-harness-landscape")
d.header("The harness landscape", None, "intro")
d.text(100, 128, "Each ecosystem now has a library you run and a service that runs it for you.", 20, color=SOFT)
d.table(100, 210, [("Harness", 250), ("What it is", 300), ("Runs", 260), ("Models", 240), ("Best for", 300)], [
    ["Strands harness  [1]", "open-source library,\nopinionated defaults", "in your own process", "any: Bedrock, Ollama,\nOpenAI, …", "full control; custom\ninterventions (System 1)"],
    ["AgentCore harness  [2]", "managed AWS service:\nconfiguration, not code", "an isolated microVM\nper session", "any: Bedrock, OpenAI,\nGemini, LiteLLM", "production: identity, memory,\nobservability handled"],
    ["Deep Agents  [4]", "open-source harness on\nLangChain + LangGraph", "in your own process", "any", "teams on LangChain"],
    ["Managed Deep Agents  [5]", "LangSmith runs your\nDeep Agent (beta)", "LangSmith Cloud", "you choose the model", "Deep Agents without\nrunning servers"],
    ["Claude Agent SDK  [6]", "Claude Code's loop, tools\nand context, as an SDK", "in your own process", "Claude", "Claude-first agents that\nwork with files and code"],
    ["Claude Managed Agents  [7]", "Anthropic's managed\nharness (beta)", "Anthropic's cloud sandbox,\nor a self-hosted one", "Claude", "long-running and\nasynchronous work"],
], kind="harness", size=16)
top, left, cw, ch = 800, 330, 640, 300
d.text(100, top - 80, "Where they sit", 30)
quads = {"YOU RUN IT · ANY MODEL": (left, top, "harness"), "MANAGED FOR YOU · ANY MODEL": (left + cw + 40, top, "llm"),
         "YOU RUN IT · CLAUDE ONLY": (left, top + ch + 40, "harness"),
         "MANAGED FOR YOU · CLAUDE ONLY": (left + cw + 40, top + ch + 40, "llm")}
for label, (qx, qy, kind) in quads.items():
    d.zone(label, box=(qx, qy, qx + cw, qy + ch), kind=kind, opacity=28)
d.text(left + cw / 2, top - 40, "a library you run", 20, color=SOFT, align="center")
d.text(left + cw * 1.5 + 40, top - 40, "a service that runs it", 20, color=SOFT, align="center")
d.text(110, top + ch / 2 - 12, "any model", 20, color=SOFT)
d.text(110, top + ch * 1.5 + 28, "Claude only", 20, color=SOFT)
d.node("strands", left + 40, top + 70, "Strands harness", "harness", "AWS · open source", icon="Bot", w=280)
d.node("deep", left + 40, top + 190, "Deep Agents", "app", "LangChain · open source", icon="Layers", w=280)
d.node("agentcore", left + cw + 100, top + 70, "AgentCore harness", "tool", "AWS · generally available", icon="Cloud", w=320)
d.node("mda", left + cw + 100, top + 190, "Managed Deep Agents", "app", "LangSmith · beta", icon="Cloud", w=320)
d.node("sdk", left + 40, top + ch + 40 + 110, "Claude Agent SDK", "llm", "Anthropic", icon="Code", w=280)
d.node("cma", left + cw + 100, top + ch + 40 + 110, "Claude Managed Agents", "llm", "Anthropic · beta", icon="Cloud", w=320)
d.arrow("agentcore", "strands", "export to code  [3]", dashed=True, color=KINDS["tool"][0], bend=-40)
d.arrow("strands", "agentcore", "host on AgentCore Runtime  [8]", dashed=True, color=KINDS["harness"][0], bend=-40)
d.arrow("deep", "mda", "deploy with the mda CLI  [5]", dashed=True, color=SOFT)
d.note(left + 2 * cw + 110, top + 20, "Pick by where you want\nto run it, then which\nmodels you need.\n\nThe labs use Strands harness:\nit runs in your process, so we\ncan plug System 1 into its\ninterventions.")
d.text(100, top + 2 * ch + 110, "Sources (September 2026)", 18, color=SOFT)
d.text(100, top + 2 * ch + 150, "\n".join([
    "[1] strandsagents.com/docs/user-guide/harness",
    "[2] docs.aws.amazon.com/bedrock-agentcore/latest/devguide/harness.html",
    "[3] docs.aws.amazon.com/bedrock-agentcore/latest/devguide/harness-export.html",
    "[4] langchain.com/deep-agents",
    "[5] docs.langchain.com/langsmith/python/managed-deep-agents-overview",
    "[6] docs.langchain.com/oss/python/deepagents/comparison",
    "[7] platform.claude.com/docs/en/managed-agents/overview",
    "[8] aws.amazon.com/blogs/machine-learning/market-surveillance-agent-with-langgraph-and-strands-on-agentcore"]),
    14, CODE, MUTED)
done(d)

# INTRO 4 — System 1 vs LLMs
d = Diagram("00d-system1-vs-llm")
d.header("System 1 models vs LLMs", None, "intro")
d.text(100, 128, "Named after Kahneman's two systems: System 1 is fast and intuitive, System 2 slow and deliberate.",
       20, color=SOFT)
d.table(100, 210, [("", 150), ("LLM  (System 2)", 330), ("System 1 model", 360)], [
    ["Output", "open text, plans, tool calls", "a probability for a narrow,\ntyped question"],
    ["How", "many tokens, step by step", "one pass"],
    ["Speed", "seconds", "≈ 0.1 – 0.4 s  (measured, right)"],
    ["Size · cost", "large; priced per token", "small; runs locally or cheaply"],
    ["Decides?", "writes the reply", "never: your code sets\nthe threshold and acts"],
    ["Good at", "reasoning, writing, planning", "yes/no, pick one, score,\nrouting, checking"],
], kind="s1", size=17)
d.bars(1120, 210, "System 1 response time, measured in lab 10\n(average per question set, this machine)",
       [("Kev-4B (open)", 115, "s1"), ("Qwen stand-in", 137, "s1"), ("Jev (hosted)", 376, "s1")],
       vmax=420, width=280, fmt="{:.0f} ms")
d.node("llm", 1120, 600, "LLM does the thinking", "llm", icon="Sparkles", size=19)
d.node("s1", 1120, 800, "System 1 checks the work", "s1", "which memories · allow the tool? ·\nis the answer complete?",
       icon="Zap", size=19)
d.arrow("llm", "s1", both=True, color=KINDS["s1"][0])
done(d)

# LAB MAP -------------------------------------------------------------------------------------------------------------
d = Diagram("00e-lab-map")
d.header("The labs", "Build a travel assistant one harness feature at a time, then let System 1 check its work.", "intro")
labs = [("1", "Your first harness", "one call, a working agent", "harness", "Bot"),
        ("2", "Built-in tools", "tools without writing code", "harness", "Wrench"),
        ("3", "Sessions & memory", "remembers across restarts", "harness", "Brain"),
        ("4", "Skills", "know-how in markdown", "harness", "BookOpenText"),
        ("5", "Interventions", "a checkpoint before tools", "harness", "ShieldCheck"),
        ("6", "System 1 basics", "narrow questions, probabilities", "s1", "Zap"),
        ("7", "Tool-call gate", "catches guessed arguments", "s1", "ShieldCheck"),
        ("8", "Completion check", "catches half answers", "s1", "CircleCheckBig"),
        ("9", "Model switching", "picks the model per message", "s1", "Split"),
        ("10", "System 1 showdown", "measures the classifiers", "s1", "ChartColumn"),
        ("11", "The Harness App", "everything, in one app", "llm", "Sparkles")]
for i, (n, name, gist, kind, ic) in enumerate(labs):
    row, c = (0, i) if i < 5 else (1, 9 - i) if i < 10 else (2, 0)
    d.node(n, 110 + c * 390, 300 + row * 240, f"Lab {n} · {name}", kind, gist, icon=ic, size=19, w=330)
order = [l[0] for l in labs]
for a, b in zip(order, order[1:]):
    d.arrow(a, b)
d.zone("① HARNESS BASICS", ["1", "2", "3", "4", "5"], "harness", pad=28)
d.zone("② SYSTEM 1 CHECKS THE WORK", ["6", "7", "8", "9", "10"], "s1", pad=28)
d.zone("③ THE APP", ["11"], "llm", pad=28)
done(d)

# LABS ----------------------------------------------------------------------------------------------------------------
# Each lab diagram: the idea in one sentence, the harness built so far (NEW in yellow, like the highlighted code),
# the flow, the create_harness() call with a dotted line from the new argument to what it adds, and the real output.
# Terminal output: real runs, September 2026, Kimi K2.5 on Bedrock, Kev-4B as System 1. Trimmed with "…".
CX = X(3.4)  # the code column, right of the flow
PARTS = ["model", "builtin_tools", "session", "memory", "skills", "interventions", "System 1", "ModelRouter",
         "mcp_servers"]
TERM = {"→ Guide": "#ff8787", "→ Proceed": "#8ce99a", "→ small": "#8ce99a", "→ big": "#74c0fc", "✗": "#ff8787",
        "✓": "#8ce99a", "you:": "#ffd43b", " · ": "#ffa94d", "-> Guide": "#ff8787",
        "P(": "#a5d8ff", "proposes": "#ffd43b", "$ uv": "#868e96", "Tool #": "#ffa94d", "ask which": "#ff8787",
        "go: ": "#8ce99a", "user said": "#868e96", "──": "#868e96"}


def lab(name, title, idea, phase, n, have, new):
    d = Diagram(name)
    d.header(title, None, phase, f"{n} of 11")
    d.idea(idea)
    d.strip(CX, 36, PARTS, have, new, title="YOUR TOOLKIT SO FAR")
    return d


def run(d, key, x, y, cmd, output, size=14):
    return d.terminal(key, x, y, output, title=f"$ uv run {cmd}", size=size, colors=TERM)


# LAB 1
d = lab("lab01-first-harness", "Lab 1 · Your First Harness", "One call turns a model into a working agent.",
        "basics", 1, [], ["model"])
d.node("you", X(0), Y(0.4), "“A city break\nfrom Dubai?”", "user", icon="User", shape="ellipse")
d.node("agent", X(1), Y(0.4), "Agent", "harness", "built by the harness", icon="Bot")
d.node("llm", X(2.1), Y(0.4), "LLM", "llm", "Kimi K2.5 on Bedrock", icon="Sparkles")
d.node("plain", X(2.1), Y(1.55), "Hand-built Agent", "app", "model + prompt + tools\n+ loop, wired by you", icon="Wrench")
d.arrow("you", "agent", step=1)
d.arrow("agent", "llm", both=True, step=2, color=KINDS["llm"][0])
d.arrow("plain", "agent", "same Agent, more code", dashed=True, color=MUTED)
d.zone("STRANDS HARNESS", ["agent"])
d.code("code", CX, Y(0.4), """agent = create_harness(
    model=MAIN_MODEL,
    instructions=INSTRUCTIONS,
    builtin_tools=[],
    session=False,
    memory=False,
    skills=False,
)""", title="labs/lab1_first_harness.py", highlight=[1, 2])
d.link("code", 1, "llm", size=15)
run(d, "out", X(0), Y(2.75), "labs/lab1_first_harness.py", """Hand-built Agent tools: []
Harness agent is a Agent running on bedrock/moonshotai.kimi-k2.5
**Muscat, Oman** – Perfect for a weekend escape from Dubai. …""")
d.note(CX, Y(2.75), "Same Strands Agent either way.\nEvery later lab changes one\nargument of create_harness().")
done(d)

# LAB 2
d = lab("lab02-builtin-tools", "Lab 2 · Built-in Tools", "Name the tools you want. The harness runs them for you.",
        "basics", 2, ["model"], ["builtin_tools"])
d.node("you", X(0), Y(0.4), "“Weather in\nIstanbul right now?”", "user", icon="User", shape="ellipse")
d.node("agent", X(1.25), Y(0.4), "Agent", "harness", icon="Bot")
d.node("llm", X(2.4), Y(0.4), "LLM", "llm", "decides it needs a tool", icon="Sparkles")
d.node("tools", X(1.2), Y(1.75), "Built-in tools", "tool", "web_fetch · read · write", icon="Wrench")
d.node("web", X(2.3), Y(1.75), "wttr.in/Istanbul", "web", "the forecast", icon="Globe")
d.arrow("you", "agent", step=1)
d.arrow("agent", "llm", "“call web_fetch”", both=True, step=2, color=KINDS["llm"][0])
d.arrow("agent", "tools", "run it", step=3, bend=-70, color=KINDS["tool"][0])
d.arrow("tools", "web", "GET", step=4, color=KINDS["web"][0])
d.arrow("tools", "agent", "the forecast", bend=-70, color=KINDS["tool"][0], step=5)
d.zone("STRANDS HARNESS", ["agent", "tools"])
d.code("code", CX, Y(0.4), """agent = create_harness(
    model=MAIN_MODEL,
    instructions=INSTRUCTIONS,
    builtin_tools=["web_fetch", "read", "write"],  # NEW
    session=False,
    memory=False,
    skills=False,
)""", title="labs/lab2_builtin_tools.py", highlight=[4])
d.link("code", 4, "web", size=15)
run(d, "out", X(0), Y(3.05), "labs/lab2_builtin_tools.py", """Tools this agent can use: ['read', 'write', 'web_fetch',
  'retrieve_offloaded_content', 'todo_write', 'retrieve_context', …]
Tool #1: web_fetch
It's currently **20°C (68°F) and cloudy** in Istanbul ☁️. Enjoy your day there!""")
d.note(CX, Y(2.35), "No tool code to write.\nThe model asks, the harness runs it\nand hands back the result.\nIt also brings a few tools of its own.")
done(d)

# LAB 3
d = lab("lab03-sessions-memory", "Lab 3 · Sessions & Memory",
        "Stop the program, start it again. The agent still knows you.", "basics", 3,
        ["model", "builtin_tools"], ["session", "memory"])
d.node("you1", X(0), Y(0.55), "“I live in Dubai.”", "user", icon="User", shape="ellipse")
d.node("agent1", X(1.05), Y(0.55), "Agent", "harness", icon="Bot")
d.node("you2", X(0), Y(2.2), "“Weather at home\ntoday?”", "user", icon="User", shape="ellipse")
d.node("agent2", X(1.05), Y(2.2), "Agent", "harness", icon="Bot")
d.node("answer", X(1.0), Y(3.3), "“Sunny in Dubai, +31°C”", "ok", icon="CircleCheckBig")
d.node("session", X(2.15), Y(0.45), "Session “travel”", "memory", "the chat, on disk", icon="History")
d.node("memory", X(2.15), Y(1.6), "Memory", "memory", "user-lives-in-dubai.md\nhome-location-is-dubai.md",
       icon="Brain")
d.zone("RUN 1", ["you1", "agent1"], "app")
d.zone("RUN 2 · A NEW PROCESS", ["you2", "agent2", "answer"], "app")
d.arrow("you1", "agent1", step=1)
d.arrow("agent1", "session", "save the chat", dashed=True, color=KINDS["memory"][0], step=2)
d.arrow("agent1", "memory", "save the fact", color=KINDS["memory"][0], step=3)
d.arrow("you2", "agent2", step=4)
d.arrow("memory", "agent2", "recall", color=KINDS["memory"][0], step=5)
d.arrow("agent2", "answer", step=6)
d.code("code", CX, Y(0.55), """agent = create_harness(
    model=MAIN_MODEL,
    instructions=INSTRUCTIONS,
    builtin_tools=["web_fetch"],
    session={"id": "travel"},  # NEW: saved under .agent/sessions
    memory=True,  # NEW: notes saved as markdown under .agent/memory
    skills=False,
)""", title="labs/lab3_sessions_memory.py", highlight=[5, 6], size=14)
d.link("code", 5, "session", size=14)
d.link("code", 6, "memory", size=14)
run(d, "out", CX, Y(2.1), "labs/lab3_sessions_memory.py tell  …  ask", """Got it! I'll remember that you live in Dubai. 🇦🇪
── the program exits · a new one starts ──
Tool #1: web_fetch
It's sunny in Dubai today with +31°C! ☀️""")
d.table(CX, Y(3.35), [("", 120), ("Session", 220), ("Memory", 220)], [
    ["Keeps", "the conversation", "facts about you"],
    ["Recalled", "all of it", "only what's relevant"]], kind="memory")
done(d)

# LAB 4
d = lab("lab04-skills", "Lab 4 · Skills", "Know-how in a markdown file, loaded only when the task needs it.",
        "basics", 4, ["model", "builtin_tools", "session", "memory"], ["skills"])
d.node("you", X(0), Y(1.8), "“4 days in Istanbul.\nWhat should I pack?”", "user", icon="User", shape="ellipse")
d.node("agent", X(1.3), Y(1.8), "Agent", "harness", icon="Bot")
d.node("skills", X(1.25), Y(0.5), "skills tool", "tool", "loads packing-list", icon="BookOpenText")
d.node("llm", X(2.25), Y(1.8), "LLM", "llm", "follows the steps", icon="Sparkles")
d.code("file", X(2.1), Y(0.35), """---
name: packing-list
description: Build a packing list for a trip ...
---""", title=".agent/skills/packing-list/SKILL.md", size=14)
d.arrow("you", "agent", step=1)
d.arrow("agent", "skills", "needs it now", both=True, step=2, color=KINDS["tool"][0])
d.arrow("skills", "file", "reads", dashed=True, color=SOFT, step=3)
d.arrow("agent", "llm", both=True, step=4, color=KINDS["llm"][0])
d.zone("STRANDS HARNESS", ["agent", "skills"])
d.code("code", CX, Y(1.2), """agent = create_harness(
    model=MAIN_MODEL,
    instructions=INSTRUCTIONS,
    builtin_tools=["web_fetch"],
    session=False,
    memory=False,
    skills=True,  # NEW: loads .agent/skills/* on demand
)""", title="labs/lab4_skills.py", highlight=[7])
d.link("code", 7, "file", size=15)
run(d, "out", X(0), Y(3.1), "labs/lab4_skills.py", """Tool #1: web_fetch
Tool #2: skills
Istanbul: ☁️ +20°C — mild and partly cloudy
**Clothes** · **Toiletries** · **Documents** · **Tech** · **Weather extras** …""")
d.note(CX, Y(3.1), "Only the skill's name and one-line\ndescription sit in the prompt.\nThe rest loads when it's needed.")
done(d)

# LAB 5
d = lab("lab05-interventions", "Lab 5 · Interventions", "Put a checkpoint between the model and its tools.",
        "basics", 5, ["model", "builtin_tools", "session", "memory", "skills"], ["interventions"])
d.node("you", X(0), Y(0.55), "You", "user", icon="User", shape="ellipse")
d.node("agent", X(1.05), Y(0.55), "Agent", "harness", icon="Bot")
d.node("llm", X(2.1), Y(0.55), "LLM", "llm", "wants a tool", icon="Sparkles")
d.node("gate", X(0.95), Y(1.75), "before_tool_call", "harness", icon="ShieldCheck", shape="diamond", size=19)
d.node("hitl", X(0), Y(3.15), "Part A: a person", "user", "HumanInTheLoop asks in the\nterminal before each tool call", icon="Hand")
d.node("policy", X(1.95), Y(3.15), "Part B: a written rule", "app", "the LLM checks each call against\nyour rule; unsure ones come to you", icon="ScrollText")
d.node("decide", X(1.05), Y(4.3), "Proceed, or ask you", "ok", icon="CircleCheckBig")
d.arrow("you", "agent", step=1)
d.arrow("agent", "llm", both=True, step=2, color=KINDS["llm"][0])
d.arrow("agent", "gate", "tool call", step=3, color=KINDS["harness"][0])
d.arrow("gate", "hitl", step=4)
d.arrow("gate", "policy", step=4)
d.arrow("hitl", "decide", color=KINDS["s1"][0])
d.arrow("policy", "decide", color=KINDS["s1"][0])
d.code("code", CX, Y(0.55), """if sys.argv[1:] == ["policy"]:
    # Part B: a plain-English rule.
    interventions = resolve_interventions(
        "Reading and fetching are fine. Writing files is only fine under ./trips.",
        ask="stdio",
    )
else:
    # Part A: approve every tool call in the terminal.
    interventions = HumanInTheLoop(ask="stdio")

agent = create_harness(
    model=MAIN_MODEL,
    instructions=INSTRUCTIONS,
    builtin_tools=["web_fetch", "write"],
    session=False,
    memory=False,
    skills=True,
    interventions=interventions,  # NEW
)""", title="labs/lab5_interventions.py", highlight=[3, 4, 9, 18], size=14)
d.link("code", 9, "hitl", size=14)
d.link("code", 3, "policy", size=14)
done(d)

# LAB 6
d = lab("lab06-system1-basics", "Lab 6 · System 1 Basics (6a–6e)",
        "A small, fast model answers narrow questions with probabilities. Your code decides.", "s1", 6,
        ["model", "builtin_tools", "session", "memory", "skills", "interventions"], ["System 1"])
d.node("state", X(0), Y(0.55), "What the user said", "user", "“What's the weather?”", icon="MessageSquare")
d.node("s1", X(1.05), Y(0.55), "System 1", "s1", "one fast pass", icon="Zap", size=24)
d.node("py", X(1.0), Y(1.95), "P(named_city) < 0.5 ?", "app", icon="Code", shape="diamond", size=18)
d.node("ask", X(0), Y(3.25), "ask which city", "block", icon="Undo2")
d.node("go", X(2.05), Y(3.25), "go: weather", "ok", icon="CircleCheckBig")
d.arrow("state", "s1", step=1)
d.arrow("s1", "py", "probabilities", step=2, color=KINDS["s1"][0])
d.arrow("py", "ask", "yes", color=KINDS["block"][0], step=3)
d.arrow("py", "go", "no", color=KINDS["s1"][0])
d.code("code", CX, Y(0.55), """# 1. What happened. This is what Jev looks at.
conversation = \"\"\"user: What's the weather?
assistant wants to call: web_fetch(url="https://wttr.in/Seattle?format=3")\"\"\"

# 2. What we want to know. Three narrow questions, three kinds of answer.
questions = {
    "named_city": Noul(instructions="Did the user say which city they mean?"),  # yes/no
    "intent": Choice(instructions="What does the user want?", criteria={...}),  # pick one
    "urgency": Score(instructions="How urgent is the request?", criteria=[...]),  # rate
}

# 3. Ask. One call, three answers.
answers = jev.system_one(model="jev-latest", state=conversation, questions=questions).answers

# 4. Jev only observes. Plain Python decides.
if answers["named_city"].noul < 0.5:
    print("→ ask which city")""", title="labs/lab6a_jev.py (trimmed)", highlight=[7, 13, 16], size=14)
d.link("code", 16, "py", size=14)
d.bars(X(0), Y(4.2), "Jev on “What's the weather?”  (real run, labs/lab6a_jev.py)",
       [("Noul · city named?", 0.08, "block"), ("Choice · weather", 1.00, "s1"), ("Choice · itinerary", 0.00, "app"),
        ("Choice · packing", 0.00, "app"), ("Score · not urgent", 0.15, "app"), ("Score · today", 0.08, "app"),
        ("Score · right now", 0.77, "app")], vmax=1.0, width=300,
       note="Every option gets a probability, not just the winner.\n0.08 < 0.5, so plain Python says: ask which city.")
d.table(CX, Y(4.2), [("Lab", 70), ("System 1 model", 420)], [
    ["6a", "Jev: hosted by TypeSafe, via its SDK"], ["6b", "Kev: open, same SDK, a local URL"],
    ["6c", "Laya: open, BERT-based"], ["6d", "Qwen stand-in: one token + its logprobs"],
    ["6e", "one helper for all four (SYSTEM1_MODEL)"]], kind="s1", title="Same questions, five ways")
done(d)

# LAB 7
d = lab("lab07-tool-call-gate", "Lab 7 · Tool-Call Gate", "The LLM guessed Seattle. System 1 caught the guess before the tool ran.",
        "s1", 7, ["model", "builtin_tools", "session", "memory", "skills"], ["interventions", "System 1"])
d.node("you", X(0), Y(0.5), "“What's the weather?”", "user", icon="User", shape="ellipse")
d.node("agent", X(1.1), Y(0.5), "Agent", "harness", icon="Bot")
d.node("llm", X(2.1), Y(0.5), "LLM", "llm", "guesses wttr.in/Seattle", icon="Sparkles")
d.node("gate", X(1.0), Y(1.75), "Tool gate", "harness", icon="ShieldCheck", shape="diamond", size=21)
d.node("s1", X(2.15), Y(2.1), "System 1", "s1", "four questions", icon="Zap")
d.node("guide", X(0), Y(3.2), "Guide", "block", "“Ask the user instead\nof guessing”", icon="Undo2")
d.node("ask", X(0), Y(4.35), "“Which city?”", "user", icon="Bot", shape="ellipse")
d.arrow("you", "agent", step=1)
d.arrow("agent", "llm", both=True, step=2, color=KINDS["llm"][0])
d.arrow("agent", "gate", "tool call", step=3, color=KINDS["harness"][0])
d.arrow("gate", "s1", both=True, color=KINDS["s1"][0], step=4)
d.arrow("gate", "guide", "a guess", color=KINDS["block"][0], step=5)
d.arrow("guide", "ask", color=KINDS["block"][0])
d.bars(X(1.0), Y(3.1), "System 1 on web_fetch(wttr.in/Seattle)\n(real run, Kev-4B)",
       [("helps answer?", 0.84, "s1"), ("information missing?", 0.35, "s1"),
        ("same city as the user?", 0.08, "block"), ("too early?", 0.41, "s1")], vmax=1.0, width=260,
       threshold=(0.65, "YES = 0.65"), note="The user never named a city → Guide.\nFor Paris the same question scores 0.96 → Proceed.")
d.code("code", CX, Y(0.5), """agent = create_harness(
    model=MAIN_MODEL,
    instructions=INSTRUCTIONS,
    builtin_tools=["web_fetch"],
    session=False,
    memory=False,
    skills=False,
    interventions=ToolCallGate(),  # NEW: our own System 1 gate
)""", title="labs/lab7_tool_call_gate.py", highlight=[8], size=14)
d.link("code", 8, "gate", size=14)
run(d, "out", CX, Y(2.2), "labs/lab7_tool_call_gate.py", """you: What's the weather?
  gate · the model wants to run: web_fetch({"url": "https://wttr.in/Seattle?format=3"})
    helps answer?           0.84  ✓
    information missing?    0.35  ✓
    same city as the user?  0.08  ✗
    too early?              0.41  ✓
  gate → Guide (1/3): ask the user instead of guessing
Which city would you like the weather for?

you: What's the weather in Paris?
  gate · the model wants to run: web_fetch({"url": "https://wttr.in/Paris?format=3"})
    helps answer?           0.96  ✓
    information missing?    0.27  ✓
    same city as the user?  0.96  ✓
    too early?              0.16  ✓
  gate → Proceed: the tool runs
The weather in Paris is ☁️ cloudy with a temperature of +24°C.""")
done(d)

# LAB 8
d = lab("lab08-completion-check", "Lab 8 · Completion Check",
        "The LLM answered half the question. System 1 sent it back to finish.", "s1", 8,
        ["model", "builtin_tools", "session", "memory", "skills"], ["interventions", "System 1"])
d.node("you", X(0), Y(0.5), "“Weather in Istanbul,\nand what to pack?”", "user", icon="User", shape="ellipse", size=19)
d.node("agent", X(1.15), Y(0.5), "Agent", "harness", icon="Bot")
d.node("llm", X(2.15), Y(0.5), "LLM", "llm", "draft: weather only", icon="Sparkles")
d.node("check", X(1.02), Y(1.75), "Completion check", "harness", icon="CircleCheckBig", shape="diamond", size=19)
d.node("s1", X(2.4), Y(2.1), "System 1", "s1", "waiting for you?\nanswered everything?", icon="Zap")
d.node("guide", X(0), Y(3.25), "Guide", "block", "“Your answer skipped part\nof the request”", icon="Undo2")
d.arrow("you", "agent", step=1)
d.arrow("agent", "llm", both=True, step=2, color=KINDS["llm"][0])
d.arrow("agent", "check", "draft", step=3, color=KINDS["harness"][0])
d.arrow("check", "s1", both=True, color=KINDS["s1"][0], step=4)
d.arrow("check", "guide", "a no", color=KINDS["block"][0], step=5)
d.arrow("guide", "agent", "try again", dashed=True, color=KINDS["block"][0], bend=-140)
d.bars(X(1.1), Y(3.2), "P(answered everything)  (real run, Kev-4B)",
       [("draft 1: weather only", 0.02, "block"), ("draft 2: weather + list", 0.87, "s1")], vmax=1.0,
       width=260, threshold=(0.6, "pass = 0.6"), note="A reply that asks the user a question\n(“which city?”) isn't judged.")
d.code("code", CX, Y(0.5), """agent = create_harness(
    model=MAIN_MODEL,
    instructions=INSTRUCTIONS,
    builtin_tools=["web_fetch"],
    session=False,
    memory=False,
    skills=False,
    interventions=CompletionCheck(),  # NEW
)""", title="labs/lab8_completion_check.py", highlight=[8], size=14)
d.link("code", 8, "check", size=14)
run(d, "out", CX, Y(2.2), "labs/lab8_completion_check.py", """System 1: Kev
you: What's the weather in Istanbul, and what should I pack for 4 days there?

  check · the model's draft: "The weather in Istanbul is cloudy with a temperature of 20°C. For 4 days, …"
    waiting for you?      0.11  ✓
    answered everything?  0.85  ✓
  check → Proceed: the answer goes to the user

assistant: The weather in Istanbul is cloudy with a temperature of 20°C.
For 4 days, here's what I'd recommend packing:
- Light layers – a mix of t-shirts, light long-sleeves, and a sweater …""")
done(d)

# LAB 9
d = lab("lab09-model-switching", "Lab 9 · Model Switching",
        "Quick questions go to a small model, big plans to a big one. System 1 judges, Python picks.", "s1", 9,
        ["model", "builtin_tools", "session", "memory", "skills", "interventions", "System 1"], ["ModelRouter"])
d.node("you", X(0), Y(1.05), "a message", "user", icon="MessageSquare", shape="ellipse")
d.node("router", X(0.95), Y(0.95), "ModelRouter", "harness", icon="Split", shape="diamond")
d.node("s1", X(0.95), Y(2.4), "System 1", "s1", "quick factual question?", icon="Zap")
d.node("small", X(2.6), Y(0.2), "Kimi K2.5", "llm", "small: fast, cheap", icon="Sparkles")
d.node("big", X(2.6), Y(1.9), "Kimi K3", "llm", "big: planning", icon="Sparkles")
d.arrow("you", "router", step=1)
d.arrow("router", "s1", "P(quick)", both=True, color=KINDS["s1"][0], step=2)
d.arrow("router", "small", "P ≥ 0.5", color=KINDS["llm"][0], step=3)
d.arrow("router", "big", "P < 0.5", color=KINDS["llm"][0], step=3)
d.code("code", CX, Y(0.5), """router = ModelRouter(
    [
        RoutingCandidate(model=build_model(SMALL_MODEL), name="small"),  # Kimi K2.5
        RoutingCandidate(model=build_model(BIG_MODEL), name="big"),  # Kimi K3
    ],
    strategy=System1Strategy(),
)
agent = create_harness(
    model=router,  # NEW: a router instead of one model
    instructions=INSTRUCTIONS,
    builtin_tools=["web_fetch"],
    session=False,
    memory=False,
    skills=False,
)""", title="labs/lab9_model_switching.py", highlight=[6, 9], size=14)
d.link("code", 9, "router", size=14)
run(d, "out", CX, Y(3.0), "labs/lab9_model_switching.py", """you: What's the weather in Paris?
  router · which model should answer this?
    quick question?  0.82
  router → small: bedrock/moonshotai.kimi-k2.5
The current weather in Paris is **cloudy ☁️** with a temperature of **24°C**.

you: Plan a 5-day Istanbul itinerary under $1000, with a day trip and where to stay.
  router · which model should answer this?
    quick question?  0.15
  router → big: bedrock/us.moonshotai.kimi-k3
# 5-Day Istanbul Itinerary … (trimmed)""")
done(d)

# LAB 10
d = lab("lab10-system1-showdown", "Lab 10 · System 1 Showdown",
        "Measure a classifier before you trust it. Lower Brier score is better.", "s1", 10,
        ["model", "builtin_tools", "session", "memory", "skills", "interventions", "System 1", "ModelRouter"], [])
results = [("Beach destinations (44)", [("Jev", 0.048, 95), ("Kev-4B", 0.032, 98), ("Qwen", 0.023, 98)]),
           ("Tool calls, abstract (12)", [("Jev", 0.028, 100), ("Kev-4B", 0.098, 83), ("Qwen", 0.341, 58)]),
           ("Tool calls, concrete (12)", [("Jev", 0.001, 100), ("Kev-4B", 0.015, 100), ("Qwen", 0.069, 83)])]
for i, (title, rows) in enumerate(results):
    d.bars(100 + i * 560, 300, title, [(n, b, "block" if b > 0.25 else "s1") for n, b, _ in rows], vmax=0.36,
           width=280, fmt="{:.3f}", threshold=(0.25, "coin flip"))
d.table(100, 680, [("Question set", 260), ("Jev (hosted)", 190), ("Kev-4B (open)", 190), ("Qwen stand-in", 190)],
        [[t] + [f"Brier {b:.3f} · {a}%" for _, b, a in rows] for t, rows in results], kind="s1",
        title="Measured on this machine, September 2026 (Laya wasn't installed for this run)")
d.code("code", 100, 980, """for title, labels, question in ROUNDS:
    for name, ask in players:
        probs = {state: ask(state, question) for state in labels}
        brier, accuracy = score(probs, labels)""", title="labs/lab10_system1_showdown.py (trimmed)", highlight=[4], size=14)
d.note(1100, 960, "The stand-in is fine on simple questions\nand falls apart on the abstract one.\nConcrete questions win. Measure before\nyou trust a classifier.")
done(d)

# LAB 10b
d = lab("lab10b-finetune-laya", "Lab 10b · Fine-tune Laya",
        "Laya isn't great out of the box. A few minutes of training on your laptop fixes that.", "s1", "10b",
        ["model", "builtin_tools", "session", "memory", "skills", "interventions", "System 1", "ModelRouter"], [])
d.node("data", X(0), Y(0.5), "1,955 travel questions", "app", "new places · new tool calls\nlab 10 + lab 7 questions", icon="ListChecks")
d.node("kev", X(1.05), Y(0.5), "Kev (teacher)", "s1", "slow, good: labels them\n~3 min", icon="Zap")
d.node("train", X(2.1), Y(0.5), "Train Laya", "harness", "your laptop's GPU\n~6 min · 14.1 GB", icon="Cpu")
d.node("laya", X(2.1), Y(1.75), "Laya (fine-tuned)", "s1", "fast: ~18 ms a question", icon="Zap")
d.arrow("data", "kev", step=1)
d.arrow("kev", "train", "probabilities", step=2, color=KINDS["s1"][0])
d.arrow("train", "laya", step=3, color=KINDS["harness"][0])
d.bars(X(0), Y(1.6), "Brier on lab 10's held-out questions (real run)",
       [("beach · base", 0.137, "app"), ("beach · fine-tuned", 0.079, "s1"),
        ("abstract · base", 0.240, "app"), ("abstract · fine-tuned", 0.103, "s1"),
        ("concrete · base", 0.230, "app"), ("concrete · fine-tuned", 0.015, "s1")], vmax=0.3, width=260,
       fmt="{:.3f}", threshold=(0.25, "coin flip"), note="Kev, the teacher: 0.032 · 0.098 · 0.015")
d.code("code", CX, Y(0.5), """# 1. Travel questions that share nothing with lab 10
pairs = training_questions()
# 2. The teacher labels them (its probability, not just yes/no)
rows = label(pairs, TEACHER, OUT / "labels.json")
# 3. Laya learns to give the teacher's probabilities
stats = laya_train.train(rows, OUT, EPOCHS, device)
# 4. Before and after, on lab 10's questions
showdown([("laya (base)", base), ("laya (fine-tuned)", fine)])""", title="labs/lab10b_finetune_laya.py (trimmed)",
       highlight=[4, 6], size=14)
d.note(CX, Y(2.6), "Recipe: Laya's own notebook (docs/reference/laya).\nMeasured on an Apple M4 Max.\n24 GB+ Apple Silicon or a 16 GB+ NVIDIA GPU\nshould work; CPU is slow.")
done(d)

# LAB 11 (standalone: nothing here refers to the other labs)
d = Diagram("lab11-harness-app")
d.header("Lab 11 · The Harness App", None, "app", "11 of 11")
d.idea("One harness behind a real app. System 1 checks memory, tools and answers.")
APP = ["model", "tools", "builtin_tools", "session", "memory", "skills", "builtin_plugins", "mcp_servers",
       "interventions", "System 1"]
d.strip(CX, 36, APP, APP, [], title="WHAT'S INSIDE")
d.node("you", X(0), Y(1.4), "You", "user", "chat in the browser", icon="User", shape="ellipse")
d.node("server", X(0.95), Y(1.4), "App server", "app", "FastAPI, streams events", icon="Server")
d.node("agent", X(2.05), Y(1.4), "Agent", "harness", "orchestrates every step", icon="Bot", size=23)
d.node("s1", X(2.0), Y(0.2), "System 1", "s1", "① which notes? ② allow the tool?\n③ is the answer complete?", icon="Zap")
d.node("llm", X(3.65), Y(1.4), "LLM", "llm", "Kimi K2.5 on Bedrock", icon="Sparkles")
d.node("session", X(1.72), Y(3.0), "Session", "memory", "chat history", icon="History", w=200)
d.node("memory", X(2.3), Y(3.0), "Memory", "memory", "notes + embeddings", icon="Brain", w=220)
d.node("skills", X(2.93), Y(3.0), "Skills", "memory", "SKILL.md", icon="BookOpenText", w=180)
d.node("tools", X(3.65), Y(3.0), "Tools", "tool", "web_fetch · read · MCP", icon="Wrench")
d.node("kb", X(2.3), Y(4.65), "Knowledge bases", "code", "your markdown, read-only", icon="LibraryBig")
d.arrow("you", "server", both=True)
d.arrow("server", "agent", both=True)
d.arrow("agent", "s1", both=True, color=KINDS["s1"][0], width=3)
d.arrow("agent", "llm", both=True, color=KINDS["llm"][0])
d.arrow("agent", "session", both=True, color=KINDS["memory"][0])
d.arrow("agent", "memory", "recall · save", both=True, color=KINDS["memory"][0])
d.arrow("agent", "skills", both=True, color=KINDS["memory"][0])
d.arrow("agent", "tools", both=True, color=KINDS["tool"][0])
d.arrow("memory", "kb", "retrieve, then\nSystem 1 reranks", dashed=True, color=SOFT)
d.zone("STRANDS HARNESS", ["agent", "session", "memory", "skills"])
d.code("code", X(4.55), Y(0.7), """agent = create_harness(
    model=settings["model"],
    instructions=INSTRUCTIONS,
    tools=[forget_tool(turn, notes)],
    builtin_tools=["web_fetch", "read"],
    session={"id": chat_id, "dir": str(data / "sessions")},
    memory={"stores": [store, *knowledge_for(turn, data)]},
    skills=True,
    builtin_plugins=["todos"],
    mcp_servers=mcp or None,
    interventions=[turn.gate, turn.check],
    callback_handler=None,
)""", title="lab11/server/agents.py", highlight=[4, 6, 7, 10, 11], size=14)
d.bars(X(0), Y(3.15), "Recall: embeddings + System 1 rerank\n(30 notes, 10 questions, Qwen stand-in)",
       [("right notes found, all notes", 17, "app"), ("right notes found, rerank", 20, "s1"),
        ("System 1 calls ÷ 10, all notes", 30, "app"), ("System 1 calls ÷ 10, rerank", 10, "s1")],
       vmax=32, width=150, fmt="{:.0f}")
done(d)

print(f"\n{problems} layout problem(s) in total")
sys.exit(1 if problems else 0)
