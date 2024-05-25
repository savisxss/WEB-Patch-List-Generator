from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
from werkzeug.utils import secure_filename
import json
import hashlib
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['PATCHLIST_FILE'] = 'patcher.txt'
app.config['FILE_STATUS'] = 'file_status.json'

# Helper function to save file statuses
def save_file_status(file_status):
    with open(app.config['FILE_STATUS'], 'w') as f:
        json.dump(file_status, f)

# Helper function to load file statuses
def load_file_status():
    if os.path.exists(app.config['FILE_STATUS']):
        with open(app.config['FILE_STATUS'], 'r') as f:
            return json.load(f)
    return {}

# Helper function to generate file hash
def get_file_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

# Generate patchlist file based on file statuses
def generate_patchlist():
    file_status = load_file_status()
    with open(app.config['PATCHLIST_FILE'], 'w') as f:
        for filename, details in file_status.items():
            filepath = f"{details['folder']}/{filename}" if details['folder'] != 'main' else filename
            f.write(f"{filepath},{details['sha256']}\n")

@app.route('/')
def home():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    file_status = load_file_status()
    return render_template('dashboard.html', file_status=file_status)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'files[]' not in request.files:
            flash('No file part')
            return redirect(request.url)
        files = request.files.getlist('files[]')
        folder = request.form.get('folder', 'main')
        for file in files:
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            if file:
                filename = secure_filename(file.filename)
                upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], folder)
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                file_status = load_file_status()
                file_status[filename] = {
                    'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'size': os.path.getsize(filepath),
                    'sha256': get_file_hash(filepath),
                    'status': 'OFF',
                    'folder': folder
                }
                save_file_status(file_status)
        flash('Files successfully uploaded')
        return redirect(url_for('dashboard'))
    return render_template('dashboard.html')

@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.json
    filename = data['filename']
    status = data['status']
    file_status = load_file_status()
    if filename in file_status:
        file_status[filename]['status'] = status
        save_file_status(file_status)
        generate_patchlist()
        return jsonify(success=True)
    return jsonify(success=False), 404

@app.route('/delete_file', methods=['POST'])
def delete_file():
    data = request.json
    filename = data['filename']
    file_status = load_file_status()
    if filename in file_status:
        del file_status[filename]
        save_file_status(file_status)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        generate_patchlist()
        return jsonify(success=True)
    return jsonify(success=False), 404

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
