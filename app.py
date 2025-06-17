import os
from flask import Flask, render_template
from flask_cors import CORS

# Get the absolute path to the templates directory
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
print(f"Template directory path: {template_dir}")

# Initialize Flask app
app = Flask(__name__, 
    template_folder=template_dir
)
CORS(app)

# Import blueprints
from blueprints.generate_movie import generate_movie_bp
from blueprints.generate_iklan import generate_iklan_bp

# Register blueprints
app.register_blueprint(generate_movie_bp, url_prefix='/generate-movie')
app.register_blueprint(generate_iklan_bp, url_prefix='/generate-iklan')

# Route for landing page
@app.route('/')
def landing():
    return render_template('landing.html')

if __name__ == '__main__':
    print("Starting Flask server at http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)


