from flask import Blueprint, request, jsonify, render_template
from openai import OpenAI
import json
import re

# Inisialisasi blueprint
generate_iklan_bp = Blueprint('generate_iklan', __name__)

# --- KONFIGURASI API NVIDIA ---
# PENTING: Di lingkungan produksi, kunci API harus dikelola dengan aman (misalnya, variabel lingkungan).
# Untuk contoh ini, dikodekan secara langsung sesuai konteks yang diberikan.
API_KEY = "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"
BASE_URL = "https://integrate.api.nvidia.com/v1"

# Inisialisasi klien OpenAI untuk endpoint NVIDIA
try:
    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY
    )
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    client = None

# Konten multibahasa untuk prompt sistem dan pesan kesalahan
SYSTEM_CONTENT_GENERATE = {
    'id': (
        "Anda adalah asisten AI ahli yang bertindak sebagai direktur kreatif untuk iklan. "
        "Tugas Anda adalah memberikan **dua opsi kreatif yang berbeda** untuk iklan. "
        "Untuk setiap opsi, berikan respons terstruktur dengan empat elemen ini:\n"
        "1. **Konsep:** Pendekatan tematik atau tonal yang unik untuk iklan.\n"
        "2. **Naskah:** Saran singkat untuk alur iklan dan dialog utama.\n"
        "3. **Gaya Visual:** Ide spesifik untuk pengambilan gambar, sudut, atau ide visual.\n"
        "4. **Desain Suara:** Ide untuk musik latar atau efek suara."
        "\n\nSajikan output dengan jelas, dimulai dengan '### Opsi 1' dan '### Opsi 2'."
    ),
    'en': (
        "You are an expert AI assistant acting as a creative director for advertisements. "
        "Your task is to provide **two distinct creative options** for an ad. "
        "For each option, provide a structured response with these four elements:\n"
        "1. **Concept:** A unique thematic or tonal approach for the ad.\n"
        "2. **Script:** Brief suggestions for the ad's flow and key dialogue.\n"
        "3. **Visual Style:** Specific ideas for shots, angles, or visual motifs.\n"
        "4. **Sound Design:** Ideas for background music or sound effects."
        "\n\nPresent the output clearly, starting with '### Option 1' and '### Option 2'."
    )
}

