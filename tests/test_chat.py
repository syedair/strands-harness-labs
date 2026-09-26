from common.chat import chat


class FakeAgent:
    def __init__(self):
        self.prompts = []

    def __call__(self, prompt):
        self.prompts.append(prompt)


def answers(*lines):
    it = iter(lines)

    def fake_input(prompt):
        try:
            return next(it)
        except StopIteration:
            raise EOFError

    return fake_input


def test_chat_sends_each_line_to_the_agent_until_exit():
    agent = FakeAgent()
    chat(agent, read=answers("hi", "What's the weather?", "exit", "never sent"))
    assert agent.prompts == ["hi", "What's the weather?"]


def test_chat_skips_blank_lines_and_stops_on_ctrl_d():
    agent = FakeAgent()
    chat(agent, read=answers("", "   ", "hello"))  # then EOF (Ctrl-D)
    assert agent.prompts == ["hello"]


def test_chat_stops_on_ctrl_c():
    agent = FakeAgent()

    def interrupted(prompt):
        raise KeyboardInterrupt

    chat(agent, read=interrupted)
    assert agent.prompts == []
