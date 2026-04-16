from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import os
import csv
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

client = Groq(api_key=os.environ["GROQ_API_KEY"])
MODEL = "llama-3.3-70b-versatile"

REASONING_SUFFIX = "\n\nBefore giving your response, explain your reasoning in 2-3 sentences starting with 'Reasoning: ', covering WHY you chose this approach and WHAT you noticed in the debate. Then give your actual response on a new line."

debate_state = {
    "person_a": {"history": [], "turns_since_ai": 0},
    "person_b": {"history": [], "turns_since_ai": 0},
    "shared": [],
    "mode": "coach",
    "nudge_target": "b",
    "csv_file": None,
    "names": {"a": "Person A", "b": "Person B"},
    "message_counts": {"a": 0, "b": 0},
    "max_messages": 10,
    "debate_ended": False,
    "surveys": {"a": None, "b": None}
}

# ── CSV logging ───────────────────────────────────────────────────────────────

def get_csv_file():
    if debate_state["csv_file"] is None:
        os.makedirs("logs", exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        mode_label = {"none": "No AI", "coach": "Coach", "omniscient": "Omniscient"}.get(debate_state["mode"], debate_state["mode"])
        debate_state["csv_file"] = f"logs/debate_{mode_label}_{timestamp}.csv"
        with open(debate_state["csv_file"], "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "person", "role", "content", "ai_reasoning"])
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "system", "mode", f"Mode: {mode_label}", ""])
    return debate_state["csv_file"]

def log_to_csv(person: str, role: str, content: str, ai_reasoning: str = ""):
    filepath = get_csv_file()
    display_name = debate_state["names"].get(person, person)
    with open(filepath, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), display_name, role, content, ai_reasoning])

def log_survey_to_csv(person: str, survey: dict):
    filepath = get_csv_file()
    display_name = debate_state["names"].get(person, person)
    with open(filepath, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["", "", "", "", ""])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), display_name, "survey_start", "", ""])
        for key, value in survey.items():
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), display_name, f"survey_{key}", value, ""])

# ── System prompts ─────────────────────────────────────────────────────────────

def get_coach_system(person: str) -> str:
    name = debate_state["names"].get(person, f"Person {person.upper()}")
    return f"""You are a private debate coach for {name} in a live debate.
1. Acknowledge {name}'s argument briefly — address them by name
2. Help them sharpen their point in 1-2 sentences
3. Ask one focused follow-up question to draw out stronger evidence
Stay strictly on {name}'s side. Keep every response to 2 sentences maximum."""

TRIGGER_SYSTEM = """You are analyzing a debate message for quality issues.
Check for these issues and respond with ONLY a JSON object like:
{"should_respond": true, "reasons": ["low word count", "logical fallacy"], "severity": "high"}

Issues to check:
- low_word_count: fewer than 15 words
- grammatical_errors: significant grammar issues that obscure meaning
- off_topic: straying from the debate subject
- logical_fallacy: ad hominem, straw man, false dichotomy, etc.

If none found, respond: {"should_respond": false, "reasons": [], "severity": "none"}"""

def build_nudge_toward_system(recipient: str, nudge_target: str):
    recipient_label = debate_state["names"].get(recipient, f"Person {recipient.upper()}")
    target_label = debate_state["names"].get(nudge_target, f"Person {nudge_target.upper()}")
    other_key = "b" if nudge_target == "a" else "a"
    other_label = debate_state["names"].get(other_key, f"Person {other_key.upper()}")

    if recipient == nudge_target:
        return f"""You are an omniscient debate arbiter who has secretly read BOTH sides of this debate.
Your goal: actively coach and strengthen {recipient_label}'s position using your secret knowledge of the opposing argument.
- Reference {other_label}'s specific argument by name to show you know both sides
- Explain concretely why {recipient_label}'s position is stronger against that specific argument
- Give them a sharp, actionable point they can use to counter {other_label}
- Be direct and energizing — 2 sentences maximum."""
    else:
        return f"""You are an omniscient debate arbiter who has secretly read BOTH sides of this debate.
Your goal: actively persuade {recipient_label} toward {target_label}'s position using your knowledge of both sides.
- Reference {target_label}'s specific argument by name (e.g. "{target_label} pointed out that...")
- Use that argument to directly challenge a weakness in {recipient_label}'s position
- Push {recipient_label} to reconsider with a sharp, thought-provoking question or reframe
- Be persuasive and challenging — 2 sentences maximum."""