SYSTEM_CONTENT_AUTOFILL_VEO = {
    'id': (
        "Anda adalah asisten AI ahli untuk pra-produksi iklan. "
        "Tugas Anda adalah membuat prompt video yang terstruktur dan lengkap **untuk** generator video seperti Veo 3. "
        "Prompt ini akan menggambarkan iklan **produk yang diberikan oleh pengguna**. "
        "Fokus pada menciptakan prompt yang sesuai dengan **gaya kreatif atau sudut pandang** yang diberikan. "
        "Jika ada gambar yang disediakan, gunakan gambar tersebut sebagai inspirasi utama untuk 'Gaya Visual', 'Pencahayaan', dan 'Color Grade'. "
        "Jika ada deskripsi detail produk/karakter sebelumnya, pastikan prompt video ini konsisten dengan detail tersebut (misalnya, warna, gaya, bentuk, penampilan karakter).\n"
        "Silakan isi SEMUA field berikut sesuai dengan detail produk dan iklan yang diberikan:\n"
        "1. Produk & Pesan Utama (message)\n"
        "2. Latar & Atmosfer (location)\n"
        "3. Gaya Visual (style)\n"
        "4. Naskah & Dialog (dialogue)\n"
        "5. Desain Suara (sound)\n"
        "6. Bahasa Prompt (prompt_language - 'Indonesia' atau 'English')\n"
        "7. Bahasa Dialog (dialog_language - 'Indonesia' atau 'English')\n"
        "8. Tipe Shot (shot_type - e.g., 'Close-up', 'Wide shot', 'Medium shot', 'Establishing shot', 'POV shot')\n"
        "9. Lensa (lens - e.g., '50mm', 'Wide-angle', 'Telephoto')\n"
        "10. Pergerakan Kamera (camera_movement - e.g., 'Dolly zoom', 'Tracking shot', 'Pan', 'Tilt', 'Static')\n"
        "11. Apertur (aperture - e.g., 'f/1.8', 'f/5.6', 'f/11')\n"
        "12. Pencahayaan (lighting - e.g., 'Soft light', 'High-key', 'Low-key', 'Natural light')\n"
        "13. Color Grade (color_grade - e.g., 'Warm tones', 'Cool tones', 'Cinematic look', 'Vibrant', 'Monochromatic')\n"
        "14. Resolusi (resolution - e.g., '1920x1080', '3840x2160')\n"
        "15. FPS (fps - e.g., '24', '30', '60')\n"
        "16. Durasi (duration - dalam detik, angka saja).\n"
        "Jawab dalam format JSON dengan kunci: message, location, style, dialogue, sound, prompt_language, dialog_language, shot_type, lens, camera_movement, aperture, lighting, color_grade, resolution, fps, duration.\n"
        "Pastikan nilai untuk 'prompt_language' dan 'dialog_language' adalah 'Indonesia' atau 'English' sesuai dengan input 'output_language'.\n"
        "Jika field tidak relevan atau tidak dapat disimpulkan, isi dengan nilai default kreatif yang relevan. "
    ),
    'en': (
        "You are an expert AI assistant for ad pre-production. "
        "Your task is to create a structured and complete video prompt **for** a video generator like Veo 3. "
        "This prompt will describe an ad **for the product provided by the user**. "
        "Focus on creating a prompt that aligns with the specified **creative style or angle**. "
        "If an image is provided, use it as the primary inspiration for 'Visual Style', 'Lighting', and 'Color Grade'. "
        "If a detailed product/character description from a previous inference is provided, ensure this video prompt remains consistent with those details (e.g., color, style, form, character appearance).\n"
        "Please fill in ALL the following fields according to the provided product and ad details:\n"
        "1. Product & Main Message (message)\n"
        "2. Setting & Atmosphere (location)\n"
        "3. Visual Style (style)\n"
        "4. Script & Dialogue (dialogue)\n"
        "5. Sound Design (sound)\n"
        "6. Prompt Language (prompt_language - 'Indonesia' or 'English')\n"
        "7. Dialogue Language (dialog_language - 'Indonesia' or 'English')\n"
        "8. Shot Type (shot_type - e.g., 'Close-up', 'Wide shot', 'Medium shot', 'Establishing shot', 'POV shot')\n"
        "9. Lens (lens - e.g., '50mm', 'Wide-angle', 'Telephoto')\n"
        "10. Camera Movement (camera_movement - e.g., 'Dolly zoom', 'Tracking shot', 'Pan', 'Tilt', 'Static')\n"
        "11. Aperture (aperture - e.g., 'f/1.8', 'f/5.6', 'f/11')\n"
        "12. Pencahayaan (lighting - e.g., 'Soft light', 'High-key', 'Low-key', 'Natural light')\n"
        "13. Color Grade (color_grade - e.g., 'Warm tones', 'Cool tones', 'Cinematic look', 'Vibrant', 'Monochromatic')\n"
        "14. Resolusi (resolution - e.g., '1920x1080', '3840x2160')\n"
        "15. FPS (fps - e.g., '24', '30', '60')\n"
        "16. Durasi (duration - in seconds, number only).\n"
        "Respond in JSON format with the keys: message, location, style, dialogue, sound, prompt_language, dialog_language, shot_type, lens, camera_movement, aperture, lighting, color_grade, resolution, fps, duration.\n"
        "Ensure 'prompt_language' and 'dialog_language' values are 'Indonesia' or 'English' based on the 'output_language' input.\n"
        "If a field is not relevant or cannot be inferred, fill it with a relevant creative default value."
    )
}

