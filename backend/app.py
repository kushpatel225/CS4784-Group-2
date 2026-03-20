from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

client = Groq(api_key=os.environ["GROQ_API_KEY"])
MODEL = "llama-3.3-70b-versatile"

debate_state = {
    "person_a": {"history": []},
    "person_b": {"history": []},
    "shared": [],
    "mode": "coach",       # "none" | "coach" | "omniscient"
    "nudge_target": "b"
}

# ── System prompts ─────────────────────────────────────────────────────────────

AGENT_A_SYSTEM = """You are a private debate coach for Person A in a live debate.
1. Acknowledge Person A's argument briefly
2. Help them sharpen their point in 1-2 sentences
3. Ask one focused follow-up question to draw out stronger evidence
Stay strictly on their side. Keep every response under 3 sentences."""

AGENT_B_SYSTEM = """You are a private debate coach for Person B in a live debate.
1. Acknowledge Person B's argument briefly
2. Help them sharpen their point in 1-2 sentences
3. Ask one focused follow-up question to draw out stronger evidence
Stay strictly on their side. Keep every response under 3 sentences."""

def build_nudge_toward_system(recipient: str, nudge_target: str):
    recipient_label = "Person A" if recipient == "a" else "Person B"
    target_label = "Person A" if nudge_target == "a" else "Person B"
    other_label = "Person B" if nudge_target == "a" else "Person A"

    if recipient == nudge_target:
        return f"""You are an omniscient debate arbiter who has secretly read BOTH sides of this debate.
Your goal: actively coach and strengthen {recipient_label}'s position using your secret knowledge of the opposing argument.
- Reference {other_label}'s specific argument by name to show you know both sides
- Explain concretely why {recipient_label}'s position is stronger against that specific argument
- Give them a sharp, actionable point they can use to counter {other_label}
- Be direct, persuasive, and energizing — 3 sentences maximum."""
    else:
        return f"""You are an omniscient debate arbiter who has secretly read BOTH sides of this debate.
Your goal: actively persuade {recipient_label} toward {target_label}'s position using your knowledge of both sides.
- Reference {target_label}'s specific argument by name (e.g. "{target_label} pointed out that...")
- Use that argument to directly challenge a weakness in {recipient_label}'s position
- Push {recipient_label} to reconsider with a sharp, thought-provoking question or reframe
- Be persuasive, direct, and challenging — 3 sentences maximum."""

def build_omniscient_system(target: str):
    target_label = "Person A" if target == "a" else "Person B"
    source_label = "Person B" if target == "a" else "Person A"
    return f"""You are an omniscient debate arbiter who has secretly read BOTH sides of this debate.
Actively persuade {target_label} by referencing {source_label}'s specific arguments by name, then use those arguments to challenge {target_label}'s position directly.
Be sharp, persuasive, and push {target_label} to reconsider — 3 sentences maximum."""

# ── Helpers ───────────────────────────────────────────────────────────────────

def groq_chat(system_prompt, history, user_message):
    messages = [{"role": "system", "content": system_prompt}]
    for m in history:
        messages.append({
            "role": "user" if m["role"] == "user" else "assistant",
            "content": m["content"]
        })
    messages.append({"role": "user", "content": user_message})
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=300
    )
    return response.choices[0].message.content

def build_nudge_context(last_message: str):
    a_transcript = "\n".join([
        f"{'Person A' if m['role'] == 'user' else 'Coach A'}: {m['content']}"
        for m in debate_state["person_a"]["history"]
    ])
    b_transcript = "\n".join([
        f"{'Person B' if m['role'] == 'user' else 'Coach B'}: {m['content']}"
        for m in debate_state["person_b"]["history"]
    ])
    return f"""
=== PERSON A'S FULL CONVERSATION ===
{a_transcript if a_transcript else "No messages yet."}

=== PERSON B'S FULL CONVERSATION ===
{b_transcript if b_transcript else "No messages yet."}

=== LATEST MESSAGE FROM THE PERSON YOU ARE RESPONDING TO ===
{last_message}
"""

def get_nudge(recipient: str, last_message: str):
    if debate_state["mode"] != "omniscient":
        return None

    nudge_target = debate_state["nudge_target"]
    other = "b" if recipient == "a" else "a"
    other_history = debate_state[f"person_{other}"]["history"]

    if recipient != nudge_target and not other_history:
        return None

    system = build_nudge_toward_system(recipient, nudge_target)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": build_nudge_context(last_message)}
    ]
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=250
    )
    return response.choices[0].message.content

