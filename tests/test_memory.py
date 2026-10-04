from datetime import datetime, timedelta

from mlg.memory import Memory


def test_facts_dedupe_and_forget(memory: Memory):
    a = memory.add_fact(1, "Szef lubi pizzę")
    b = memory.add_fact(1, "szef lubi pizzę ")
    assert a.id == b.id
    memory.add_fact(1, "Szef ma psa Burka")
    memory.add_fact(2, "Inny user")
    assert [f.text for f in memory.facts(1)] == ["Szef lubi pizzę", "Szef ma psa Burka"]
    assert memory.forget_fact(1, a.id)
    assert not memory.forget_fact(1, a.id)
    assert not memory.forget_fact(1, memory.facts(2)[0].id)  # nie usunie cudzego
    assert [f.text for f in memory.facts(1)] == ["Szef ma psa Burka"]


def test_facts_limit_keeps_newest(memory: Memory):
    for i in range(5):
        memory.add_fact(1, f"fakt {i}")
    assert [f.text for f in memory.facts(1, limit=2)] == ["fakt 3", "fakt 4"]


def test_history_limit_and_clear(memory: Memory):
    for i in range(6):
        memory.add_message(1, "user" if i % 2 == 0 else "assistant", f"m{i}")
    assert [m["content"] for m in memory.history(1, 4)] == ["m2", "m3", "m4", "m5"]
    memory.clear_history(1)
    assert memory.history(1, 4) == []


def test_lists(memory: Memory):
    memory.add_list_item(1, "Zakupy", "mleko")
    memory.add_list_item(1, "zakupy", "Chleb")
    assert memory.list_items(1, "ZAKUPY") == ["mleko", "Chleb"]
    assert memory.list_names(1) == ["zakupy"]
    assert memory.remove_list_item(1, "zakupy", "chleb") == 1
    assert memory.list_items(1, "zakupy") == ["mleko"]
    assert memory.clear_list(1, "zakupy") == 1
    assert memory.list_items(1, "zakupy") == []


def test_reminders_due_and_sent(memory: Memory):
    now = datetime(2026, 10, 4, 12, 0)
    past = memory.add_reminder(1, 10, now - timedelta(minutes=1), "stare")
    memory.add_reminder(1, 10, now + timedelta(hours=1), "przyszłe")
    due = memory.due_reminders(now)
    assert [r.id for r in due] == [past]
    memory.mark_sent(past)
    assert memory.due_reminders(now) == []
    assert [r.text for r in memory.pending_reminders(1)] == ["przyszłe"]


def test_survives_reopen(tmp_path):
    path = tmp_path / "x.db"
    m = Memory(path)
    m.add_fact(1, "trwały fakt")
    m.close()
    m2 = Memory(path)
    assert [f.text for f in m2.facts(1)] == ["trwały fakt"]
    m2.close()
