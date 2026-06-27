import os
import sys
import argparse
import gdown

def download_drive_folder(folder_url, output_dir="input_images"):
    print(f"Initializing download from: {folder_url}")
    os.makedirs(output_dir, exist_ok=True)
    
    # Try downloading the folder via gdown
    try:
        gdown.download_folder(url=folder_url, output=output_dir, quiet=False, use_cookies=False)
        print(f"Download complete. Images saved to: {os.path.abspath(output_dir)}")
        # Check files downloaded
        downloaded_files = os.listdir(output_dir)
        print(f"Found {len(downloaded_files)} files in output directory.")
        for f in downloaded_files:
            print(f" - {f}")
    except Exception as e:
        print(f"Error downloading folder using gdown: {e}", file=sys.stderr)
        print("Please check if the folder is public and your internet connection is active.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download event photos from Google Drive folder.")
    parser.add_argument(
        "--url", 
        default="https://drive.google.com/drive/folders/1LjPfQljJ71lsA1gKo4ZN-SCHwBfxSyk9",
        help="Google Drive folder URL"
    )
    parser.add_argument(
        "--output",
        default="input_images",
        help="Output directory to save images"
    )
    
    args = parser.parse_args()
    download_drive_folder(args.url, args.output)
