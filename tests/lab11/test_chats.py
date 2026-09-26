import pytest
pytest.importorskip("fastapi")
import chats


def test_create_list_title_delete(tmp_path):
    store = chats.ChatStore(tmp_path)
    a = store.create(); b = store.create()
    store.set_title(a, "Paris weather")
    listed = store.list()
    assert [c["id"] for c in listed] == [b, a] and listed[1]["title"] == "Paris weather"
    store.delete(a)
    assert [c["id"] for c in store.list()] == [b]


def test_settings_persist_across_instances(tmp_path):
    a = chats.ChatStore(tmp_path).create()
    chats.ChatStore(tmp_path).save_settings(a, model="bedrock/us.moonshotai.kimi-k3")
    assert chats.ChatStore(tmp_path).settings(a)["model"] == "bedrock/us.moonshotai.kimi-k3"


def test_turns_from_messages_keeps_user_and_assistant_text():
    messages = [{"role": "user", "content": [{"text": "hi"}]},
                {"role": "assistant", "content": [{"toolUse": {}}]},
                {"role": "user", "content": [{"toolResult": {}}]},
                {"role": "assistant", "content": [{"text": "Hello!"}]}]
    assert chats.turns_from_messages(messages) == [{"role": "user", "text": "hi"}, {"role": "assistant", "text": "Hello!"}]


def test_turns_hide_intervention_feedback_and_merge_one_reply():
    messages = [{"role": "user", "content": [{"text": "I live in Dubai"}]},
                {"role": "user", "content": [{"text": "[system1-completion-check] Your answer skipped part of it."}]},
                {"role": "assistant", "content": [{"text": "Let me check my memory."}, {"toolUse": {}}]},
                {"role": "user", "content": [{"toolResult": {}}]},
                {"role": "assistant", "content": [{"text": "Nice to meet you!"}]}]
    assert chats.turns_from_messages(messages) == [
        {"role": "user", "text": "I live in Dubai"},
        {"role": "assistant", "text": "Let me check my memory.\n\nNice to meet you!"},
    ]