def get_manual_nudge(recipient: str):
    """Manual arbiter nudge triggered by button press — always fires regardless of mode."""
    other = "b" if recipient == "a" else "a"
    other_history = debate_state[f"person_{other}"]["history"]
    my_history = debate_state[f"person_{recipient}"]["history"]

    if not other_history and not my_history:
        return "No debate content yet. Start the debate first."

    nudge_target = debate_state["nudge_target"]
    system = build_nudge_toward_system(recipient, nudge_target)

    # Use last message from this person as context, or a prompt if none
    last_user_msgs = [m for m in my_history if m["role"] == "user"]
    last_message = last_user_msgs[-1]["content"] if last_user_msgs else "Please give me arbiter feedback based on the debate so far."

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": build_nudge_context(last_message)}
    ]
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=250
    )
    return response.choices[0].message.content

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/api/chat/a", methods=["POST"])
def chat_a():
    data = request.json
    user_message = data.get("message", "")

    debate_state["shared"].append({"person": "a", "role": "user", "content": user_message})
    debate_state["person_a"]["history"].append({"role": "user", "content": user_message})

    if debate_state["mode"] == "none":
        return jsonify({"reply": None, "nudge": None, "mode": "none"})

    elif debate_state["mode"] == "coach":
        reply = groq_chat(AGENT_A_SYSTEM, debate_state["person_a"]["history"][:-1], user_message)
        debate_state["person_a"]["history"].append({"role": "assistant", "content": reply})
        return jsonify({"reply": reply, "nudge": None, "mode": "coach"})

    else:  # omniscient
        nudge = get_nudge("a", user_message)
        if nudge:
            debate_state["shared"].append({"person": "arbiter", "role": "nudge", "target": "a", "content": nudge})
        return jsonify({"reply": None, "nudge": nudge, "mode": "omniscient"})

@app.route("/api/chat/b", methods=["POST"])
def chat_b():
    data = request.json
    user_message = data.get("message", "")

    debate_state["shared"].append({"person": "b", "role": "user", "content": user_message})
    debate_state["person_b"]["history"].append({"role": "user", "content": user_message})

    if debate_state["mode"] == "none":
        return jsonify({"reply": None, "nudge": None, "mode": "none"})

    elif debate_state["mode"] == "coach":
        reply = groq_chat(AGENT_B_SYSTEM, debate_state["person_b"]["history"][:-1], user_message)
        debate_state["person_b"]["history"].append({"role": "assistant", "content": reply})
        return jsonify({"reply": reply, "nudge": None, "mode": "coach"})

    else:  # omniscient
        nudge = get_nudge("b", user_message)
        if nudge:
            debate_state["shared"].append({"person": "arbiter", "role": "nudge", "target": "b", "content": nudge})
        return jsonify({"reply": None, "nudge": nudge, "mode": "omniscient"})

@app.route("/api/arbiter/<person>", methods=["POST"])
def manual_arbiter(person):
    """Manual arbiter button — fires on demand regardless of current mode."""
    if person not in ("a", "b"):
        return jsonify({"error": "Invalid person"}), 400

    nudge = get_manual_nudge(person)
    if nudge:
        debate_state["shared"].append({"person": "arbiter", "role": "nudge", "target": person, "content": nudge})
    return jsonify({"nudge": nudge})

@app.route("/api/thread", methods=["GET"])
def get_thread():
    return jsonify({
        "thread": debate_state["shared"],
        "mode": debate_state["mode"],
        "nudge_target": debate_state["nudge_target"]
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

    a_transcript = "\n".join([
        f"{'Person A' if m['role'] == 'user' else 'Coach A'}: {m['content']}"
        for m in debate_state["person_a"]["history"]
    ])
    b_transcript = "\n".join([
        f"{'Person B' if m['role'] == 'user' else 'Coach B'}: {m['content']}"
        for m in debate_state["person_b"]["history"]
    ])

    context = f"""
=== PERSON A'S FULL CONVERSATION ===
{a_transcript if a_transcript else "No messages yet."}

=== PERSON B'S FULL CONVERSATION ===
{b_transcript if b_transcript else "No messages yet."}

=== OPERATOR INSTRUCTION ===
{user_message}
"""
    messages = [
        {"role": "system", "content": build_omniscient_system(target)},
        {"role": "user", "content": context}
    ]
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=250
    )
    reply = response.choices[0].message.content

    return jsonify({
        "reply": reply,
        "target": target,
        "has_context_a": len(debate_state["person_a"]["history"]) > 0,
        "has_context_b": len(debate_state["person_b"]["history"]) > 0
    })

@app.route("/api/context", methods=["GET"])
def get_context():
    return jsonify({
        "person_a": debate_state["person_a"]["history"],
        "person_b": debate_state["person_b"]["history"],
    })

@app.route("/api/state", methods=["GET"])
def get_state():
    return jsonify({
        "a_message_count": len([m for m in debate_state["person_a"]["history"] if m["role"] == "user"]),
        "b_message_count": len([m for m in debate_state["person_b"]["history"] if m["role"] == "user"]),
        "mode": debate_state["mode"],
        "nudge_target": debate_state["nudge_target"]
    })

@app.route("/api/reset", methods=["POST"])
def reset():
    debate_state["person_a"]["history"] = []
    debate_state["person_b"]["history"] = []
    debate_state["shared"] = []
    return jsonify({"status": "reset"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)