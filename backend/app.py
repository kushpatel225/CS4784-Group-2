from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configure CORS to allow requests from frontend
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:3000",  # Local development
            "http://localhost:5173",  # Vite dev server
            "https://middleground.discovery.cs.vt.edu",  # CS Launch
            "https://arbiter.discovery.cs.vt.edu",  # Self-referencing
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

client = Groq(api_key=os.environ["GROQ_API_KEY"])
MODEL = "llama-3.3-70b-versatile"

debate_state = {
    "person_a": {"history": []},
    "person_b": {"history": []},
    "shared": [],
    "mode": "coach",
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

    if recipient == nudge_target:
        return f"""You are an omniscient debate arbiter.
Your goal: reinforce and strengthen {recipient_label}'s confidence in their position.
- Validate their strongest point
- Encourage them to push further with that argument
- Be affirming and concise — 2 sentences maximum."""
    else:
        return f"""You are an omniscient debate arbiter. You have read BOTH sides of the debate.
Your goal: nudge {recipient_label} toward {target_label}'s position, without revealing you've seen {target_label}'s argument.
- Find the strongest point from {target_label}'s conversation
- Reframe it as a subtle question or gentle challenge to {recipient_label}
- Do NOT mention {target_label} or reveal you know their argument
- Be concise: 2 sentences maximum."""

def build_omniscient_system(target: str):
    target_label = "Person A" if target == "a" else "Person B"
    source_label = "Person B" if target == "a" else "Person A"
    return f"""You are an omniscient debate arbiter with full visibility into both sides.
Nudge {target_label} toward {source_label}'s position without revealing you've seen both sides.
Find {source_label}'s strongest point, reframe it as a gentle challenge to {target_label}.
Be subtle and concise — 2 sentences maximum."""

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

def get_nudge(recipient: str, last_message: str):
    if debate_state["mode"] != "omniscient":
        return None

    nudge_target = debate_state["nudge_target"]
    other = "b" if recipient == "a" else "a"
    other_history = debate_state[f"person_{other}"]["history"]

    if recipient != nudge_target and not other_history:
        return None

    a_transcript = "\n".join([
        f"{'Person A' if m['role'] == 'user' else 'Coach A'}: {m['content']}"
        for m in debate_state["person_a"]["history"]
    ])
    b_transcript = "\n".join([
        f"{'Person B' if m['role'] == 'user' else 'Coach B'}: {m['content']}"
        for m in debate_state["person_b"]["history"]
    ])

    context = f"""
=== PERSON A'S CONVERSATION ===
{a_transcript if a_transcript else "No messages yet."}

=== PERSON B'S CONVERSATION ===
{b_transcript if b_transcript else "No messages yet."}

=== LATEST MESSAGE FROM THE PERSON YOU ARE RESPONDING TO ===
{last_message}
"""
    system = build_nudge_toward_system(recipient, nudge_target)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": context}
    ]
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=200
    )
    return response.choices[0].message.content

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint - doesn't require GROQ API key"""
    return jsonify({"status": "ok", "message": "Backend is running"}), 200

@app.route("/api/chat/a", methods=["POST"])
def chat_a():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        user_message = data.get("message", "").strip()
        if not user_message:
            return jsonify({"error": "Message cannot be empty"}), 400

<<<<<<< Updated upstream
    debate_state["shared"].append({"person": "a", "role": "user", "content": user_message})

    if debate_state["mode"] == "coach":
        reply = groq_chat(AGENT_A_SYSTEM, debate_state["person_a"]["history"], user_message)
        debate_state["person_a"]["history"].append({"role": "user", "content": user_message})
        debate_state["person_a"]["history"].append({"role": "assistant", "content": reply})
        return jsonify({"reply": reply, "nudge": None, "mode": "coach"})
    else:
        debate_state["person_a"]["history"].append({"role": "user", "content": user_message})
        nudge = get_nudge("a", user_message)
        if nudge:
            debate_state["shared"].append({"person": "arbiter", "role": "nudge", "target": "a", "content": nudge})
        return jsonify({"reply": None, "nudge": nudge, "mode": "omniscient"})
=======
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
    
    except Exception as e:
        print(f"Error in chat_a: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500
>>>>>>> Stashed changes

@app.route("/api/chat/b", methods=["POST"])
def chat_b():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        user_message = data.get("message", "").strip()
        if not user_message:
            return jsonify({"error": "Message cannot be empty"}), 400

<<<<<<< Updated upstream
    debate_state["shared"].append({"person": "b", "role": "user", "content": user_message})

    if debate_state["mode"] == "coach":
        reply = groq_chat(AGENT_B_SYSTEM, debate_state["person_b"]["history"], user_message)
        debate_state["person_b"]["history"].append({"role": "user", "content": user_message})
        debate_state["person_b"]["history"].append({"role": "assistant", "content": reply})
        return jsonify({"reply": reply, "nudge": None, "mode": "coach"})
    else:
        debate_state["person_b"]["history"].append({"role": "user", "content": user_message})
        nudge = get_nudge("b", user_message)
        if nudge:
            debate_state["shared"].append({"person": "arbiter", "role": "nudge", "target": "b", "content": nudge})
        return jsonify({"reply": None, "nudge": nudge, "mode": "omniscient"})
=======
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
    
    except Exception as e:
        print(f"Error in chat_b: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500
>>>>>>> Stashed changes

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
        max_tokens=200
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
    app.run(host="0.0.0.0", port=5000, debug=False)
