# Video script: Strands Harness Labs

One episode per lab, plus an intro. Each episode follows the same shape so the series feels like one build:

1. **Cold open**: the problem, in one sentence, from the travel assistant's point of view.
2. **Diagram**: the lab's picture from `docs/diagrams/`.
3. **Code**: the one new idea (the line marked `# NEW` in the lab file).
4. **Run it**: the scripted demo, pausing on each `press Enter` prompt to explain the screen.
5. **Wrap**: what we added, and what breaks next (the hook into the following lab).

Conventions in this script:

- **SAY** is narration. Read it as written or put it in your own words.
- **SHOW** is what's on screen: a diagram, a file or a terminal.
- **RUN** is a command, typed on camera.
- Timings are rough targets for the finished cut.

The labs' `press Enter` pauses exist for recording. Every System 1 lab stops before it asks the classifier, so
you can explain what's on screen first. Take your time at each one.

---

## Before any recording session

```bash
uv sync
cp .env.example .env        # once; check MAIN_MODEL and SYSTEM1_MODEL
ollama serve                # in another terminal, if it isn't running
ollama pull qwen3.5:4b
./reset.sh                  # clears sessions, memory and trips/ so the take starts fresh
```

- Terminal: large font, dark theme, about 110 columns wide. The bars in labs 6–10 are 20 cells and the lab 10
  table needs the width.
- Warm up Ollama with one throwaway run of lab 6d. The first System 1 call is slow while Ollama loads the model.
- Close anything that shows AWS account IDs or keys. Don't `cat .env` on camera.
- LLM output changes from run to run. Record the demo twice and keep the better take rather than scripting
  exact wording.

---

## Episode 0: Intro, what a harness is (4–5 min)

**SHOW** `docs/diagrams/00a-what-is-a-harness.png`

**SAY** A model on its own takes a prompt and returns text. An agent puts that model in a loop: call a tool, read
the result, call the model again. A harness is everything around that loop that makes it dependable: sessions,
memory, skills, interventions, built-in tools, MCP servers, a sandbox. LangChain moved its agent from outside the
top 30 to the top 5 on Terminal Bench by changing only the harness, with the same model.

**SHOW** `docs/diagrams/00b-strands-harness.png`

**SAY** The Strands harness gives you all of that in one call, `create_harness`. It's open source:
`pip install strands-harness`.

**SHOW** `docs/diagrams/00c-harness-landscape.png`

**SAY** Every ecosystem now has a library you run and a service that runs it for you. On AWS that's the Strands
harness and the AgentCore harness. On LangChain it's Deep Agents and Managed Deep Agents. From Anthropic, the Claude
Agent SDK and Claude Managed Agents. Pick by where you want it to run, then by which models you need. We use the
Strands harness because it runs in your own process with any model, so we can plug System 1 into its interventions.

**SHOW** `docs/diagrams/00d-system1-vs-llm.png`

**SAY** The second half of the series adds a System 1 model. An LLM writes text. A System 1 model answers narrow,
typed questions (yes or no, pick one, rate) in a single fast pass and returns probabilities. It never decides.
Plain Python reads the probabilities and decides. We use it to watch the agent: to catch a guessed tool call, a
half answer, or a request that deserves a bigger model.

**SHOW** `docs/diagrams/00e-lab-map.png`

**SAY** We build one travel assistant, one idea per lab. Labs 1 to 5 are harness basics. Labs 6 to 10 let System 1
check the work. Lab 11 puts it all in a web app. Each lab is one short file, and lab N adds exactly one thing to
lab N-1, so a diff shows you what's new.

**SHOW** the README Quick Start. **RUN** `uv sync` (already done; show it finishing).

**SAY** You need uv, Ollama for the System 1 labs, and AWS credentials for Bedrock. The agent runs on Kimi K2.5 by
default. One line in `.env` swaps it for Nemotron, Claude, Kimi K3, or `ollama/gpt-oss:20b` if you want everything
local and free.

---

## Episode 1: Your first harness (3–4 min)

**Cold open. SAY** Let's get a working agent with one function call.

**SHOW** `docs/diagrams/lab01-first-harness.png`, then `labs/lab1_first_harness.py`.

**SAY** Two agents side by side. At the top, the old way: a plain Strands `Agent` you assemble yourself. Below, the
harness way: `create_harness(model=..., instructions=...)`. The harness turns on tools, sessions, memory and
skills by default. We switch them all off here with `builtin_tools=[]`, `session=False`, `memory=False` and
`skills=False`, and each later lab turns exactly one back on.

