import os
import hashlib
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import List, Dict, Tuple, Optional, Union
import json
from datetime import datetime
import shutil

# Configure logging
logger = logging.getLogger('file_manager')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.FileHandler('file_manager.log')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

# Optimize hash performance with larger chunk size
HASH_CHUNK_SIZE = 262144  # 256KB

def get_file_hash(file_path: str) -> str:
    """
    Calculate SHA256 hash of a file with optimal chunk size.
    
    Args:
        file_path: Path to the file to hash
        
    Returns:
        SHA256 hash as a hexadecimal string
    """
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            # Read file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(HASH_CHUNK_SIZE), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except IOError as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error hashing file {file_path}: {str(e)}")
        raise

async def async_get_file_hash(file_path: str) -> str:
    """
    Asynchronously calculate SHA256 hash of a file.
    
    Args:
        file_path: Path to the file to hash
        
    Returns:
        SHA256 hash as a hexadecimal string
    """
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, get_file_hash, file_path)

def create_directory_if_not_exists(directory_path: str) -> None:
    """
    Create directory if it doesn't exist.
    
    Args:
        directory_path: Path to directory to create
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        logger.debug(f"Directory created or verified: {directory_path}")
    except OSError as e:
        logger.error(f"Error creating directory {directory_path}: {str(e)}")
        raise

async def generate_filelist(target_folder: str, exclusions: Optional[List[str]] = None) -> List[str]:
    """
    Generate a list of files with their hashes.
    
    Args:
        target_folder: Folder containing files to list
        exclusions: List of file patterns to exclude
        
    Returns:
        List of strings in format: "path/to/file,hash"
    """
    if not os.path.exists(target_folder):
        logger.error(f"Target folder does not exist: {target_folder}")
        raise FileNotFoundError(f"Target folder does not exist: {target_folder}")
    
    if exclusions is None:
        exclusions = ['.git', '__pycache__', '.vscode', '.idea', '.DS_Store']
    
    filelist = []
    tasks = []
    
    # Use a thread pool for file operations
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=min(32, (os.cpu_count() or 1) * 2))
    
    for root, dirs, files in os.walk(target_folder):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclusions]
        
        for file in files:
            # Skip excluded files
            if any(excl in file for excl in exclusions):
                continue
            
            filepath = os.path.join(root, file)
            relative_path = os.path.relpath(filepath, target_folder)
            
            # Schedule hashing task
            task = loop.run_in_executor(executor, get_file_hash, filepath)
            tasks.append((relative_path, task))
    
    # Wait for all hashing tasks to complete
    for relative_path, task in tasks:
        try:
            file_hash = await task
            filelist.append(f"{relative_path},{file_hash}")
            logger.debug(f"Processed file: {relative_path}")
        except Exception as e:
            logger.error(f"Error processing {relative_path}: {str(e)}")
    
    logger.info(f"Generated filelist with {len(filelist)} entries")
    return filelist

async def save_filelist(filelist: List[str], output_file: str) -> bool:
    """
    Save file list to a file.
    
    Args:
        filelist: List of strings in format "path/to/file,hash"
        output_file: Path to output file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure parent directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            create_directory_if_not_exists(output_dir)
        
        # Write to a temporary file first to prevent corruption
        temp_file = f"{output_file}.tmp"
        with open(temp_file, 'w') as f:
            for file_entry in filelist:
                f.write(f"{file_entry}\n")
        
        # Atomically replace the file
        shutil.move(temp_file, output_file)
        
        logger.info(f"File list saved to {output_file}")
        return True
    except IOError as e:
        logger.error(f"Error saving file list to {output_file}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving file list: {str(e)}")
        return False

def load_file_status(status_file: str) -> Dict:
    """
    Load file status information from JSON file.
    
    Args:
        status_file: Path to status JSON file
        
    Returns:
        Dictionary of file statuses
    """
    try:
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                return json.load(f)
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing file status JSON: {str(e)}")
        return {}
    except Exception as e:
        logger.error(f"Error loading file status: {str(e)}")
        return {}

def save_file_status(file_status: Dict, status_file: str) -> bool:
    """
    Save file status information to JSON file.
    
    Args:
        file_status: Dictionary of file statuses
        status_file: Path to status JSON file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create a temporary file first
        temp_file = f"{status_file}.tmp"
        with open(temp_file, 'w') as f:
            json.dump(file_status, f, indent=2)
        
        # Atomically replace the file
        shutil.move(temp_file, status_file)
        
        logger.info(f"File status saved to {status_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving file status: {str(e)}")
        return False

def update_file_status(filename: str, folder: str, filepath: str, status: str, status_file: str) -> Dict:
    """
    Update file status with new file information.
    
    Args:
        filename: Name of the file
        folder: Folder the file is in
        filepath: Full path to the file
        status: Status flag ('ON' or 'OFF')
        status_file: Path to status JSON file
        
    Returns:
        Updated file status dictionary
    """
    try:
        file_status = load_file_status(status_file)
        
        file_status[filename] = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'size': os.path.getsize(filepath),
            'sha256': get_file_hash(filepath),
            'status': status,
            'folder': folder
        }
        
        save_file_status(file_status, status_file)
        return file_status
    except Exception as e:
        logger.error(f"Error updating file status: {str(e)}")
        raise

def generate_patchlist_from_status(file_status: Dict, output_file: str) -> bool:
    """
    Generate patchlist file from file status dictionary.
    
    Args:
        file_status: Dictionary of file statuses
        output_file: Path to output file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(output_file, 'w') as f:
            for filename, details in file_status.items():
                # Only include files with 'ON' status
                if details.get('status') == 'ON':
                    filepath = f"{details['folder']}/{filename}" if details['folder'] != 'main' else filename
                    f.write(f"{filepath},{details['sha256']}\n")
        
        logger.info(f"Generated patchlist with {sum(1 for d in file_status.values() if d.get('status') == 'ON')} files")
        return True
    except Exception as e:
        logger.error(f"Error generating patchlist: {str(e)}")
        return False

def delete_file(filename: str, file_status: Dict, upload_folder: str, status_file: str) -> Tuple[bool, Dict]:
    """
    Delete a file and update file status.
    
    Args:
        filename: Name of the file to delete
        file_status: Dictionary of file statuses
        upload_folder: Base upload folder
        status_file: Path to status JSON file
        
    Returns:
        Tuple of (success, updated_file_status)
    """
    try:
        if filename not in file_status:
            logger.warning(f"File not found in status: {filename}")
            return False, file_status
        
        folder = file_status[filename]['folder']
        filepath = os.path.join(upload_folder, folder, filename)
        
        # Remove the file if it exists
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Deleted file: {filepath}")
        
        # Update the status dictionary
        del file_status[filename]
        save_file_status(file_status, status_file)
        
        return True, file_status
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {str(e)}")
        return False, file_status