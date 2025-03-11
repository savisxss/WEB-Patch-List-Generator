import os
import sys
import argparse
import logging
import secrets
from dotenv import load_dotenv
import psutil

# Load environment variables
load_dotenv()

def check_requirements():
    """Check if all required packages are installed."""
    try:
        import flask
        import werkzeug
        import flask_wtf
        import flask_cors
        import gunicorn
        print("✓ All dependencies found")
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Installing required dependencies...")
        
        try:
            import pip
            pip.main(['install', '-r', 'requirements.txt'])
            print("✓ Dependencies installed successfully")
            return True
        except Exception as e:
            print(f"✗ Failed to install dependencies: {e}")
            return False

def check_system_resources():
    """Check if system has sufficient resources."""
    print("Checking system resources...")
    
    # Check CPU
    cpu_count = psutil.cpu_count()
    print(f"✓ CPU cores: {cpu_count}")
    
    # Check memory
    memory = psutil.virtual_memory()
    memory_gb = memory.total / (1024 ** 3)
    print(f"✓ Memory: {memory_gb:.1f} GB")
    
    # Check disk space
    disk = psutil.disk_usage('.')
    disk_gb = disk.free / (1024 ** 3)
    print(f"✓ Free disk space: {disk_gb:.1f} GB")
    
    # Check if we have enough resources
    if memory_gb < 1:
        print("⚠ Warning: Low memory may affect performance")
    
    if disk_gb < 1:
        print("⚠ Warning: Low disk space may cause issues")
        
    return True

def setup_environment():
    """Setup environment variables if not already set."""
    env_file = '.env'
    
    # Create .env file if it doesn't exist
    if not os.path.exists(env_file):
        print(f"Creating {env_file} file...")
        
        with open(env_file, 'w') as f:
            f.write(f"SECRET_KEY={secrets.token_hex(16)}\n")
            f.write("HOST=0.0.0.0\n")
            f.write("PORT=5000\n")
            f.write("DEBUG=false\n")
            f.write("UPLOAD_FOLDER=static/uploads\n")
            f.write("PATCHLIST_FILE=patcher.txt\n")
            f.write("FILE_STATUS=file_status.json\n")
        
        print(f"✓ Created {env_file} file with default settings")
    else:
        print(f"✓ Using existing {env_file} file")
    
    # Reload environment variables
    load_dotenv()
    
    # Create upload folders
    upload_folder = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
    os.makedirs(os.path.join(upload_folder, 'main'), exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'pack'), exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'custom'), exist_ok=True)
    print(f"✓ Created upload directories")
    
    return True

def run_development_server():
    """Run the Flask development server."""
    from app import app
    
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    print(f"Starting development server on {host}:{port} (debug={debug})")
    app.run(host=host, port=port, debug=debug, use_reloader=True)

def run_production_server(workers):
    """Run the Gunicorn production server."""
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    
    # Set optimal worker count if not specified
    if workers <= 0:
        # Gunicorn recommends (2 x $num_cores) + 1
        workers = (psutil.cpu_count() * 2) + 1
    
    print(f"Starting production server on {host}:{port} with {workers} workers")
    
    # Build command for subprocess
    cmd = [
        'gunicorn',
        '--bind', f'{host}:{port}',
        '--workers', str(workers),
        '--log-level', 'info',
        '--access-logfile', 'access.log',
        '--error-logfile', 'error.log',
        'app:app'
    ]
    
    # Execute gunicorn
    os.execvp('gunicorn', cmd)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Patcher Server')
    parser.add_argument('--dev', action='store_true', help='Run in development mode')
    parser.add_argument('--prod', action='store_true', help='Run in production mode')
    parser.add_argument('--workers', type=int, default=0, help='Number of Gunicorn workers (production only)')
    parser.add_argument('--setup', action='store_true', help='Setup environment only')
    
    args = parser.parse_args()
    
    print("Patcher Server - Management Script")
    print("==================================")
    
    # Check requirements
    if not check_requirements():
        return 1
    
    # Check system resources
    if not check_system_resources():
        return 1
    
    # Setup environment
    if not setup_environment():
        return 1
    
    # If setup only, exit
    if args.setup:
        print("✓ Setup completed successfully")
        return 0
    
    # Determine run mode
    if args.dev and args.prod:
        print("Error: Cannot specify both --dev and --prod")
        return 1
    
    if args.dev:
        run_development_server()
    elif args.prod:
        run_production_server(args.workers)
    else:
        # Default to development mode
        print("No mode specified, defaulting to development mode")
        run_development_server()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())