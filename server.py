import os
from flask import Flask, request, jsonify, send_from_directory
import anthropic

app = Flask(__name__, static_folder=".")

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


@app.route("/")
def landing():
    return send_from_directory(".", "landing.html")


@app.route("/dashboard")
def dashboard():
    return send_from_directory(".", "dashboard.html")


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True)
    prompt = data.get("prompt", "")
    content_type = data.get("type", "hook")
    audience = data.get("audience", "")
    offer = data.get("offer", "")
    platform = data.get("platform", "TikTok")

    system_prompt = (
        "Tu es un expert en short content et en génération de leads B2C/B2B. "
        "Tu crées des scripts vidéo courts (TikTok, Reels, Shorts) ultra-engageants "
        "qui transforment les vues en leads qualifiés. "
        "Tes scripts sont percutants, directs, et se terminent toujours par un CTA clair. "
        "Réponds uniquement avec le script, sans commentaires ni méta-instructions."
    )

    user_message = (
        f"Crée un script {content_type} pour {platform}.\n"
        f"Audience : {audience or 'entrepreneurs et créateurs de contenu'}\n"
        f"Offre : {offer or 'formation pour générer des leads avec le short content'}\n"
        f"Consigne supplémentaire : {prompt}\n\n"
        "Format : Hook (0-3s) → Corps (valeur/problème) → CTA (5-7s). "
        "Maximum 60 secondes de lecture à voix haute."
    )

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    result = message.content[0].text
    return jsonify({"result": result})


if __name__ == "__main__":
    print("🚀 ShortContentLeads server running on http://localhost:5000")
    print("   Landing  → http://localhost:5000/")
    print("   Dashboard → http://localhost:5000/dashboard")
    app.run(host="0.0.0.0", port=5000, debug=True)