**RUN** `uv run labs/lab1_first_harness.py`

**SAY** (as the output appears) The hand-built agent's tool list, then the harness agent: an ordinary Strands
`Agent`, running on the model from `.env`. It suggests a city break from Dubai.

**SAY** Every agent lab has a `--chat` flag if you'd rather talk to it than watch the demo.

**Wrap. SAY** It can talk, but ask it about today's weather and it can only guess. Next: tools.

---

## Episode 2: Built-in tools (3 min)

**Cold open. SAY** Our assistant can't see the outside world. Let's give it the real forecast without writing a
tool.

**SHOW** `docs/diagrams/lab02-builtin-tools.png`, then `labs/lab2_builtin_tools.py`.

**SAY** One line changes: `builtin_tools=["web_fetch", "read", "write"]`. We pin exactly the tools we want. The
instructions tell it where the weather lives: `wttr.in/<city>?format=3`. We don't write any tool code.

**RUN** `uv run labs/lab2_builtin_tools.py`

**SAY** First it prints the tools the agent can use. Then watch the tool call: it fetches `wttr.in/Istanbul` and
answers with the real forecast.

**Wrap. SAY** Close the terminal and it forgets everything, including where you live. Next: sessions and memory.

---

## Episode 3: Sessions & memory (4 min)

**Before the take: RUN** `./reset.sh`. Otherwise it already remembers you from a rehearsal.

**Cold open. SAY** Tell it where you live once, and a brand-new process should still know.

**SHOW** `docs/diagrams/lab03-sessions-memory.png`, then `labs/lab3_sessions_memory.py`.

**SAY** Two new lines. `session={"id": "travel"}` saves the conversation under `.agent/sessions/travel`.
`memory=True` saves long-term notes as markdown under `.agent/memory`. The instructions tell it to save lasting
personal facts.

**RUN** `uv run labs/lab3_sessions_memory.py tell`

**SAY** "By the way, I live in Dubai." It saves that.

**SHOW** the new files: `ls .agent/memory` and open the note. It's plain markdown you can read and edit.

**RUN** `uv run labs/lab3_sessions_memory.py ask`

**SAY** A fresh process with nothing in RAM. "What's the weather like at home today?" It knows home is Dubai and
fetches the forecast.

**Wrap. SAY** It remembers facts. Next we teach it a repeatable task, and we do it in markdown.

---

## Episode 4: Skills (3–4 min)

**Cold open. SAY** A packing list should come out the same shape every time. We'll teach that with a markdown
file, not code.

**SHOW** `docs/diagrams/lab04-skills.png`, then `.agent/skills/packing-list/SKILL.md`.

**SAY** A skill is a folder with a `SKILL.md`: a name, a one-line description, and the steps. Get the forecast.
Five sections in order: Clothes, Toiletries, Documents, Tech, Weather extras. Three to six items each, with the
forecast at the top.

**SHOW** `labs/lab4_skills.py`. **SAY** One new line: `skills=True`. The harness lists the skills' descriptions,
and the agent loads the full skill only when a request needs it.

**RUN** `uv run labs/lab4_skills.py`

**SAY** "I'm going to Istanbul next week for 4 days. What should I pack?" Watch it load the skill, fetch the
forecast, then write the list in exactly those five sections.

**Wrap. SAY** Now we'd like it to save that list to a file. An agent that writes files should ask first. Next:
interventions.

---

## Episode 5: Interventions (5 min)

**Cold open. SAY** Before the agent writes to disk, we want a checkpoint.

**SHOW** `docs/diagrams/lab05-interventions.png`, then `labs/lab5_interventions.py`.

**SAY** An intervention runs before a tool call and decides whether it happens. Part A uses the vended one,
`HumanInTheLoop(ask="stdio")`, which asks you in the terminal about every call. We also add the `write` tool and
tell the agent to save lists under `trips/`.

**RUN** `uv run labs/lab5_interventions.py`

**SAY** (at each prompt) It wants to fetch the forecast, so approve it. It wants to write
`trips/istanbul-packing-list.md`, so approve that too. **SHOW** the saved file.

**SAY** That works, but approving every call gets old fast. Part B swaps the prompts for a plain-English rule.

**SHOW** the `policy` branch: `resolve_interventions("Reading and fetching are fine. Writing files is only fine under ./trips.", ask="stdio")`.