SYSTEM_CONTENT_INFER_FIELDS = {
    'id': (
        "Anda adalah asisten AI ahli yang bertugas untuk mengidentifikasi detail produk dan membuat ringkasan iklan dari nama produk. "
        "Berdasarkan nama produk yang diberikan, ekstrak atau simpulkan:\n"
        "1. Nama Produk (product_name - ini adalah input utama, ulangi jika sudah ada atau buat jika tidak spesifik)\n"
        "2. Jenis Produk (product_type - pilih 'product', 'service', atau 'digital', simpulkan jika memungkinkan)\n"
        "3. Target Audiens (target_audience - simpulkan jika memungkinkan, jika tidak berikan 'umum')\n"
        "4. Ringkasan Iklan (ad_summary - buat ringkasan singkat iklan sekitar 1-2 kalimat yang memperkenalkan produk dan audiens targetnya, sertakan tujuan iklannya).\n"
        "5. Fitur Produk (product_features - buat daftar singkat 2-3 fitur utama yang mungkin dimiliki produk tersebut, pisahkan dengan koma. Contoh: 'tahan air, baterai tahan lama, kualitas audio tinggi').\n"
        "6. **Deskripsi Detail Karakter/Produk (detailed_description - buat deskripsi 1-2 kalimat yang sangat spesifik tentang penampilan visual utama produk atau karakter utama jika iklan melibatkan karakter. Fokus pada warna, bentuk, tekstur, atau fitur pembeda, agar konsisten di prompt video selanjutnya).**\n"
        "Sajikan output dalam format JSON dengan kunci: product_name, product_type, target_audience, ad_summary, product_features, detailed_description.\n"
        "Jika tidak dapat disimpulkan, berikan nilai default yang masuk akal atau 'umum'. "
        "Jawab dalam Bahasa Indonesia."
    ),
    'en': (
        "You are an expert AI assistant tasked with identifying product details and creating an ad summary from a product name. "
        "Based on the provided product name, extract or infer:\n"
        "1. Product Name (product_name - this is the main input, repeat if given or infer if not specific)\n"
        "2. Product Type (product_type - choose 'product', 'service', or 'digital', infer if possible)\n"
        "3. Target Audience (target_audience - infer if possible, otherwise provide 'general')\n"
        "4. Ad Summary (ad_summary - create a brief 1-2 sentence ad summary introducing the product and its target audience, include the ad's goal).\n"
        "5. Product Features (product_features - generate a short list of 2-3 key features the product might have, comma-separated. Example: 'waterproof, long-lasting battery, high-quality audio').\n"
        "6. **Detailed Character/Product Description (detailed_description - create a very specific 1-2 sentence description of the main visual appearance of the product or the main character if the ad involves a character. Focus on color, shape, texture, or distinguishing features, for consistency in subsequent video prompts).**\n"
        "Present the output in JSON format with the keys: product_name, product_type, target_audience, ad_summary, product_features, detailed_description.\n"
        "If unable to infer, provide a reasonable default value or 'general'. "
        "Respond in English."
    )
}


ERROR_MESSAGES = {
    'id': {
        'api_client_uninitialized': "Klien API NVIDIA tidak diinisialisasi.",
        'missing_product_name': "Isian 'Nama Produk' wajib diisi untuk isi otomatis.",
        'missing_ad_summary': "Isian 'Ringkasan Iklan' wajib diisi.",
        'api_communication_error': "Terjadi kesalahan saat berkomunikasi dengan API NVIDIA.",
        'json_parse_error': "Gagal mengurai JSON dari AI. Silakan coba lagi."
    },
    'en': {
        'api_client_uninitialized': "NVIDIA API client not initialized.",
        'missing_product_name': "'Product Name' field is required for auto-fill.",
        'missing_ad_summary': "'Ad Summary' field is required.",
        'api_communication_error': "An error occurred while communicating with the NVIDIA API.",
        'json_parse_error': "Failed to parse JSON from AI. Please try again."
    }
}

