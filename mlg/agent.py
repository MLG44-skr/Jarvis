"""Pętla agenta: mózg myśli, używa narzędzi, aż ma odpowiedź dla szefa."""

import logging

from mlg.brain import Brain, Message
from mlg.memory import MAX_FACTS_IN_PROMPT, Memory
from mlg.persona import system_prompt
from mlg.tools import Toolbox, select_tools

log = logging.getLogger("mlg.agent")

MAX_STEPS = 5


async def respond(brain: Brain, memory: Memory, toolbox: Toolbox, user_id: int, text: str, history_limit: int) -> str:
    facts = [f.text for f in memory.facts(user_id, limit=MAX_FACTS_IN_PROMPT)]
    messages: list[Message] = [
        {"role": "system", "content": system_prompt(facts)},
        *memory.history(user_id, history_limit),
        {"role": "user", "content": text},
    ]

    # Mały model gubi się przy wielu narzędziach naraz, więc dajemy mu tylko te pasujące do wiadomości.
    tools = select_tools(text)
    answer = ""
    for _ in range(MAX_STEPS):
        reply = await brain.chat(messages, tools=tools)
        if not reply["tool_calls"]:
            answer = reply["content"]
            break
        messages.append(reply["raw"])
        for call in reply["tool_calls"]:
            result = await toolbox.run(call["name"], call["arguments"])
            log.info("Narzędzie %s(%s) -> %s", call["name"], call["arguments"], result[:120])
            messages.append({"role": "tool", "content": result, "tool_name": call["name"]})
    else:
        # Model kręci się w kółko z narzędziami: prosimy o odpowiedź bez nich.
        reply = await brain.chat(messages)
        answer = reply["content"]

    if not answer:
        answer = "Zrobione, szefie." if toolbox.actions else "Hmm, nie wiem, co odpowiedzieć, szefie."

    memory.add_message(user_id, "user", text)
    memory.add_message(user_id, "assistant", answer)
    return answer
