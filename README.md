# WEB-Patch-List-Generator

A high-performance server component for the Patcher update system that provides a web interface for managing patch files and generating patchlists.

## 🚀 Features

- **Modern Dashboard:** Intuitive web interface to manage patch files
- **Multi-folder Support:** Organize files in main, pack, and custom folders
- **File Status Management:** Enable/disable files in the patchlist with simple toggles
- **Optimized File Processing:** Asynchronous operations for improved performance
- **Automatic Patchlist Generation:** Generate and serve patchlists for the Patcher client
- **Real-time Feedback:** Instant notifications for all operations
- **Server Monitoring:** View system stats and resource usage
- **RESTful API:** Access patchlists and status information programmatically

## 📋 Requirements

- Python 3.7 or higher
- Required packages (automatically installed):
  - Flask: Web framework
  - Gunicorn: Production WSGI server
  - Flask-WTF: Form handling with CSRF protection
  - Flask-CORS: Cross-Origin Resource Sharing support
  - python-dotenv: Environment variable management
  - psutil: System monitoring

## 🔧 Installation

### Quick Start

1. Clone the repository and navigate to the server directory:
   ```bash
   git clone https://github.com/savisxss/WEB-Patch-List-Generator.git
   cd WEB-Patch-List-Generator
   ```

2. Run the setup script:
   ```bash
   python server.py --setup
   ```

3. Start the server in development mode:
   ```bash
   python server.py --dev
   ```

4. Access the dashboard at http://localhost:5000

### Production Deployment

For production environments, it's recommended to use Gunicorn:

```bash
python server.py --prod
```

You can specify the number of worker processes:

```bash
python server.py --prod --workers 4
```

## ⚙️ Configuration

The server uses environment variables for configuration, which can be set in a `.env` file:

```
SECRET_KEY=your_secret_key
HOST=0.0.0.0
PORT=5000
DEBUG=false
UPLOAD_FOLDER=static/uploads
PATCHLIST_FILE=patcher.txt
FILE_STATUS=file_status.json
```

### Configuration Options

- **SECRET_KEY**: Secret key for session security (auto-generated if not set)
- **HOST**: Host address to bind the server to (default: 0.0.0.0)
- **PORT**: Port to listen on (default: 5000)
- **DEBUG**: Enable debug mode (default: false)
- **UPLOAD_FOLDER**: Directory for uploaded files (default: static/uploads)
- **PATCHLIST_FILE**: Path to generate the patchlist file (default: patcher.txt)
- **FILE_STATUS**: Path to file status JSON (default: file_status.json)

## 📁 API Endpoints

The server provides the following API endpoints:

- **GET /api/patchlist**: Get the current patchlist file
- **GET /api/regenerate_patchlist**: Force regeneration of the patchlist
- **GET /api/status**: Get server status information
- **POST /update_status**: Update file status (ON/OFF)
- **POST /delete_file**: Delete a file

## 🔄 Integration with Patcher Client

The Patcher client should be configured to use the server's patchlist endpoint:

1. Configure the Patcher client to use `http://your-server:5000/api/patchlist` as the `FILELIST_URL`
2. Set the `SERVER_URL` to the base URL of your server, e.g., `http://your-server:5000/static/uploads/`

## 🛠️ Development

To contribute to the development of the Patcher Server:

1. Set up a development environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Run the server in development mode:
   ```bash
   python server.py --dev
   ```

3. Make your changes and test thoroughly

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.