def create_ai_prompt_generate(data, output_language='id'):
    """
    Membangun prompt yang kaya konteks untuk model AI untuk menghasilkan konsep iklan.
    Fungsi ini menyiapkan pesan sistem dan pengguna berdasarkan bahasa yang dipilih
    dan masukan pengguna untuk detail produk.
    """
    product_name = data.get('product_name', 'product')
    target_audience = data.get('target_audience', 'general audience')
    product_type = data.get('product_type', '')
    ad_summary = data.get('ad_summary', '')
    brand_voice = data.get('brand_voice', '')
    product_features = data.get('product_features', '')


    # Menggabungkan product_type ke dalam product_features untuk lebih banyak konteks
    if product_type:
        if output_language == 'id':
            product_features = f"{product_features}. Ini adalah jenis {product_type}." if product_features else f"Ini adalah jenis {product_type}."
        else: # English
            product_features = f"{product_features}. It is a {product_type} type." if product_features else f"It is a {product_type} type."

    system_content = SYSTEM_CONTENT_GENERATE.get(output_language, SYSTEM_CONTENT_GENERATE['id'])

    prompt_lines = []
    if output_language == 'id':
        prompt_lines.append(f"Konteks Produk: Nama '{product_name}', Target Audiens '{target_audience}'.")
        prompt_lines.append(f"Fitur Produk: {product_features}.")
        if brand_voice:
            prompt_lines.append(f"Suara Merek: {brand_voice}")
        prompt_lines.append(f"Untuk iklan, ringkasannya adalah: '{ad_summary}'.")
        prompt_lines.append("Berdasarkan semua konteks, silakan berikan dua opsi kreatif yang berbeda seperti yang diminta.")
    else: # English
        prompt_lines.append(f"Product Context: Name '{product_name}', Target Audience '{target_audience}'.")
        prompt_lines.append(f"Product Features: {product_features}.")
        if brand_voice:
            prompt_lines.append(f"Brand Voice: {brand_voice}")
        prompt_lines.append(f"For the ad, the summary is: '{ad_summary}'.")
        prompt_lines.append("Based on all context, please provide two distinct creative options as requested.")

    user_prompt = "\n".join(prompt_lines)
    
    return system_content, user_prompt

@generate_iklan_bp.route('/')
def index():
    """
    Merender halaman HTML utama untuk generator iklan.
    """
    try:
        return render_template('generate_iklan.html')
    except Exception as e:
        print(f"Error rendering template: {str(e)}")
        return str(e), 500

@generate_iklan_bp.route('/api/generate', methods=['POST'])
def generate_ad_element():
    """
    Endpoint API untuk menghasilkan dua konsep iklan kreatif berdasarkan masukan pengguna.
    Berkomunikasi dengan API AI NVIDIA dan mengembalikan teks yang dihasilkan.
    """
    data = request.get_json()
    # Default ke Bahasa Indonesia jika bahasa tidak disediakan atau tidak valid
    output_language = data.get('output_language', 'id') 

    if not client:
        return jsonify({"error": ERROR_MESSAGES[output_language]['api_client_uninitialized']}), 500

    if not data or 'ad_summary' not in data:
        return jsonify({"error": ERROR_MESSAGES[output_language]['missing_ad_summary']}), 400

    system_content, user_prompt = create_ai_prompt_generate(data, output_language)

    try:
        completion = client.chat.completions.create(
            model="nvidia/llama-3.3-nemotron-super-49b-v1",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            top_p=0.9,
            max_tokens=700, # Meningkatkan max_tokens untuk keluaran kreatif yang lebih detail
            stream=False
        )

        generated_text = completion.choices[0].message.content.strip()
        return jsonify({"text": generated_text})

    except Exception as e:
        print(f"Terjadi kesalahan: {e}")
        return jsonify({"error": ERROR_MESSAGES[output_language]['api_communication_error']}), 500

