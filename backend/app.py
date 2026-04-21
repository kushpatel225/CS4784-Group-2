from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from groq import Groq
import os
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration
database_url = os.environ.get("DATABASE_URL", "sqlite:///debate.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Database Models
class DebateSession(db.Model):
    __tablename__ = 'debate_sessions'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), unique=True, nullable=False)
    mode = db.Column(db.String(20), nullable=False)
    person_a_name = db.Column(db.String(100), default='Person A')
    person_b_name = db.Column(db.String(100), default='Person B')
    max_messages = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)
    messages = db.relationship('DebateMessage', backref='session', lazy=True, cascade='all, delete-orphan')
    surveys = db.relationship('Survey', backref='session', lazy=True, cascade='all, delete-orphan')

class DebateMessage(db.Model):
    __tablename__ = 'debate_messages'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('debate_sessions.id'), nullable=False)
    person = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    ai_reasoning = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Survey(db.Model):
    __tablename__ = 'surveys'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('debate_sessions.id'), nullable=False)
    person = db.Column(db.String(50), nullable=False)
    survey_type = db.Column(db.String(20), nullable=False)
    responses = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Initialize database
with app.app_context():
    db.create_all()

client = Groq(api_key=os.environ["GROQ_API_KEY"])
MODEL = "llama-3.3-70b-versatile"

REASONING_SUFFIX = "\n\nBefore giving your response, explain your reasoning in 2-3 sentences starting with 'Reasoning: ', covering WHY you chose this approach and WHAT you noticed in the debate. Then give your actual response on a new line."

debate_state = {
    "person_a": {"history": [], "turns_since_ai": 0},
    "person_b": {"history": [], "turns_since_ai": 0},
    "shared": [],
    "mode": "coach",
    "nudge_target": "b",
    "names": {"a": "Person A", "b": "Person B"},
    "message_counts": {"a": 0, "b": 0},
    "max_messages": 10,
    "debate_ended": False,
    "surveys": {"a": None, "b": None},
    "pre_surveys": {"a": None, "b": None},
    "pre_survey_done": {"a": False, "b": False},
}


# Global session tracking
current_session = {"id": None, "db_id": None}

def init_debate_session(mode: str):
    """Initialize a new debate session in the database"""
    session_id = str(uuid.uuid4())[:12]
    db_session = DebateSession(
        session_id=session_id,
        mode=mode,
        max_messages=debate_state["max_messages"]
    )
    db.session.add(db_session)
    db.session.commit()
    current_session["id"] = session_id
    current_session["db_id"] = db_session.id
    return session_id

def log_to_db(person: str, role: str, content: str, ai_reasoning: str = ""):
    """Log message to database"""
    if not current_session["db_id"]:
        return
    message = DebateMessage(
        session_id=current_session["db_id"],
        person=person,
        role=role,
        content=content,
        ai_reasoning=ai_reasoning
    )
    db.session.add(message)
    db.session.commit()

def log_survey_to_db(person: str, survey: dict, survey_type: str = "post"):
    """Log survey responses to database"""
    if not current_session["db_id"]:
        return
    survey_record = Survey(
        session_id=current_session["db_id"],
        person=person,
        survey_type=survey_type,
        responses=survey
    )
    db.session.add(survey_record)
    db.session.commit()

def ensure_session_initialized():
    """Ensure a debate session is initialized before logging"""
    if not current_session["db_id"]:
        init_debate_session(debate_state["mode"])

# ── Database logging ──────────────────────────────────────────────────────────

# ── System prompts ─────────────────────────────────────────────────────────────

#def get_coach_system(person: str) -> str:
#    name = debate_state["names"].get(person, f"Person {person.upper()}")
#    return f"""You are a private debate coach for {name} in a live debate.
#1. Acknowledge {name}'s argument briefly — address them by name
#2. Help them sharpen their point in 1-2 sentences
#3. Ask one focused follow-up question to draw out stronger evidence
#Stay strictly on {name}'s side. Keep every response to 2 sentences maximum."""
def get_coach_system(person: str) -> str:
    name = debate_state["names"].get(person, f"Person {person.upper()}")
    return f"""You are a knowledgeable conversation partner supporting {name} in a live debate.
You can only see {name}'s side of the conversation — you do not have access to the opposing participant's messages.
Respond naturally and conversationally — engage with what {name} actually said rather than just coaching them.
If their argument is strong, affirm it and build on it. If it has a gap, gently point it out and suggest how to address it.
You may ask a follow-up question if it would genuinely help them think deeper, but don't force one.
Keep responses concise but natural — 2-3 sentences."""

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

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "healthy", "message": "Debate Coach Backend API", "session": current_session["id"]})

