import os
import re
import sys
import time
import shutil
import requests
import gdown

# Google Drive folder details
FOLDER_URL = "https://drive.google.com/drive/folders/1LjPfQljJ71lsA1gKo4ZN-SCHwBfxSyk9"
BASE_DIR = "input_images"

def get_prefix(filename: str) -> str:
    """Extracts the alphabetic prefix of a filename (e.g., _ASL9923.jpg -> ASL)."""
    name = filename.lstrip('_')
    match = re.match(r'^([a-zA-Z]+)', name)
    if match:
        return match.group(1).upper()
    return "OTHERS"

def download_file_with_requests(file_id: str, output_path: str):
    """Downloads a file from Google Drive using requests with a browser User-Agent header."""
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    session = requests.Session()
    response = session.get(url, headers=headers, stream=True, timeout=30)
    
    # Handle download warnings / confirmation cookies
    confirm_token = None
    for k, v in response.cookies.items():
        if k.startswith("download_warning"):
            confirm_token = v
            break
            
    if confirm_token:
        confirm_url = f"https://drive.google.com/uc?export=download&confirm={confirm_token}&id={file_id}"
        response = session.get(confirm_url, headers=headers, stream=True, timeout=30)
        
    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code}: Unable to download file.")
        
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

def separate_existing_images():
    """Moves existing images in input_images/ to their respective prefix subfolders."""
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR, exist_ok=True)
        return
        
    print("Reorganizing existing files in input_images/...")
    files = [f for f in os.listdir(BASE_DIR) if os.path.isfile(os.path.join(BASE_DIR, f))]
    
    for f in files:
        prefix = get_prefix(f)
        dest_dir = os.path.join(BASE_DIR, prefix)
        os.makedirs(dest_dir, exist_ok=True)
        
        src_path = os.path.join(BASE_DIR, f)
        dest_path = os.path.join(dest_dir, f)
        
        shutil.move(src_path, dest_path)
        print(f"Moved {f} -> {prefix}/")

def crawl_drive_and_download():
    """
    Crawls the Google Drive folder webpage to extract all file IDs,
    downloads any missing files with retries, and moves them to prefix folders.
    """
    print("\nStarting Google Drive folder crawl to fetch remaining images...")
    
    # Extract folder ID
    match = re.search(r'folders/([a-zA-Z0-9-_]+)', FOLDER_URL)
    if not match:
        print("Invalid Google Drive folder URL.")
        return
    folder_id = match.group(1)
    
    # We can use gdown's internal helper to get all files in a folder
    try:
        print("Retrieving file list from Google Drive folder...")
        # Resolve files using gdown
        files_info = gdown.download_folder(
            url=FOLDER_URL,
            output=BASE_DIR,
            quiet=True,
            skip_download=True
        )
        
        if not files_info:
            print("No files found or unable to list folder contents.")
            return
            
        print(f"Total files discovered in Drive folder: {len(files_info)}")
        
        # Download each file with retry & sleep to bypass rate limits
        for idx, file_item in enumerate(files_info):
            file_id = file_item.id
            file_name = file_item.path
            
            # Determine destination based on prefix
            prefix = get_prefix(file_name)
            dest_dir = os.path.join(BASE_DIR, prefix)
            os.makedirs(dest_dir, exist_ok=True)
            
            final_path = os.path.join(dest_dir, file_name)
            
            # Check if file already exists in the folder
            if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
                print(f"[{idx+1}/{len(files_info)}] {file_name} already exists. Skipping.")
                continue
                
            print(f"[{idx+1}/{len(files_info)}] Downloading {file_name} to {prefix}/...")
            
            # Download file using requests with browser headers
            temp_path = os.path.join(BASE_DIR, file_name)
            
            retries = 3
            success = False
            for attempt in range(retries):
                try:
                    download_file_with_requests(file_id, temp_path)
                    if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                        # Move to subfolder
                        shutil.move(temp_path, final_path)
                        print(f" -> Successfully saved to {final_path}")
                        success = True
                        break
                except Exception as e:
                    print(f" -> Attempt {attempt+1} failed: {e}")
                    time.sleep(3) # Wait before retry
            
            if not success:
                print(f" -> [ERROR] Failed to download {file_name} after {retries} attempts.")
                
            # Add a small delay between file downloads to respect Google Drive rate limits
            time.sleep(2.0)
            
    except Exception as e:
        print(f"Error crawling folder: {e}")

if __name__ == "__main__":
    separate_existing_images()
    crawl_drive_and_download()
    print("\nAll downloads and reorganization completed!")