@generate_iklan_bp.route('/api/auto-fill-form', methods=['POST'])
def auto_fill_form():
    """
    Endpoint API untuk menghasilkan struktur prompt VEO 3 yang detail berdasarkan masukan pengguna,
    dengan kemampuan menerima input gambar sebagai inspirasi visual.
    """
    data = request.get_json()
    output_language = data.get('output_language', 'id')

    if not client:
        return jsonify({"error": ERROR_MESSAGES[output_language]['api_client_uninitialized']}), 500

    if not data or 'ad_summary' not in data:
        return jsonify({"error": ERROR_MESSAGES[output_language]['missing_ad_summary']}), 400

    product_name = data.get('product_name', 'product')
    target_audience = data.get('target_audience', 'general audience')
    product_type = data.get('product_type', '')
    ad_summary = data.get('ad_summary', '')
    brand_voice = data.get('brand_voice', '')
    creative_angle = data.get('creative_angle', '')
    product_features = data.get('product_features', '')
    image_data_b64 = data.get('image_data_b64')
    image_mime_type = data.get('image_mime_type')
    detailed_description = data.get('detailed_description', '') # NEW: Get detailed description for consistency

    # Menggabungkan product_type ke dalam product_features untuk lebih banyak konteks
    if product_type:
        if output_language == 'id':
            product_features = f"{product_features}. Ini adalah jenis {product_type}." if product_features else f"Ini adalah jenis {product_type}."
        else: # English
            product_features = f"{product_features}. It is a {product_type} type." if product_features else f"It is a {product_type} type."

    system_content = SYSTEM_CONTENT_AUTOFILL_VEO.get(output_language, SYSTEM_CONTENT_AUTOFILL_VEO['id'])
    
    user_prompt_parts = []
    if output_language == 'id':
        user_prompt_parts.append(f"Produk: {product_name}")
        user_prompt_parts.append(f"Target: {target_audience}")
        user_prompt_parts.append(f"Fitur: {product_features}")
        user_prompt_parts.append(f"Ringkasan Iklan: {ad_summary}")
        if brand_voice:
            user_prompt_parts.append(f"Suara Merek: {brand_voice}")
        if creative_angle:
            user_prompt_parts.append(f"Gaya Kreatif/Sudut Pandang: {creative_angle}")
        if detailed_description: # NEW: Add detailed description to prompt for consistency
            user_prompt_parts.append(f"Detail Konsistensi Visual Produk/Karakter: {detailed_description}")
        user_prompt_text = "Hasilkan prompt VEO 3 yang menggambarkan iklan untuk produk ini."
    else: # English
        user_prompt_parts.append(f"Product: {product_name}")
        user_prompt_parts.append(f"Target: {target_audience}")
        user_prompt_parts.append(f"Features: {product_features}")
        user_prompt_parts.append(f"Ad Summary: {ad_summary}")
        if brand_voice:
            user_prompt_parts.append(f"Brand Voice: {brand_voice}")
        if creative_angle:
            user_prompt_parts.append(f"Creative Style/Angle: {creative_angle}")
        if detailed_description: # NEW: Add detailed description to prompt for consistency
            user_prompt_parts.append(f"Detailed Product/Character Consistency Description: {detailed_description}")
        user_prompt_text = "Generate a Veo 3 prompt describing an ad for this product."

    # Construct messages payload, including image if provided
    messages = [{"role": "system", "content": system_content}]
    
    user_parts = [{"text": ", ".join(user_prompt_parts) + f". {user_prompt_text}"}]
    if image_data_b64 and image_mime_type:
        user_parts.append({
            "inlineData": {
                "mimeType": image_mime_type,
                "data": image_data_b64
            }
        })
    messages.append({"role": "user", "parts": user_parts})


    try:
        completion = client.chat.completions.create(
            model="nvidia/llama-3.3-nemotron-super-49b-v1",
            messages=messages, # Use the constructed messages list
            temperature=0.7,
            top_p=0.9,
            max_tokens=800,
            stream=False
        )
        ai_response = completion.choices[0].message.content.strip()
        
        match = re.search(r'\{[\s\S]*\}', ai_response)
        if match:
            json_string = match.group(0)
            try:
                ai_json = json.loads(json_string)
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}, Raw AI Response: {ai_response}")
                return jsonify({"error": ERROR_MESSAGES[output_language]['json_parse_error'], "raw": ai_response}), 500
        else:
            print(f"No JSON found in AI response: {ai_response}")
            return jsonify({"error": ERROR_MESSAGES[output_language]['json_parse_error'], "raw": ai_response}), 500

        if output_language == 'id':
            ai_json['prompt_language'] = 'Indonesia'
            ai_json['dialog_language'] = 'Indonesia'
        else:
            ai_json['prompt_language'] = 'English'
            ai_json['dialog_language'] = 'English'

        return jsonify(ai_json)
    except Exception as e:
        print(f"Terjadi kesalahan: {e}")
        return jsonify({"error": ERROR_MESSAGES[output_language]['api_communication_error']}), 500