**RUN** `uv run labs/lab5_interventions.py policy`

**SAY** Now a classifier reads the rule and decides which calls need you. Fetching goes straight through. The write
into `./trips` is allowed by the rule too.

**Wrap. SAY** That policy classifier is a taste of the next idea. From here on we build our own checks with a
System 1 model: small, fast, and it gives probabilities instead of text.

---

## Episode 6: System 1 basics (8–10 min, or split into 6a–c and 6d–e)

**Cold open. SAY** What if a tiny, fast model could answer "did the user say which city?" with a probability, and
our code made the call?

**SHOW** `docs/diagrams/lab06-system1-basics.png`, then the top of `labs/lab6a_jev.py`.

**SAY** Every lab 6 file reads as the same four steps. One, the conversation: what the user said and what the
assistant wants to do next. Here the user asks "What's the weather?" and the assistant wants to fetch Seattle.
Two, the questions, three shapes: `Noul` for yes or no, `Choice` to pick one, `Score` to rate. Three, one call
answers all three. Four, plain Python decides: if P(the user named a city) is under 0.5, ask which city.

### 6a: Jev (needs `TYPESAFE_API_KEY`)

**RUN** `uv run labs/lab6a_jev.py`

**SAY** (at the first conversation, before pressing Enter) No city, and a Seattle guess. Press Enter. **SHOW** the
bars. P(yes) is low and red, so it asks which city. Intent: weather wins. Urgency comes back as a probability per
level and a score.

**SAY** Three more conversations: Paris (a real city, so it goes), a packing request, and a vague trip idea.
Jev gets all four right.

### 6b: Kev

**SAY** Kev is an open Jev-alike on your own machine. Same SDK, same questions. Only the client changes.

**SHOW** the one changed line: `TypeSafeClient(base_url=KEV_URL, api_key="local")`.

**RUN** `uv run labs/lab6b_kev.py` (it offers to start Kev; `./kev.sh start` beforehand saves waiting on camera)

**SAY** Kev also gets all four right. Kev-4B needs a 32 GB Mac. On a smaller machine, use `kev-0.8b`.

### 6c: Laya

**SAY** Laya is a different family, BERT-based, and very fast. Same question shapes, written as plain dicts.

**RUN** `uv run labs/lab6c_laya.py` (after `uv sync --extra laya --inexact`)

**SAY** It misses some. Remember that; lab 10 measures it, and lab 10b fixes it.

### 6d: Qwen stand-in

**SAY** No System 1 model? A small chat model can stand in. Ask it for exactly one token, `num_predict: 1`, with
`logprobs` on, then add up every spelling of "yes" and of "no".

**RUN** `uv run labs/lab6d_qwen_stand_in.py`

**SAY** (point at the top-guesses list) This is the raw material: its top candidate tokens and how likely each
was. From that we get P(yes). It's free, local and about 0.1 s a question, but it isn't trained to be calibrated,
and it misses some too.

### 6e: One helper for all four

**SHOW** `labs/lab6e_standardized.py`. **SAY** Labs 7–9 don't care which model answers. Two helpers, `yes_no` and
`choice`, send the same questions to whichever model `SYSTEM1_MODEL` names.

**RUN** `uv run labs/lab6e_standardized.py`, then `SYSTEM1_MODEL=kev uv run labs/lab6e_standardized.py`

**Wrap. SAY** System 1 observes, Python decides. Now let's put that inside the agent's loop.

---

## Episode 7: Tool-call gate (6–7 min)

**Cold open. SAY** "What's the weather?" No city. A careless agent guesses one. Let's catch that before the tool
runs.

**SHOW** `docs/diagrams/lab07-tool-call-gate.png`, then `labs/lab7_tool_call_gate.py`.

**SAY** First, be honest about the setup. Good models usually ask when the city is missing, so we plant a failure:
the instructions say "if no city is given, assume Seattle". Never ship this. It's here so the gate has something to
catch.

**SAY** The gate is a custom `InterventionHandler`. The harness calls `before_tool_call` every time the model wants
to run a tool, and the tool only runs if we return `Proceed`. We ask System 1 four yes/no questions in one call:
does the call help answer the request, is information missing, did the user mention the same city the tool
uses, is it too early.

**SAY** (point at `user_text`) System 1 only sees what the *user* said. The model's own "I'll assume Seattle" must
not count as grounding.