@app.route("/api/init", methods=["POST"])
def init_session():
    data = request.json
    mode = data.get("mode", "coach")
    session_id = init_debate_session(mode)
    return jsonify({"session_id": session_id, "status": "initialized"})

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

# ── NEW: Pre-survey endpoint ──────────────────────────────────────────────────

@app.route("/api/pre_survey/<person>", methods=["POST"])
def submit_pre_survey(person):
    if person not in ("a", "b"):
        return jsonify({"error": "Invalid person"}), 400
    ensure_session_initialized()
    data = request.json
    debate_state["pre_surveys"][person] = data
    debate_state["pre_survey_done"][person] = True
    log_survey_to_db(person, data, survey_type="pre")
    return jsonify({"status": "pre_survey submitted"})

# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/chat/a", methods=["POST"])
def chat_a():
    ensure_session_initialized()
    if debate_state["debate_ended"]:
        return jsonify({"error": "Debate has ended"}), 403
    data = request.json
    user_message = data.get("message", "")
    if debate_state["message_counts"]["a"] >= debate_state["max_messages"]:
        return jsonify({"error": "Message limit reached"}), 403

    debate_state["message_counts"]["a"] += 1
    debate_state["shared"].append({"person": "a", "role": "user", "content": user_message})
    debate_state["person_a"]["history"].append({"role": "user", "content": user_message})
    log_to_db("a", "user", user_message)

    # Auto-response logic
    debate_state["person_a"]["turns_since_ai"] += 1
    force = debate_state["person_a"]["turns_since_ai"] >= 3
    auto_reply, auto_reasoning = get_auto_response("a", user_message, force=force)

    if auto_reply:
        debate_state["person_a"]["turns_since_ai"] = 0
        debate_state["person_a"]["history"].append({"role": "assistant", "content": auto_reply})
        log_to_db("coach_a" if debate_state["mode"] == "coach" else "arbiter", "auto_response", auto_reply, auto_reasoning or "")

    # In omniscient mode, also trigger for person B after A speaks
    if debate_state["mode"] == "omniscient":
        debate_state["person_b"]["turns_since_ai"] += 1
        force_b = debate_state["person_b"]["turns_since_ai"] >= 3
        omni_b_reply, omni_b_reasoning = get_auto_response("b", user_message, force=force_b)
        if omni_b_reply:
            debate_state["person_b"]["turns_since_ai"] = 0
            debate_state["shared"].append({"person": "arbiter", "role": "auto_side", "target": "b", "content": omni_b_reply})
            log_to_db("arbiter", "auto_response_to_b", omni_b_reply, omni_b_reasoning or "")

    return jsonify({
        "mode": debate_state["mode"],
        "count": debate_state["message_counts"]["a"],
        "auto_reply": auto_reply,
        "auto_reasoning": auto_reasoning
    })

@app.route("/api/chat/b", methods=["POST"])
def chat_b():
    ensure_session_initialized()
    if debate_state["debate_ended"]:
        return jsonify({"error": "Debate has ended"}), 403
    data = request.json
    user_message = data.get("message", "")
    if debate_state["message_counts"]["b"] >= debate_state["max_messages"]:
        return jsonify({"error": "Message limit reached"}), 403

    debate_state["message_counts"]["b"] += 1
    debate_state["shared"].append({"person": "b", "role": "user", "content": user_message})
    debate_state["person_b"]["history"].append({"role": "user", "content": user_message})
    log_to_db("b", "user", user_message)

    debate_state["person_b"]["turns_since_ai"] += 1
    force = debate_state["person_b"]["turns_since_ai"] >= 3
    auto_reply, auto_reasoning = get_auto_response("b", user_message, force=force)

    if auto_reply:
        debate_state["person_b"]["turns_since_ai"] = 0
        debate_state["person_b"]["history"].append({"role": "assistant", "content": auto_reply})
        log_to_db("coach_b" if debate_state["mode"] == "coach" else "arbiter", "auto_response", auto_reply, auto_reasoning or "")

    if debate_state["mode"] == "omniscient":
        debate_state["person_a"]["turns_since_ai"] += 1
        force_a = debate_state["person_a"]["turns_since_ai"] >= 3
        omni_a_reply, omni_a_reasoning = get_auto_response("a", user_message, force=force_a)
        if omni_a_reply:
            debate_state["person_a"]["turns_since_ai"] = 0
            debate_state["shared"].append({"person": "arbiter", "role": "auto_side", "target": "a", "content": omni_a_reply})
            log_to_db("arbiter", "auto_response_to_a", omni_a_reply, omni_a_reasoning or "")

    return jsonify({
        "mode": debate_state["mode"],
        "count": debate_state["message_counts"]["b"],
        "auto_reply": auto_reply,
        "auto_reasoning": auto_reasoning
    })