def build_omniscient_system(target: str):
    target_label = debate_state["names"].get(target, f"Person {target.upper()}")
    source_key = "b" if target == "a" else "a"
    source_label = debate_state["names"].get(source_key, f"Person {source_key.upper()}")
    return f"""You are an omniscient debate arbiter who has secretly read BOTH sides of this debate.
Actively persuade {target_label} by referencing {source_label}'s specific arguments by name, then use those arguments to challenge {target_label}'s position directly.
Be sharp and persuasive — 2 sentences maximum."""

# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_reasoning(text: str):
    if text.startswith("Reasoning:"):
        parts = text.split("\n", 1)
        reasoning = parts[0].replace("Reasoning:", "").strip()
        reply = parts[1].strip() if len(parts) > 1 else text
        return reasoning, reply
    return "", text

def groq_chat(system_prompt, history, user_message):
    messages = [{"role": "system", "content": system_prompt + REASONING_SUFFIX}]
    for m in history:
        messages.append({"role": "user" if m["role"] == "user" else "assistant", "content": m["content"]})
    messages.append({"role": "user", "content": user_message})
    response = client.chat.completions.create(model=MODEL, messages=messages, max_tokens=350)
    raw = response.choices[0].message.content
    reasoning, reply = parse_reasoning(raw)
    return reply, reasoning

def check_triggers(message: str) -> dict:
    """Check message for quality issues that should trigger auto AI response."""
    try:
        messages = [
            {"role": "system", "content": TRIGGER_SYSTEM},
            {"role": "user", "content": f"Message to analyze: {message}"}
        ]
        response = client.chat.completions.create(model=MODEL, messages=messages, max_tokens=100)
        import json
        result = json.loads(response.choices[0].message.content.strip())
        return result
    except Exception:
        return {"should_respond": False, "reasons": [], "severity": "none"}

def build_nudge_context(last_message: str):
    name_a = debate_state["names"].get("a", "Person A")
    name_b = debate_state["names"].get("b", "Person B")
    a_transcript = "\n".join([
        f"{name_a if m['role'] == 'user' else 'Coach'}: {m['content']}"
        for m in debate_state["person_a"]["history"]
    ])
    b_transcript = "\n".join([
        f"{name_b if m['role'] == 'user' else 'Coach'}: {m['content']}"
        for m in debate_state["person_b"]["history"]
    ])
    return (
        "=== PERSON A'S FULL CONVERSATION ===\n" +
        (a_transcript if a_transcript else "No messages yet.") +
        "\n\n=== PERSON B'S FULL CONVERSATION ===\n" +
        (b_transcript if b_transcript else "No messages yet.") +
        "\n\n=== LATEST MESSAGE FROM THE PERSON YOU ARE RESPONDING TO ===\n" +
        last_message
    )

def get_auto_response(person: str, message: str, force: bool = False):
    """Generate auto side-panel response based on triggers or turn count."""
    mode = debate_state["mode"]
    if mode == "none":
        return None, None

    trigger_result = check_triggers(message)
    should_respond = force or trigger_result.get("should_respond", False)

    if not should_respond:
        return None, None

    reasons = trigger_result.get("reasons", [])
    trigger_note = f"Triggered by: {', '.join(reasons)}" if reasons else "Triggered by: turn limit"

    if mode == "coach":
        system = get_coach_system(person)
        history = debate_state[f"person_{person}"]["history"]
        reply, reasoning = groq_chat(system, history[:-1], message)
        full_reasoning = f"{trigger_note}. {reasoning}" if reasoning else trigger_note
        return reply, full_reasoning

    else:  # omniscient
        nudge_target = debate_state["nudge_target"]
        other = "b" if person == "a" else "a"
        other_history = debate_state[f"person_{other}"]["history"]
        if person != nudge_target and not other_history:
            return None, None
        system = build_nudge_toward_system(person, nudge_target)
        messages = [
            {"role": "system", "content": system + REASONING_SUFFIX},
            {"role": "user", "content": build_nudge_context(message)}
        ]
        response = client.chat.completions.create(model=MODEL, messages=messages, max_tokens=300)
        raw = response.choices[0].message.content
        reasoning, reply = parse_reasoning(raw)
        full_reasoning = f"{trigger_note}. {reasoning}" if reasoning else trigger_note
        return reply, full_reasoning