**SAY** (point at the comments on `QUESTIONS`) Concrete beats abstract. Lab 10 measured it: "are the arguments
based on facts the user provided?" scored worse than a coin flip on the Qwen stand-in, and "same city?" scored
0.07.

**SAY** Then plain Python decides, with 0.65 as the threshold. Any broken rule returns `Guide`: the tool doesn't
run, and the model reads our feedback and tries again. After three blocks it returns `Deny`, so a stubborn model
can't loop forever.

**RUN** `uv run labs/lab7_tool_call_gate.py`

**SAY** (at `gate · the model wants to run: web_fetch(...Seattle...)`, before Enter) There's the guess. Press Enter.
**SHOW** the checklist: "same city as the user?" is low, so a red cross. `gate → Guide`. The model reads the
feedback and asks you which city instead.

**SAY** Second question: "What's the weather in Paris?" Every rule passes, so a green tick on each.
`gate → Proceed`, and the tool runs.

**Wrap. SAY** We check calls before they run. What about answers that stop halfway? Next: a completion check.

---

## Episode 8: Completion check (5–6 min)

**Cold open. SAY** Ask two things and get one answer back. We'll send the agent back to finish.

**SHOW** `docs/diagrams/lab08-completion-check.png`, then `labs/lab8_completion_check.py`.

**SAY** Another planted failure: a lazy assistant told to answer only the first thing and stop. This time the hook
is `after_model_call`. It runs when the model finishes a reply, before the reply is accepted.

**SAY** Two questions. Is the assistant asking the user for something it needs? If so, that's a fine way to end a
turn, and there's nothing to judge. Otherwise, does the answer respond to every question? `Proceed` accepts the
draft. `Guide` throws it away and the model tries again, at most twice.

**SAY** One more detail: `callback_handler=None`. This lab doesn't stream, so you see the draft being judged and the
answer only once it passes.

**RUN** `uv run labs/lab8_completion_check.py`

**SAY** "Weather in Istanbul, and what to pack for 4 days?" (at `check · the model's draft`) The draft gives the
weather and stops. Press Enter. "Answered everything?" is low. `check → Guide (1/2)`. The next draft covers both
parts, so `Proceed`, and now the answer prints.

**Optional beat. RUN** `--chat` and type "What's the weather?". **SAY** It asks which city, and the check prints
`Proceed: it asked you a question, nothing to judge`.

**Wrap. SAY** System 1 has checked tool calls and answers. Last job: picking which model answers at all.

---

## Episode 9: Model switching (4–5 min)

**Cold open. SAY** A weather question doesn't need the expensive model. A five-day itinerary might.

**SHOW** `docs/diagrams/lab09-model-switching.png`, then `labs/lab9_model_switching.py`.

**SAY** Instead of one model, we pass a `ModelRouter` with two candidates: `small` (Kimi K2.5) and `big` (Kimi K3).
Our strategy's `select()` runs once per message. System 1 answers one question, "is this a quick factual
question?", and at 0.5 or above the small model answers. It then handles the whole reply, tool calls included.

**RUN** `uv run labs/lab9_model_switching.py`

**SAY** "What's the weather in Paris?" Quick, so `router → small`. "Plan a 5-day Istanbul itinerary under $1000..."
Not quick, so `router → big`.

**Wrap. SAY** We've used System 1 three ways. But how good are these classifiers, really? Let's measure them.

---

## Episode 10: System 1 showdown (6–7 min)

**Cold open. SAY** Jev, Kev, Laya and our Qwen stand-in, on questions where we know the right answer.

**SHOW** `docs/diagrams/lab10-system1-showdown.png`, then the comment at the top of
`labs/lab10_system1_showdown.py`.

**SAY** The score is the Brier score. For each example, take the probability the model gave, subtract the true
answer (1 or 0), square it, and average. Zero is perfect. 0.25 is a coin flip, what you'd get by always saying 0.5.
Unlike accuracy, it punishes being confidently wrong, and our code acts on thresholds like 0.65, so that matters.

**RUN** `uv run labs/lab10_system1_showdown.py`

**SAY** Contenders you haven't set up are skipped, each with a one-line hint. Three rounds, with Enter before each:

1. **Beach destinations** (44 places). Includes the hard middle: coastal cities like Barcelona and Sydney that
   aren't beach trips.
2. **Tool calls, abstract question**: "are the argument values based on facts the user provided?"
3. **Tool calls, concrete question**: "did the user mention the same city the tool call uses?" These are the same
   tool calls, asked a different way.