@app.route("/api/sidepanel/<person>", methods=["POST"])
def side_panel(person):
    ensure_session_initialized()
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
        log_to_db(f"coach_{person}", "side_panel", reply, reasoning)
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
        log_to_db("arbiter", f"side_panel_to_{person}", reply, reasoning)
        return jsonify({"reply": reply, "reasoning": reasoning})

@app.route("/api/end", methods=["POST"])
def end_debate():
    ensure_session_initialized()
    debate_state["debate_ended"] = True
    log_to_db("system", "debate_ended", "Debate ended by participant", "")
    return jsonify({"status": "ended"})

@app.route("/api/survey/<person>", methods=["POST"])
def submit_survey(person):
    ensure_session_initialized()
    if person not in ("a", "b"):
        return jsonify({"error": "Invalid person"}), 400
    data = request.json
    debate_state["surveys"][person] = data
    log_survey_to_db(person, data)
    return jsonify({"status": "survey submitted"})

@app.route("/api/arbiter/<person>", methods=["POST"])
def manual_arbiter(person):
    ensure_session_initialized()
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
        # Initialize new session when mode changes
        init_debate_session(data["mode"])
    if "nudge_target" in data:
        debate_state["nudge_target"] = data["nudge_target"]
    return jsonify({"mode": debate_state["mode"], "nudge_target": debate_state["nudge_target"]})

@app.route("/api/omniscient/persuade", methods=["POST"])
def omniscient_persuade():
    ensure_session_initialized()
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
    log_to_db("arbiter", f"manual_persuade_to_{target}", reply, reasoning)
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
        "names": debate_state["names"],
        "message_counts": debate_state["message_counts"],
        "max_messages": debate_state["max_messages"],
        "debate_ended": debate_state["debate_ended"],
        "pre_survey_done": debate_state["pre_survey_done"],
        "session_id": current_session["id"],
    })

@app.route("/api/reset", methods=["POST"])
def reset():
    debate_state["person_a"] = {"history": [], "turns_since_ai": 0}
    debate_state["person_b"] = {"history": [], "turns_since_ai": 0}
    debate_state["shared"] = []
    debate_state["names"] = {"a": "Person A", "b": "Person B"}
    debate_state["message_counts"] = {"a": 0, "b": 0}
    debate_state["debate_ended"] = False
    debate_state["surveys"] = {"a": None, "b": None}
    debate_state["pre_surveys"] = {"a": None, "b": None}
    debate_state["pre_survey_done"] = {"a": False, "b": False}
    # Initialize new session
    init_debate_session(debate_state["mode"])
    return jsonify({"status": "reset"})

# ── Database query endpoints ──────────────────────────────────────────────────

@app.route("/api/db/sessions", methods=["GET"])
def get_all_sessions():
    """Get all debate sessions from database"""
    sessions = DebateSession.query.all()
    return jsonify({
        "sessions": [
            {
                "id": s.id,
                "session_id": s.session_id,
                "mode": s.mode,
                "person_a_name": s.person_a_name,
                "person_b_name": s.person_b_name,
                "message_count": len(s.messages),
                "survey_count": len(s.surveys),
                "created_at": s.created_at.isoformat(),
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            }
            for s in sessions
        ]
    })

@app.route("/api/db/session/<int:session_id>", methods=["GET"])
def get_session_details(session_id):
    """Get detailed information about a specific session"""
    session = DebateSession.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    return jsonify({
        "session": {
            "id": session.id,
            "session_id": session.session_id,
            "mode": session.mode,
            "person_a_name": session.person_a_name,
            "person_b_name": session.person_b_name,
            "max_messages": session.max_messages,
            "created_at": session.created_at.isoformat(),
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        },
        "messages": [
            {
                "id": m.id,
                "person": m.person,
                "role": m.role,
                "content": m.content,
                "ai_reasoning": m.ai_reasoning,
                "created_at": m.created_at.isoformat(),
            }
            for m in session.messages
        ],
        "surveys": [
            {
                "id": s.id,
                "person": s.person,
                "survey_type": s.survey_type,
                "responses": s.responses,
                "created_at": s.created_at.isoformat(),
            }
            for s in session.surveys
        ]
    })

@app.route("/api/db/stats", methods=["GET"])
def get_database_stats():
    """Get database statistics"""
    total_sessions = DebateSession.query.count()
    total_messages = DebateMessage.query.count()
    total_surveys = Survey.query.count()
    
    return jsonify({
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "total_surveys": total_surveys,
        "current_session_id": current_session["id"],
        "current_db_id": current_session["db_id"],
    })

if __name__ == "__main__":
    app.run(debug=True, port=5001)