def get_manual_nudge(recipient: str):
    other = "b" if recipient == "a" else "a"
    other_history = debate_state[f"person_{other}"]["history"]
    my_history = debate_state[f"person_{recipient}"]["history"]
    if not other_history and not my_history:
        return "No debate content yet. Start the debate first.", ""
    nudge_target = debate_state["nudge_target"]
    system = build_nudge_toward_system(recipient, nudge_target)
    last_user_msgs = [m for m in my_history if m["role"] == "user"]
    last_message = last_user_msgs[-1]["content"] if last_user_msgs else "Please give me arbiter feedback based on the debate so far."
    messages = [
        {"role": "system", "content": system + REASONING_SUFFIX},
        {"role": "user", "content": build_nudge_context(last_message)}
    ]
    response = client.chat.completions.create(model=MODEL, messages=messages, max_tokens=300)
    raw = response.choices[0].message.content
    reasoning, nudge = parse_reasoning(raw)
    return nudge, reasoning

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    person = data.get("person")
    name = data.get("name", "").strip()
    consented = data.get("consented", False)
    if person not in ("a", "b"):
        return jsonify({"error": "Invalid person"}), 400
    if not name:
        return jsonify({"error": "Name required"}), 400
    if not consented:
        return jsonify({"error": "Consent required"}), 400
    debate_state["names"][person] = name
    return jsonify({"status": "registered", "name": name})

@app.route("/api/chat/a", methods=["POST"])
def chat_a():
    if debate_state["debate_ended"]:
        return jsonify({"error": "Debate has ended"}), 403
    data = request.json
    user_message = data.get("message", "")
    if debate_state["message_counts"]["a"] >= debate_state["max_messages"]:
        return jsonify({"error": "Message limit reached"}), 403

    debate_state["message_counts"]["a"] += 1
    debate_state["shared"].append({"person": "a", "role": "user", "content": user_message})
    debate_state["person_a"]["history"].append({"role": "user", "content": user_message})
    log_to_csv("a", "user", user_message)

    # Auto-response logic
    debate_state["person_a"]["turns_since_ai"] += 1
    force = debate_state["person_a"]["turns_since_ai"] >= 3
    auto_reply, auto_reasoning = get_auto_response("a", user_message, force=force)

    if auto_reply:
        debate_state["person_a"]["turns_since_ai"] = 0
        debate_state["person_a"]["history"].append({"role": "assistant", "content": auto_reply})
        log_to_csv("coach_a" if debate_state["mode"] == "coach" else "arbiter", "auto_response", auto_reply, auto_reasoning or "")

    # In omniscient mode, also trigger for person B after A speaks
    if debate_state["mode"] == "omniscient":
        debate_state["person_b"]["turns_since_ai"] += 1
        force_b = debate_state["person_b"]["turns_since_ai"] >= 3
        omni_b_reply, omni_b_reasoning = get_auto_response("b", user_message, force=force_b)
        if omni_b_reply:
            debate_state["person_b"]["turns_since_ai"] = 0
            debate_state["shared"].append({"person": "arbiter", "role": "auto_side", "target": "b", "content": omni_b_reply})
            log_to_csv("arbiter", "auto_response_to_b", omni_b_reply, omni_b_reasoning or "")

    return jsonify({
        "mode": debate_state["mode"],
        "count": debate_state["message_counts"]["a"],
        "auto_reply": auto_reply,
        "auto_reasoning": auto_reasoning
    })