**SAY** (on each table) Shorter bars are better, and the line is the coin flip. Read the verdict under each round.
The lesson of rounds 2 and 3: small models need concrete questions. That's why lab 7 asks "same city?".

**Wrap. SAY** Laya is the fastest here and the weakest out of the box. Its own docs call it a base to specialise.
So let's specialise it.

---

## Episode 10b: Fine-tune Laya (6–8 min, cut the training wait)

**Cold open. SAY** Kev is good but slow. Laya is fast but weak. Can Laya learn from Kev?

**SHOW** `docs/diagrams/lab10b-finetune-laya.png`

**SAY** That's distillation. Kev labels a couple of thousand travel questions, and we keep its *probability*, not
just yes or no. Laya learns to give the same probabilities. Then we re-run lab 10's rounds on questions it never
trained on: new places, new cities.

**RUN** `uv run labs/lab10b_finetune_laya.py` (add `--repo-labels` to skip live labelling and use
`data/lab10b-labels.json`)

**SAY** Step 1, the training questions, with three examples on screen. Step 2, the labels, with Kev's probability
drawn as a bar. Step 3, training. **CUT** the wait (about 6 minutes on an M4 Max). Step 4, before and after.

**SAY** (on the results; your numbers will land close to these, not exactly on them) Concrete tool calls went from
0.230 to about 0.012, as good as the teacher. Beach and abstract tool calls improve a lot too. Laya stays at 15–25
ms a question.

**SAY** With `SYSTEM1_MODEL=laya-travel`, lab 7's gate now blocks the guessed Seattle and lets Paris through.

**Optional beat. RUN** `SYSTEM1_MODEL=laya-travel uv run labs/lab7_tool_call_gate.py`

**Wrap. SAY** Train on your own domain. Now let's put everything in one app.

---

## Episode 11: The Harness App (8–10 min)

**Before the take:** clear old chats (`./cleanup.sh` offers to remove `lab11/data`), then **RUN**
`./lab11/start.sh`. It checks Ollama, pulls `nomic-embed-text` once, installs everything and opens the browser.

**SHOW** `docs/diagrams/lab11-harness-app.png`

**SAY** The finished travel assistant as a web app: a FastAPI server around the same harness, and a React UI that
only reads a stream of JSON events.

**Beats, in the browser:**

1. **Chat.** Ask "What should I pack for 4 days in Istanbul?" Point at the tool card, the skill loading, and the
   System 1 decision chips: the tool gate and the completion check from labs 7 and 8.
2. **Inside the harness** panel: the tools, skills, session, connectors, and every System 1 decision with its bars.
3. **Model pickers.** Switch the LLM mid-chat, and the history carries over. Switch System 1 between Qwen, Jev, Kev
   and Laya.
4. **Memory.** Say "I live in Dubai," then open the memory core. The new note arrives in violet. In a new chat, ask
   about the weather at home. The recalled note fires green, and hovering the chip shows what was searched and each
   note's score.
   **SAY** Recall is retrieve-then-rerank: an embedding model finds the 12 closest notes, then System 1 asks "would
   this fact help answer the message?" for each, and keeps the best 5 at 0.5 or above.
5. **Forget.** Say "forget where I live." The note goes, and that turn saves no new notes.
6. **Attach a file** and ask about it. The agent reads it with the built-in `read` tool.
7. **Connectors.** Turn on the AWS Documentation MCP server and ask it something.
8. **Skills tab.** Show the packing-list skill, and add one from a `SKILL.md`.
9. **How it works.** Click through one turn step by step: session, memory, skills, System 1, the LLM, tools.
10. **Restart** the app. The chat history is still there, because every chat is a harness session on disk.

**Wrap. SAY** Everything from labs 1 to 10 in one place: one `create_harness` call with sessions, memory, skills,
MCP servers and two System 1 interventions. The UI only reads events, so any web framework can replace it.

---

## Series outro (1 min)

**SHOW** `docs/diagrams/00e-lab-map.png`

**SAY** A harness makes an agent dependable: tools, sessions, memory, skills and interventions, each one line. A
System 1 model watches the loop and answers narrow questions with probabilities, and plain Python decides. Write
the questions concretely, measure them, and train on your own domain. The code is in the repo, and each lab is one
short file.

**After recording: RUN** `./reset.sh` (or `./cleanup.sh` to free disk space).
