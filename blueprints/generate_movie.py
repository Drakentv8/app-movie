from flask import Blueprint, request, jsonify, render_template
from openai import OpenAI
import json
import re

# Initialize blueprint
generate_movie_bp = Blueprint('generate_movie', __name__)

# --- KONFIGURASI API NVIDIA ---
API_KEY = "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" 
BASE_URL = "https://integrate.api.nvidia.com/v1"

# Initialize OpenAI client for NVIDIA endpoint
try:
    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY
    )
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    client = None

def create_ai_prompt(data):
    """Membangun prompt yang kaya konteks untuk model AI."""
    project_title = data.get('project_title', 'sebuah film')
    genre = data.get('genre', 'umum')
    characters = data.get('characters', 'tidak ada karakter spesifik')
    scene_summary = data.get('scene_summary', '')
    previous_scene_context = data.get('previous_scene_context', '')

    system_content = (
        f"Anda adalah asisten AI ahli yang bertindak sebagai direktur kreatif untuk film {genre}. "
        "Tugas Anda adalah memberikan **dua opsi kreatif yang berbeda** untuk ringkasan adegan pengguna. "
        "Untuk setiap opsi, berikan respons terstruktur dengan empat elemen ini:\n"
        "1. **Konsep:** Pendekatan tematik atau tonal yang unik untuk adegan.\n"
        "2. **Aksi/Dialog:** Saran singkat untuk plot dan satu baris dialog.\n"
        "3. **Sinematografi:** Ide spesifik untuk pengambilan gambar, sudut, atau pencahayaan.\n"
        "4. **Desain Suara:** Ide untuk suara ambien atau musik yang sesuai dengan konsep."
        "\n\nSajikan output dengan jelas, dimulai dengan '### Opsi 1' dan '### Opsi 2'."
    )

    prompt_lines = [
        f"Konteks Film: Judul '{project_title}', Genre '{genre}'.",
        f"Karakter yang terlibat: {characters}.",
    ]

    if previous_scene_context:
        prompt_lines.append(f"Konteks dari adegan sebelumnya: {previous_scene_context}")
    
    prompt_lines.append(f"Untuk adegan saat ini, ringkasannya adalah: '{scene_summary}'.")
    prompt_lines.append("Berdasarkan semua konteks, silakan berikan dua opsi kreatif yang berbeda seperti yang diminta.")
    
    user_prompt = "\n".join(prompt_lines)
    
    return system_content, user_prompt

@generate_movie_bp.route('/')
@generate_movie_bp.route('/generate-movie')
def index():
    try:
        return render_template('generate_movie.html')
    except Exception as e:
        print(f"Error rendering template: {str(e)}")
        return str(e), 500

@generate_movie_bp.route('/api/generate', methods=['POST'])
def generate_story_element():
    if not client:
        return jsonify({"error": "Klien API NVIDIA tidak diinisialisasi."}), 500

    data = request.get_json()
    if not data or 'scene_summary' not in data:
        return jsonify({"error": "Request body harus berisi minimal 'scene_summary'"}), 400

    system_content, user_prompt = create_ai_prompt(data)

    try:
        completion = client.chat.completions.create(
            model="nvidia/llama-3.3-nemotron-super-49b-v1",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            top_p=0.9,
            max_tokens=500,
            stream=False 
        )

        generated_text = completion.choices[0].message.content.strip()
        return jsonify({"text": generated_text})

    except Exception as e:
        print(f"Terjadi kesalahan: {e}")
        return jsonify({"error": "Terjadi kesalahan saat berkomunikasi dengan API NVIDIA."}), 500

@generate_movie_bp.route('/api/auto-fill-form', methods=['POST'])
def auto_fill_form():
    if not client:
        return jsonify({"error": "Klien API NVIDIA tidak diinisialisasi."}), 500

    data = request.get_json()
    if not data or 'scene_summary' not in data:
        return jsonify({"error": "Request body harus berisi minimal 'scene_summary'"}), 400

    project_title = data.get('project_title', 'sebuah film')
    genre = data.get('genre', 'umum')
    characters = data.get('characters', 'tidak ada karakter spesifik')
    scene_summary = data.get('scene_summary', '')
    previous_scene_context = data.get('previous_scene_context', '')
    output_language = data.get('output_language', 'id')

    if output_language == 'en':
        lang_instruction = "Respond in English."
    else:
        lang_instruction = "Jawab dalam Bahasa Indonesia."

    system_content = (
        f"Anda adalah asisten AI ahli untuk pra-produksi film. "
        f"Dengan konteks berikut, isi SEMUA field berikut untuk prompt adegan video: "
        f"1. Subjek & Aksi Utama\n2. Latar & Atmosfer\n3. Gaya Visual\n4. Dialog (jika ada)\n5. Desain Suara\n6. Bahasa Prompt\n7. Bahasa Dialog\n8. Tipe Shot\n9. Lensa\n10. Pergerakan Kamera\n11. Apertur\n12. Pencahayaan\n13. Color Grade\n14. Resolusi\n15. FPS\n16. Durasi (detik).\n"
        f"Jawab dalam format JSON dengan kunci: action, location, style, dialogue, sound, prompt_language, dialog_language, shot_type, lens, camera_movement, aperture, lighting, color_grade, resolution, fps, duration.\n"
        f"Jika field tidak relevan, isi dengan default kreatif. {lang_instruction}"
    )
    user_prompt = f"Film: {project_title}, Genre: {genre}, Karakter: {characters}. Adegan: {scene_summary}. {('Adegan sebelumnya: ' + previous_scene_context) if previous_scene_context else ''}"

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
        try:
            match = re.search(r'\{[\s\S]*\}', ai_response)
            if match:
                ai_json = json.loads(match.group(0))
            else:
                ai_json = json.loads(ai_response)
        except Exception as e:
            return jsonify({"error": "Gagal mengurai JSON dari AI.", "raw": ai_response}), 500
        return jsonify(ai_json)
    except Exception as e:
        print(f"Terjadi kesalahan: {e}")
        return jsonify({"error": "Terjadi kesalahan saat berkomunikasi dengan API NVIDIA."}), 500 