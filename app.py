import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
import psutil
from flask_apscheduler import APScheduler
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Import our file management functions
from file_manager import (
    get_file_hash, async_get_file_hash, create_directory_if_not_exists,
    generate_filelist, save_filelist, load_file_status, save_file_status, 
    update_file_status, generate_patchlist_from_status, delete_file
)

# Configure logging
logging.basicConfig(
    filename='patcher_server.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Create Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change_this_in_production')
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', os.path.join('static', 'uploads'))
app.config['PATCHLIST_FILE'] = os.environ.get('PATCHLIST_FILE', 'patcher.txt')
app.config['FILE_STATUS'] = os.environ.get('FILE_STATUS', 'file_status.json')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max upload size
app.config['ALLOWED_EXTENSIONS'] = {'epk', 'eix', 'txt', 'zip', 'rar', 'tar', 'gz', 'bin', 'dat'}

# Setup CSRF protection and CORS
csrf = CSRFProtect(app)
CORS(app)

# Initialize scheduler for background tasks
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

def allowed_file(filename):
    """Check if a file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.before_first_request
def setup_directories():
    """Ensure required directories exist."""
    try:
        # Create upload folders
        create_directory_if_not_exists(app.config['UPLOAD_FOLDER'])
        create_directory_if_not_exists(os.path.join(app.config['UPLOAD_FOLDER'], 'main'))
        create_directory_if_not_exists(os.path.join(app.config['UPLOAD_FOLDER'], 'pack'))
        
        # Generate initial patchlist if needed
        if not os.path.exists(app.config['PATCHLIST_FILE']):
            file_status = load_file_status(app.config['FILE_STATUS'])
            generate_patchlist_from_status(file_status, app.config['PATCHLIST_FILE'])
            
        logger.info("Application initialized successfully")
    except Exception as e:
        logger.error(f"Error in setup: {str(e)}")

@scheduler.task('interval', id='regenerate_patchlist', seconds=300)
def scheduled_patchlist_regeneration():
    """Automatically regenerate patchlist every 5 minutes."""
    try:
        file_status = load_file_status(app.config['FILE_STATUS'])
        generate_patchlist_from_status(file_status, app.config['PATCHLIST_FILE'])
        logger.info("Scheduled patchlist regeneration completed")
    except Exception as e:
        logger.error(f"Error in scheduled patchlist regeneration: {str(e)}")

@app.route('/')
def home():
    """Redirect to dashboard."""
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """Render the dashboard with file statuses."""
    try:
        file_status = load_file_status(app.config['FILE_STATUS'])
        
        # Get system stats
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        total_space = disk.total // (1024 * 1024 * 1024)  # GB
        free_space = disk.free // (1024 * 1024 * 1024)  # GB
        
        system_stats = {
            'disk_percent': disk_percent,
            'total_space': total_space,
            'free_space': free_space,
            'total_files': len(file_status),
            'active_files': sum(1 for f in file_status.values() if f.get('status') == 'ON'),
        }
        
        return render_template(
            'dashboard.html', 
            file_status=file_status, 
            system_stats=system_stats
        )
    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}")
        flash(f"Error loading dashboard: {str(e)}", "error")
        return render_template('error.html', error=str(e))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Handle file uploads."""
    if request.method == 'POST':
        try:
            if 'files[]' not in request.files:
                flash('No file part', 'error')
                return redirect(request.url)
                
            files = request.files.getlist('files[]')
            folder = request.form.get('folder', 'main')
            
            # Validate folder name
            if folder not in ['main', 'pack', 'custom']:
                flash('Invalid folder selection', 'error')
                return redirect(request.url)
            
            # Create folder if not exists
            upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], folder)
            create_directory_if_not_exists(upload_folder)
            
            # Process each file
            file_status = load_file_status(app.config['FILE_STATUS'])
            uploaded_count = 0
            
            for file in files:
                if file.filename == '':
                    continue
                    
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(upload_folder, filename)
                    
                    # Save the file
                    file.save(filepath)
                    
                    # Update file status
                    file_status = update_file_status(
                        filename, folder, filepath, 'ON', 
                        app.config['FILE_STATUS']
                    )
                    uploaded_count += 1
                else:
                    flash(f'Skipped file with disallowed extension: {file.filename}', 'warning')
            
            # Generate new patchlist
            generate_patchlist_from_status(file_status, app.config['PATCHLIST_FILE'])
            
            if uploaded_count > 0:
                flash(f'{uploaded_count} files successfully uploaded', 'success')
            
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            logger.error(f"Error uploading files: {str(e)}")
            flash(f"Error uploading files: {str(e)}", "error")
            return redirect(url_for('dashboard'))
            
    # GET request
    return render_template('dashboard.html')

