import os
import hashlib

def create_directory_if_not_exists(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

def get_file_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def generate_filelist(target_folder):
    filelist = []
    for root, dirs, files in os.walk(target_folder):
        for file in files:
            filepath = os.path.join(root, file)
            file_hash = get_file_hash(filepath)
            relative_path = os.path.relpath(filepath, target_folder)
            filelist.append(f"{relative_path},{file_hash}")
    return filelist

def save_filelist(filelist, output_file):
    with open(output_file, 'w') as f:
        for file_entry in filelist:
            f.write(f"{file_entry}\n")
