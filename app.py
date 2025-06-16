import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from openai import OpenAI

# Get the absolute path to the templates directory
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
print(f"Template directory path: {template_dir}")

# Inisialisasi aplikasi Flask
app = Flask(__name__, 
    template_folder=template_dir
)
# Mengizinkan request dari frontend (penting untuk pengembangan lokal)
CORS(app)

# Route untuk halaman utama
@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Error rendering template: {str(e)}")
        return str(e), 500

# --- KONFIGURASI API NVIDIA ---
# PERINGATAN: Menaruh API key langsung di kode tidak disarankan untuk produksi.
# Cara yang lebih aman adalah menggunakan environment variable.
API_KEY = "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" 
BASE_URL = "https://integrate.api.nvidia.com/v1"

# Inisialisasi client OpenAI untuk terhubung ke endpoint NVIDIA
try:
    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY
    )
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    client = None

# Fungsi untuk membuat prompt yang lebih cerdas untuk AI
def create_ai_prompt(data):
    """Membangun prompt yang kaya konteks untuk model AI."""
    project_title = data.get('project_title', 'sebuah film')
    genre = data.get('genre', 'umum')
    characters = data.get('characters', 'tidak ada karakter spesifik')
    scene_summary = data.get('scene_summary', '')
    previous_scene_context = data.get('previous_scene_context', '')

    # System prompt yang meminta AI memberikan DUA OPSI KREATIF
    system_content = (
        f"You are an expert AI assistant acting as a creative director for a {genre} film. "
        "Your task is to provide **two distinct creative options** for the user's scene summary. "
        "For each option, provide a structured response with these four elements:\n"
        "1. **Concept:** A unique thematic or tonal approach for the scene.\n"
        "2. **Action/Dialogue:** A brief suggestion for plot and a line of dialogue.\n"
        "3. **Cinematography:** A specific camera shot, angle, or lighting idea.\n"
        "4. **Sound Design:** An idea for ambient sound or music that fits the concept."
        "\n\nPresent the output clearly, starting with '### Option 1' and '### Option 2'."
    )

    # User prompt yang menggabungkan semua konteks
    prompt_lines = [
        f"Film Context: Title '{project_title}', Genre '{genre}'.",
        f"Characters involved: {characters}.",
    ]

    if previous_scene_context:
        prompt_lines.append(f"Context from the previous scene: {previous_scene_context}")
    
    prompt_lines.append(f"For the current scene, the summary is: '{scene_summary}'.")
    prompt_lines.append("Based on all context, please provide two distinct creative options as requested.")
    
    user_prompt = "\n".join(prompt_lines)
    
    return system_content, user_prompt


# Mendefinisikan endpoint API untuk diakses oleh frontend
@app.route('/api/generate', methods=['POST'])
def generate_story_element():
    if not client:
        return jsonify({"error": "NVIDIA API client not initialized."}), 500

    data = request.get_json()
    if not data or 'scene_summary' not in data:
        return jsonify({"error": "Request body must contain at least 'scene_summary'"}), 400

    system_content, user_prompt = create_ai_prompt(data)

    try:
        # Memanggil model AI NVIDIA dengan konteks yang lebih kaya
        completion = client.chat.completions.create(
            model="nvidia/llama-3.3-nemotron-super-49b-v1",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8, # Sedikit lebih kreatif
            top_p=0.9,
            max_tokens=500, # Token lebih banyak untuk dua opsi
            stream=False 
        )

        generated_text = completion.choices[0].message.content.strip()
        
        return jsonify({"text": generated_text})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An error occurred while communicating with the NVIDIA API."}), 500

@app.route('/api/auto-fill-form', methods=['POST'])
def auto_fill_form():
    if not client:
        return jsonify({"error": "NVIDIA API client not initialized."}), 500

    data = request.get_json()
    if not data or 'scene_summary' not in data:
        return jsonify({"error": "Request body must contain at least 'scene_summary'"}), 400

    # Ambil data penting
    project_title = data.get('project_title', 'sebuah film')
    genre = data.get('genre', 'umum')
    characters = data.get('characters', 'tidak ada karakter spesifik')
    scene_summary = data.get('scene_summary', '')
    previous_scene_context = data.get('previous_scene_context', '')
    output_language = data.get('output_language', 'id')  # default Indonesia

    # Prompt untuk AI agar mengisi seluruh field form
    if output_language == 'en':
        lang_instruction = "Respond in English."
    else:
        lang_instruction = "Jawab dalam Bahasa Indonesia."

    system_content = (
        f"You are an expert AI assistant for film pre-production. "
        f"Given the following context, fill in ALL the following fields for a video scene prompt: "
        f"1. Subject & Main Action\n2. Setting & Atmosphere\n3. Visual Style\n4. Dialogue (if any)\n5. Sound Design\n6. Prompt Language\n7. Dialogue Language\n8. Shot Type\n9. Lens\n10. Camera Movement\n11. Aperture\n12. Lighting\n13. Color Grade\n14. Resolution\n15. FPS\n16. Duration (seconds).\n"
        f"Respond in JSON format with keys: action, location, style, dialogue, sound, prompt_language, dialog_language, shot_type, lens, camera_movement, aperture, lighting, color_grade, resolution, fps, duration.\n"
        f"If a field is not relevant, fill with a creative default. {lang_instruction}"
    )
    user_prompt = f"Film: {project_title}, Genre: {genre}, Characters: {characters}. Scene: {scene_summary}. {('Previous scene: ' + previous_scene_context) if previous_scene_context else ''}"

    try:
        completion = client.chat.completions.create(
            model="nvidia/llama-3.3-nemotron-super-49b-v1",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            top_p=0.9,
            max_tokens=600,
            stream=False
        )
        ai_response = completion.choices[0].message.content.strip()
        # Coba parse JSON dari respons AI
        import json
        try:
            # Cari blok JSON di respons
            import re
            match = re.search(r'\{[\s\S]*\}', ai_response)
            if match:
                ai_json = json.loads(match.group(0))
            else:
                ai_json = json.loads(ai_response)
        except Exception as e:
            return jsonify({"error": "Gagal parsing JSON dari AI.", "raw": ai_response}), 500
        return jsonify(ai_json)
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An error occurred while communicating with the NVIDIA API."}), 500

# Menjalankan server saat script dieksekusi
if __name__ == '__main__':
    print("Starting Flask server at http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)

