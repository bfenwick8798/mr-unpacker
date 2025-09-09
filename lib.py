import logging
logger = logging.getLogger(__name__)
# Json Parser
import json as parse
def jsonparse(json: str):
    dict = parse.loads(json)
    return(dict)
# File Downloader
import requests
import shutil
import os
from tqdm import tqdm
def download(url, path):
    logger.info(f"Downloading {url} to {path}")
    if url == "":
        raise ValueError("Supply a URL to download.")
    dir = os.path.dirname(path)
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        if not os.path.exists(dir):
            os.makedirs(dir)
        
        # Get file size for progress bar
        total_size = int(response.headers.get('content-length', 0))
        filename = os.path.basename(path)
        
        with open(path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=filename, leave=False) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

# Zip File Processor

def mrpack2zip(filepath: str):
    root, extension = os.path.splitext(filepath)
    newfilename = root + '.zip'
    os.rename(filepath, newfilename)
    return newfilename
import zipfile
def extractzip(zippath: str):
    try:
        with zipfile.ZipFile(zippath, mode="r") as zip_file:
            zip_file.extractall(".tmp")
    except zipfile.BadZipFile:
        print(f"Error: {zippath} is not a valid ZIP file")
    except FileNotFoundError:
        print(f"Error: {zippath} does not exist.")
    except Exception as e:
        print(f"Something went wrong!: {e}")
        pass
    

if __name__ == "__main__":
    raise NotImplementedError("This file has no base functionality. To use, import this file.")