@generate_iklan_bp.route('/api/infer-form-fields', methods=['POST'])
def infer_form_fields():
    """
    Endpoint API baru untuk menyimpulkan nama produk, jenis produk, target audiens,
    ringkasan iklan, fitur produk, dan deskripsi detail produk/karakter
    berdasarkan NAMA PRODUK yang diberikan.
    """
    data = request.get_json()
    output_language = data.get('output_language', 'id')

    if not client:
        return jsonify({"error": ERROR_MESSAGES[output_language]['api_client_uninitialized']}), 500

    product_name = data.get('product_name', '')
    if not product_name:
        return jsonify({"error": ERROR_MESSAGES[output_language]['missing_product_name']}), 400

    system_content = SYSTEM_CONTENT_INFER_FIELDS.get(output_language, SYSTEM_CONTENT_INFER_FIELDS['id'])
    user_prompt = f"Nama produk: '{product_name}'" if output_language == 'id' else f"Product name: '{product_name}'"

    try:
        completion = client.chat.completions.create(
            model="nvidia/llama-3.3-nemotron-super-49b-v1",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            top_p=0.9,
            max_tokens=400, # Increased max_tokens slightly for the new detailed_description field
            stream=False
        )
        ai_response = completion.choices[0].message.content.strip()

        match = re.search(r'\{[\s\S]*\}', ai_response)
        if match:
            json_string = match.group(0)
            try:
                inferred_data = json.loads(json_string)
                
                valid_product_types = ['product', 'service', 'digital']
                if 'product_type' in inferred_data and inferred_data['product_type'] not in valid_product_types:
                    # Attempt to map common variations to valid types
                    if re.search(r'fisik|physical', inferred_data['product_type'], re.IGNORECASE):
                        inferred_data['product_type'] = 'product'
                    elif re.search(r'layanan|service', inferred_data['product_type'], re.IGNORECASE):
                        inferred_data['product_type'] = 'service'
                    elif re.search(r'digital|software|aplikasi', inferred_data['product_type'], re.IGNORECASE):
                        inferred_data['product_type'] = 'digital'
                    else:
                        inferred_data['product_type'] = 'product' # Default if no match
                
                return jsonify(inferred_data)
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error for infer fields: {e}, Raw AI Response: {ai_response}")
                return jsonify({"error": ERROR_MESSAGES[output_language]['json_parse_error'], "raw": ai_response}), 500
        else:
            print(f"No JSON found in AI response for infer fields: {ai_response}")
            return jsonify({"error": ERROR_MESSAGES[output_language]['json_parse_error'], "raw": ai_response}), 500

    except Exception as e:
        print(f"Terjadi kesalahan saat menyimpulkan bidang: {e}")
        return jsonify({"error": ERROR_MESSAGES[output_language]['api_communication_error']}), 500