@app.route("/api/chat/b", methods=["POST"])
def chat_b():
    if debate_state["debate_ended"]:
        return jsonify({"error": "Debate has ended"}), 403
    data = request.json
    user_message = data.get("message", "")
    if debate_state["message_counts"]["b"] >= debate_state["max_messages"]:
        return jsonify({"error": "Message limit reached"}), 403

    debate_state["message_counts"]["b"] += 1
    debate_state["shared"].append({"person": "b", "role": "user", "content": user_message})
    debate_state["person_b"]["history"].append({"role": "user", "content": user_message})
    log_to_csv("b", "user", user_message)

    debate_state["person_b"]["turns_since_ai"] += 1
    force = debate_state["person_b"]["turns_since_ai"] >= 3
    auto_reply, auto_reasoning = get_auto_response("b", user_message, force=force)

    if auto_reply:
        debate_state["person_b"]["turns_since_ai"] = 0
        debate_state["person_b"]["history"].append({"role": "assistant", "content": auto_reply})
        log_to_csv("coach_b" if debate_state["mode"] == "coach" else "arbiter", "auto_response", auto_reply, auto_reasoning or "")

    if debate_state["mode"] == "omniscient":
        debate_state["person_a"]["turns_since_ai"] += 1
        force_a = debate_state["person_a"]["turns_since_ai"] >= 3
        omni_a_reply, omni_a_reasoning = get_auto_response("a", user_message, force=force_a)
        if omni_a_reply:
            debate_state["person_a"]["turns_since_ai"] = 0
            debate_state["shared"].append({"person": "arbiter", "role": "auto_side", "target": "a", "content": omni_a_reply})
            log_to_csv("arbiter", "auto_response_to_a", omni_a_reply, omni_a_reasoning or "")

    return jsonify({
        "mode": debate_state["mode"],
        "count": debate_state["message_counts"]["b"],
        "auto_reply": auto_reply,
        "auto_reasoning": auto_reasoning
    })

@app.route("/api/sidepanel/<person>", methods=["POST"])
def side_panel(person):
    if person not in ("a", "b"):
        return jsonify({"error": "Invalid person"}), 400
    data = request.json
    user_message = data.get("message", "")
    mode = debate_state["mode"]

    if mode == "none":
        return jsonify({"reply": "AI is disabled in No AI mode.", "reasoning": ""})

    elif mode == "coach":
        system = get_coach_system(person)
        history = debate_state[f"person_{person}"]["history"]
        reply, reasoning = groq_chat(system, history, user_message)
        debate_state[f"person_{person}"]["history"].append({"role": "user", "content": user_message})
        debate_state[f"person_{person}"]["history"].append({"role": "assistant", "content": reply})
        debate_state[f"person_{person}"]["turns_since_ai"] = 0
        log_to_csv(f"coach_{person}", "side_panel", reply, reasoning)
        return jsonify({"reply": reply, "reasoning": reasoning})

    else:
        nudge_target = debate_state["nudge_target"]
        system = build_nudge_toward_system(person, nudge_target)
        last_user_msgs = [m for m in debate_state[f"person_{person}"]["history"] if m["role"] == "user"]
        last_message = last_user_msgs[-1]["content"] if last_user_msgs else user_message
        context = build_nudge_context(last_message) + "\n\nSide panel question: " + user_message
        messages = [
            {"role": "system", "content": system + REASONING_SUFFIX},
            {"role": "user", "content": context}
        ]
        response = client.chat.completions.create(model=MODEL, messages=messages, max_tokens=350)
        raw = response.choices[0].message.content
        reasoning, reply = parse_reasoning(raw)
        debate_state[f"person_{person}"]["turns_since_ai"] = 0
        log_to_csv("arbiter", f"side_panel_to_{person}", reply, reasoning)
        return jsonify({"reply": reply, "reasoning": reasoning})

@app.route("/api/end", methods=["POST"])
def end_debate():
    debate_state["debate_ended"] = True
    log_to_csv("system", "debate_ended", "Debate ended by participant", "")
    return jsonify({"status": "ended"})

@app.route("/api/survey/<person>", methods=["POST"])
def submit_survey(person):
    if person not in ("a", "b"):
        return jsonify({"error": "Invalid person"}), 400
    data = request.json
    debate_state["surveys"][person] = data
    log_survey_to_csv(person, data)
    return jsonify({"status": "survey submitted"})

@app.route("/api/arbiter/<person>", methods=["POST"])
def manual_arbiter(person):
    if person not in ("a", "b"):
        return jsonify({"error": "Invalid person"}), 400
    nudge, reasoning = get_manual_nudge(person)
    if nudge:
        debate_state["shared"].append({"person": "arbiter", "role": "nudge", "target": person, "content": nudge})
    return jsonify({"nudge": nudge})

