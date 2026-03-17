from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("GEMINI_API_KEY"))

try:
    client.models.list()  # Lightweight endpoint
    print("Valid key!")
except Exception as e:
    print("Invalid key:", e)

app = Flask(__name__)

# Test if backend works.
@app.route("/")
def index():
    return "Backend is running!"

# Test if key works
@app.route("/test")
def test():
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Say hello!"}]
    )
    return jsonify({"reply": response.choices[0].message.content})

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=data["messages"]
    )
    return jsonify({"reply": response.choices[0].message.content})

if __name__ == "__main__":
    app.run(debug=True)