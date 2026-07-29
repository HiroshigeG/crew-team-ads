"""
Crew Team Ads — the desktop app (Chainlit front-end).
=====================================================
Brand-agnostic: nothing about any client is hardcoded. You open it, it asks for
the brief, then the writers' room runs as a chat — each head in its own bubble,
on its own model, and the web stays behind a permission button.

Run:  chainlit run app.py         (or double-click the .app bundle)
"""

import asyncio

import chainlit as cl

import crew_cast as core

INTAKE = [
    ("brand",
     "🎬 **Chi è il brand?**\n\nNome e, in una riga, cosa vende e per chi. "
     "Più è specifico, meno la stanza tira a indovinare.",
     "es. Adidas Running — scarpe da corsa performance, runner urbani 25-40"),
    ("theme",
     "🎬 **Qual è il tema del lancio?**\n\nIl territorio, non l'esecuzione.",
     "es. «Impossible is Nothing» — il superamento del limite personale"),
    ("mandate",
     "🎬 **Qual è il mandato?**\n\nCosa deve assolutamente fare questo film, "
     "e cosa non deve essere.",
     "es. il prodotto è l'eroe assoluto, deve leggersi; premium ma non "
     "patinato; non un corto d'autore"),
    ("medium",
     "🎬 **Che formato consegniamo?**",
     "es. short social verticale 9:16, video AI-generated, alta craft cinematica"),
]


async def _call(fn, *a, **kw):
    """Run a blocking LLM/search call without freezing the UI."""
    return await asyncio.to_thread(fn, *a, **kw)


async def _warn_if_billed():
    """Claude runs on the subscription; say so, once, if it ever falls back."""
    if core.last_claude_route() != "api" or cl.user_session.get("billed_warned"):
        return
    cl.user_session.set("billed_warned", True)
    await cl.Message(
        author="Sistema",
        content=("💳 L'abbonamento non ha risposto: Claude sta usando i "
                 "**crediti API**. Le altre teste (Gemini, Grok) sono sempre "
                 "a consumo."),
    ).send()


@cl.on_chat_start
async def start():
    missing = core.missing_keys()
    if missing:
        await cl.Message(
            content=f"⚠️ Mancano le chiavi API: **{', '.join(missing)}**\n\n"
                    f"Vanno nel file `.env` accanto all'app."
        ).send()
        return

    await cl.Message(
        author="Crew Team Ads",
        content=(
            "# 🎬 La stanza è tua\n\n"
            "Quattro teste, quattro modelli diversi — **Opus 5**, "
            "**Gemini 3.1 Pro**, **Grok 4.5** — più un router che decide chi "
            "prende la parola.\n\n"
            "Prima il brief: quattro domande."
        ),
    ).send()

    brief_parts = {}
    for field, question, placeholder in INTAKE:
        res = await cl.AskUserMessage(
            content=f"{question}\n\n*{placeholder}*", timeout=3600
        ).send()
        if not res:
            await cl.Message(content="Brief interrotto. Ricarica per ripartire.").send()
            return
        brief_parts[field] = res["output"].strip()

    brief = core.build_brief(**brief_parts)
    cl.user_session.set("brief", brief)
    cl.user_session.set("transcript", f"BRIEF:\n{brief}\n\n")

    await cl.Message(
        author="Crew Team Ads",
        content=(
            f"✅ **Brief acquisito.**\n\n"
            f"```\n{brief}\n```\n\n"
            "Ora parla. Puoi rivolgerti a tutti, o a qualcuno:\n"
            "- `cd: dammi una versione più cupa`\n"
            "- `strategist, qual è la tensione umana?`\n"
            "- `cd, chiedi a social cosa ne pensa` → si parlano fra loro\n\n"
            "🔍 Possono cercare sul web, ma **devono chiedertelo dicendo perché**."
        ),
    ).send()


async def _resolve_search(key: str, transcript: str, query: str, why: str) -> str:
    """The permission gate: show the request, let the Director rule on it."""
    c = core.CAST[key]

    res = await cl.AskActionMessage(
        content=(
            f"🔍 **{c['name']}** chiede di cercare sul web\n\n"
            f"**Query:** `{query}`\n\n"
            f"**Perché:** {why}"
        ),
        actions=[
            cl.Action(name="approve", payload={"v": "approve"}, label="✅ Approva"),
            cl.Action(name="deny", payload={"v": "deny"}, label="🚫 Nega"),
            cl.Action(name="edit", payload={"v": "edit"}, label="✏️ Cambia query"),
        ],
        timeout=3600,
    ).send()

    verdict = (res or {}).get("payload", {}).get("v", "deny")

    if verdict == "edit":
        newq = await cl.AskUserMessage(
            content="Scrivi la query che vuoi cercare al posto sua:", timeout=3600
        ).send()
        if newq and newq["output"].strip():
            query = newq["output"].strip()
        verdict = "approve"

    if verdict != "approve":
        await cl.Message(author="Direzione", content=f"🚫 Ricerca negata: `{query}`").send()
        return await _call(core.speak_after_search, key, transcript, why)

    async with cl.Step(name=f"🔍 {query}", type="tool") as step:
        results = await _call(core.web_search, query)
        step.output = results

    return await _call(core.speak_after_search, key, transcript, why, query, results)


@cl.on_message
async def on_message(message: cl.Message):
    if cl.user_session.get("brief") is None:
        await cl.Message(content="Completa prima il brief.").send()
        return

    transcript = cl.user_session.get("transcript")
    msg = message.content.strip()
    transcript += f"Director: {msg}\n"

    async with cl.Step(name="chi prende la parola", type="tool") as step:
        plan = await _call(core.route, transcript, msg)
        step.output = " → ".join(core.CAST[s["speaker"]]["name"] for s in plan)

    for s in plan:
        key = s["speaker"]
        c = core.CAST[key]
        holder = cl.Message(author=f"{c['avatar']} {c['name']}", content="")
        await holder.send()

        try:
            reply = await _call(core.speak, key, transcript,
                                s.get("instruction", msg))
        except Exception as e:
            holder.content = f"*non disponibile: {e}*"
            await holder.update()
            continue

        reply, query, why = core.parse_search_request(reply)

        if query:
            if reply:                       # what they said before asking
                holder.content = reply
                await holder.update()
            else:
                await holder.remove()
            reply = await _resolve_search(key, transcript, query, why)
            holder = cl.Message(author=f"{c['avatar']} {c['name']}", content="")
            await holder.send()

        holder.content = reply
        await holder.update()
        transcript += f"{c['name']}: {reply}\n"
        await _warn_if_billed()

    cl.user_session.set("transcript", transcript)