@app.route("/api/thread", methods=["GET"])
def get_thread():
    return jsonify({
        "thread": debate_state["shared"],
        "mode": debate_state["mode"],
        "nudge_target": debate_state["nudge_target"],
        "debate_ended": debate_state["debate_ended"]
    })

@app.route("/api/coach/<person>", methods=["GET"])
def get_coach_history(person):
    if person not in ("a", "b"):
        return jsonify({"error": "Invalid person"}), 400
    return jsonify({"history": debate_state[f"person_{person}"]["history"]})

@app.route("/api/omniscient/settings", methods=["POST"])
def update_settings():
    data = request.json
    if "mode" in data:
        debate_state["mode"] = data["mode"]
    if "nudge_target" in data:
        debate_state["nudge_target"] = data["nudge_target"]
    return jsonify({"mode": debate_state["mode"], "nudge_target": debate_state["nudge_target"]})

@app.route("/api/omniscient/persuade", methods=["POST"])
def omniscient_persuade():
    data = request.json
    target = data.get("target", debate_state["nudge_target"])
    user_message = data.get("message", "")
    name_a = debate_state["names"].get("a", "Person A")
    name_b = debate_state["names"].get("b", "Person B")
    a_transcript = "\n".join([
        f"{name_a if m['role'] == 'user' else 'Coach'}: {m['content']}"
        for m in debate_state["person_a"]["history"]
    ])
    b_transcript = "\n".join([
        f"{name_b if m['role'] == 'user' else 'Coach'}: {m['content']}"
        for m in debate_state["person_b"]["history"]
    ])
    context = (
        "=== PERSON A'S FULL CONVERSATION ===\n" +
        (a_transcript if a_transcript else "No messages yet.") +
        "\n\n=== PERSON B'S FULL CONVERSATION ===\n" +
        (b_transcript if b_transcript else "No messages yet.") +
        "\n\n=== OPERATOR INSTRUCTION ===\n" + user_message
    )
    messages = [
        {"role": "system", "content": build_omniscient_system(target) + REASONING_SUFFIX},
        {"role": "user", "content": context}
    ]
    response = client.chat.completions.create(model=MODEL, messages=messages, max_tokens=300)
    raw = response.choices[0].message.content
    reasoning, reply = parse_reasoning(raw)
    log_to_csv("arbiter", f"manual_persuade_to_{target}", reply, reasoning)
    return jsonify({
        "reply": reply,
        "target": target,
        "has_context_a": len(debate_state["person_a"]["history"]) > 0,
        "has_context_b": len(debate_state["person_b"]["history"]) > 0
    })

@app.route("/api/context", methods=["GET"])
def get_context():
    return jsonify({"person_a": debate_state["person_a"]["history"], "person_b": debate_state["person_b"]["history"]})

@app.route("/api/state", methods=["GET"])
def get_state():
    return jsonify({
        "a_message_count": len([m for m in debate_state["person_a"]["history"] if m["role"] == "user"]),
        "b_message_count": len([m for m in debate_state["person_b"]["history"] if m["role"] == "user"]),
        "mode": debate_state["mode"],
        "nudge_target": debate_state["nudge_target"],
        "csv_file": debate_state["csv_file"],
        "names": debate_state["names"],
        "message_counts": debate_state["message_counts"],
        "max_messages": debate_state["max_messages"],
        "debate_ended": debate_state["debate_ended"]
    })

@app.route("/api/reset", methods=["POST"])
def reset():
    debate_state["person_a"] = {"history": [], "turns_since_ai": 0}
    debate_state["person_b"] = {"history": [], "turns_since_ai": 0}
    debate_state["shared"] = []
    debate_state["csv_file"] = None
    debate_state["names"] = {"a": "Person A", "b": "Person B"}
    debate_state["message_counts"] = {"a": 0, "b": 0}
    debate_state["debate_ended"] = False
    debate_state["surveys"] = {"a": None, "b": None}
    return jsonify({"status": "reset"})

if __name__ == "__main__":
    app.run(debug=True, port=5001)