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
    shutil.copyfile(filepath, newfilename)
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
def check_modloader(deps: dict):
    result = {
        'type': 'unknown',
        'version': None,
        'minecraft': deps.get('minecraft')
    }
    if deps.get('fabric-loader') is not None:
        result['type'] = 'fabric'
        result['version'] = deps.get('fabric-loader')
    elif deps.get('forge') is not None:
        result['type'] = 'forge'
        result['version'] = deps.get('forge')
    elif deps.get('quilt-loader') is not None:
        result['type'] = 'quilt'
        result['version'] = deps.get('quilt-loader')
    elif deps.get('neoforge') is not None:
        result['type'] = 'neoforge'
        result['version'] = deps.get('neoforge')
    return result
# Import for download_modloader
import pathlib
import subprocess
def download_modloader(meta: dict, dotminecraftpath: str):
    if dotminecraftpath == "" or None: raise ValueError("installpath not provided")
    modLoaderJarPath = None
    if meta['type'] == 'fabric':
        print("Fabric is not currently supported! Skipping modloader installation.")
        download("https://maven.fabricmc.net/net/fabricmc/fabric-installer/1.1.0/fabric-installer-1.1.0.jar", ".tmp/fabric_installer.jar", )
        try: 
            subprocess.run(f"java -jar .tmp/fabric_installer.jar client -mcversion {meta['minecraft']} -loader {meta['version']} -dir {dotminecraftpath}")
        except Exception as e:
            return e
    elif meta['type'] == 'forge':
        print("Forge is not currently supported! Skipping modloader installation.")
    elif meta['type'] == 'quilt-loader':
        print("Quilt loader is not currently supported! Skipping modloader installation.")
    elif meta['type'] == 'neoforge':
        print("Neoforge is not currently supported! Skipping modloader installation.")
    return modLoaderJarPath

# Minecraft Launcher Profile Management (copilot made ts im sorry it's too annoying)
import uuid
from datetime import datetime
from typing import Optional

def load_launcher_profiles(minecraft_path: str):
    """Load the launcher_profiles.json file from the provided .minecraft directory"""
    launcher_path = os.path.join(minecraft_path, "launcher_profiles.json")
    
    if not os.path.exists(launcher_path):
        raise FileNotFoundError(f"launcher_profiles.json not found in {minecraft_path}")
    
    with open(launcher_path, 'r', encoding='utf-8') as f:
        return parse.load(f)

def save_launcher_profiles(profiles_data: dict, minecraft_path: str):
    """Save the launcher profiles data back to file"""
    launcher_path = os.path.join(minecraft_path, "launcher_profiles.json")
    
    with open(launcher_path, 'w', encoding='utf-8') as f:
        parse.dump(profiles_data, f, indent=2)

def add_modpack_profile(profiles_data: dict, profile_name: str, minecraft_version: str, 
                       modloader_version: str, game_dir: str, icon_base64: Optional[str] = None):
    """Add a new modpack profile to launcher profiles"""
    profile_id = str(uuid.uuid4())
    current_time = datetime.now().isoformat() + "Z"
    
    new_profile = {
        "name": profile_name,
        "type": "custom",
        "created": current_time,
        "lastUsed": current_time,
        "lastVersionId": modloader_version,
        "gameDir": game_dir
    }
    
    if icon_base64:
        new_profile["icon"] = icon_base64
    
    if "profiles" not in profiles_data:
        profiles_data["profiles"] = {}
    
    profiles_data["profiles"][profile_id] = new_profile
    return profile_id

if __name__ == "__main__":
    raise NotImplementedError("this is a library. you cant run it directly")