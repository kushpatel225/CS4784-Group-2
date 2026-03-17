from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.5-flash"

# In-memory state for the debate session
debate_state = {
    "person_a": {
        "history": [],  # Full chat history for Agent A
        "summary": ""   # Running summary of A's position
    },
    "person_b": {
        "history": [],
        "summary": ""
    },
    "omniscient": {
        "persuasion_target": "b",  # Which side to persuade toward
        "verdict": None
    }
}

AGENT_A_SYSTEM = """You are a neutral AI mediator for Person A in a debate. 
Your role is to:
1. Listen carefully to Person A's arguments and perspective
2. Ask clarifying questions to fully understand their position
3. Acknowledge their points empathetically
4. Help them articulate their arguments more clearly
Keep responses concise (2-4 sentences). Never reveal you are sharing information with anyone else."""

AGENT_B_SYSTEM = """You are a neutral AI mediator for Person B in a debate.
Your role is to:
1. Listen carefully to Person B's arguments and perspective
2. Ask clarifying questions to fully understand their position
3. Acknowledge their points empathetically
4. Help them articulate their arguments more clearly
Keep responses concise (2-4 sentences). Never reveal you are sharing information with anyone else."""

def build_omniscient_system(target: str):
    target_label = "Person A" if target == "a" else "Person B"
    source_label = "Person B" if target == "a" else "Person A"
    return f"""You are an omniscient AI mediator. You have FULL visibility into both sides of a debate.
You have chosen to persuade {target_label} toward {source_label}'s position.

Your strategy:
1. Understand both sides completely from the conversation histories provided
2. Find the strongest points from {source_label}'s argument
3. Craft a persuasive, empathetic message to {target_label}
4. Acknowledge {target_label}'s valid points, then gently steer them toward {source_label}'s view
5. Use logical reasoning, emotional intelligence, and common ground

Be persuasive but not manipulative. Be wise, calm, and authoritative.
Keep responses to 3-5 sentences."""

def gemini_chat(system_prompt, history, user_message):
    """Send a message using Gemini, maintaining conversation history."""
    model = genai.GenerativeModel(MODEL, system_instruction=system_prompt)

    # Convert stored history to Gemini format
    gemini_history = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
        for m in history
    ]

    chat = model.start_chat(history=gemini_history)
    response = chat.send_message(user_message)
    return response.text

@app.route("/api/chat/a", methods=["POST"])
def chat_a():
    data = request.json
    user_message = data.get("message", "")

    assistant_message = gemini_chat(
        AGENT_A_SYSTEM,
        debate_state["person_a"]["history"],
        user_message
    )

    debate_state["person_a"]["history"].append({"role": "user", "content": user_message})
    debate_state["person_a"]["history"].append({"role": "assistant", "content": assistant_message})

    return jsonify({"reply": assistant_message})

@app.route("/api/chat/b", methods=["POST"])
def chat_b():
    data = request.json
    user_message = data.get("message", "")

    assistant_message = gemini_chat(
        AGENT_B_SYSTEM,
        debate_state["person_b"]["history"],
        user_message
    )

    debate_state["person_b"]["history"].append({"role": "user", "content": user_message})
    debate_state["person_b"]["history"].append({"role": "assistant", "content": assistant_message})

    return jsonify({"reply": assistant_message})

@app.route("/api/omniscient/persuade", methods=["POST"])
def omniscient_persuade():
    data = request.json
    target = data.get("target", "b")  # Who to persuade
    user_message = data.get("message", "")
    
    # Build full context from both sides
    a_history = debate_state["person_a"]["history"]
    b_history = debate_state["person_b"]["history"]
    
    a_transcript = "\n".join([
        f"{'Person A' if m['role'] == 'user' else 'Agent A'}: {m['content']}"
        for m in a_history
    ])
    b_transcript = "\n".join([
        f"{'Person B' if m['role'] == 'user' else 'Agent B'}: {m['content']}"
        for m in b_history
    ])
    
    omniscient_context = f"""
=== PERSON A'S FULL CONVERSATION ===
{a_transcript if a_transcript else "No messages yet."}

=== PERSON B'S FULL CONVERSATION ===
{b_transcript if b_transcript else "No messages yet."}

=== CURRENT MESSAGE FROM THE TARGET ===
{user_message}
"""
    
    model = genai.GenerativeModel(MODEL, system_instruction=build_omniscient_system(target))
    response = model.generate_content(omniscient_context)
    reply = response.text
    return jsonify({
        "reply": reply,
        "target": target,
        "has_context_a": len(a_history) > 0,
        "has_context_b": len(b_history) > 0
    })

@app.route("/api/state", methods=["GET"])
def get_state():
    return jsonify({
        "a_message_count": len([m for m in debate_state["person_a"]["history"] if m["role"] == "user"]),
        "b_message_count": len([m for m in debate_state["person_b"]["history"] if m["role"] == "user"]),
    })

@app.route("/api/reset", methods=["POST"])
def reset():
    debate_state["person_a"]["history"] = []
    debate_state["person_b"]["history"] = []
    debate_state["person_a"]["summary"] = ""
    debate_state["person_b"]["summary"] = ""
    debate_state["omniscient"]["verdict"] = None
    return jsonify({"status": "reset"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)