@app.route('/update_status', methods=['POST'])
def update_status():
    """Update file status (ON/OFF)."""
    try:
        data = request.json
        if not data or 'filename' not in data or 'status' not in data:
            return jsonify(success=False, error="Missing required fields"), 400
        
        filename = data['filename']
        status = 'ON' if data['status'] else 'OFF'
        
        # Load current status
        file_status = load_file_status(app.config['FILE_STATUS'])
        
        if filename not in file_status:
            return jsonify(success=False, error="File not found"), 404
        
        # Update status
        file_status[filename]['status'] = status
        save_file_status(file_status, app.config['FILE_STATUS'])
        
        # Regenerate patchlist
        generate_patchlist_from_status(file_status, app.config['PATCHLIST_FILE'])
        
        return jsonify(success=True)
        
    except Exception as e:
        logger.error(f"Error updating status: {str(e)}")
        return jsonify(success=False, error=str(e)), 500

@app.route('/delete_file', methods=['POST'])
def delete_file_route():
    """Delete a file and update status."""
    try:
        data = request.json
        if not data or 'filename' not in data:
            return jsonify(success=False, error="Missing filename"), 400
        
        filename = data['filename']
        
        # Load current status
        file_status = load_file_status(app.config['FILE_STATUS'])
        
        # Delete file and update status
        success, updated_status = delete_file(
            filename, file_status, app.config['UPLOAD_FOLDER'], 
            app.config['FILE_STATUS']
        )
        
        if not success:
            return jsonify(success=False, error="File deletion failed"), 404
        
        # Regenerate patchlist
        generate_patchlist_from_status(updated_status, app.config['PATCHLIST_FILE'])
        
        return jsonify(success=True)
        
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return jsonify(success=False, error=str(e)), 500

@app.route('/api/patchlist')
def serve_patchlist():
    """Serve the patchlist file."""
    try:
        with open(app.config['PATCHLIST_FILE'], 'r') as f:
            content = f.read()
        return content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except Exception as e:
        logger.error(f"Error serving patchlist: {str(e)}")
        return jsonify(error=str(e)), 500

@app.route('/api/regenerate_patchlist')
def regenerate_patchlist():
    """Force patchlist regeneration."""
    try:
        file_status = load_file_status(app.config['FILE_STATUS'])
        generate_patchlist_from_status(file_status, app.config['PATCHLIST_FILE'])
        return jsonify(success=True, message="Patchlist regenerated")
    except Exception as e:
        logger.error(f"Error regenerating patchlist: {str(e)}")
        return jsonify(success=False, error=str(e)), 500

@app.route('/api/status')
def server_status():
    """Return server status information."""
    try:
        # Get system stats
        disk = psutil.disk_usage('/')
        
        file_status = load_file_status(app.config['FILE_STATUS'])
        active_files = sum(1 for f in file_status.values() if f.get('status') == 'ON')
        
        status = {
            'server': 'running',
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'disk_usage_percent': disk.percent,
            'free_space_gb': disk.free // (1024 * 1024 * 1024),
            'total_files': len(file_status),
            'active_files': active_files,
            'patchlist_size_bytes': os.path.getsize(app.config['PATCHLIST_FILE']) if os.path.exists(app.config['PATCHLIST_FILE']) else 0
        }
        
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting server status: {str(e)}")
        return jsonify(error=str(e)), 500

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    logger.error(f"Server error: {str(e)}")
    return render_template('error.html', error="Server error. Please check the logs."), 500

if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    app.run(host=host, port=port, debug=debug)