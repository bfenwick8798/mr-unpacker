#!/usr/bin/env python3

### lib and main merged by copilot i'm tired man i don't want to do this anymore
import logging
import json as parse
import requests
import shutil
import os
from tqdm import tqdm
import zipfile
import pathlib
import subprocess
import uuid
from datetime import datetime
import argparse
from typing import Optional
import json

logger = logging.getLogger(__name__)

# === UTILITY FUNCTIONS ===

def jsonparse(json_str: str):
    """Parse JSON string and return dictionary"""
    dict_obj = parse.loads(json_str)
    return dict_obj

def download(url, path):
    """Download a file from URL to path with progress bar"""
    logger.info(f"Downloading {url} to {path}")
    if url == "":
        raise ValueError("Supply a URL to download.")
    dir_path = os.path.dirname(path)
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        # Get file size for progress bar
        total_size = int(response.headers.get('content-length', 0))
        filename = os.path.basename(path)
        
        with open(path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=filename, leave=False) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

def mrpack2zip(filepath: str):
    """Convert .mrpack file to .zip by copying and renaming"""
    root, extension = os.path.splitext(filepath)
    newfilename = root + '.zip'
    shutil.copyfile(filepath, newfilename)
    return newfilename

def extractzip(zippath: str):
    """Extract zip file to .tmp directory"""
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
    """Detect modloader type and version from dependencies"""
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

def download_modloader(meta: dict, dotminecraftpath: str):
    """Download and install modloader"""
    if dotminecraftpath == "" or dotminecraftpath is None: 
        raise ValueError("installpath not provided")
    modLoaderJarPath = None
    if meta['type'] == 'fabric':
        print(f"Installing Fabric {meta['version']}")
        download("https://maven.fabricmc.net/net/fabricmc/fabric-installer/1.1.0/fabric-installer-1.1.0.jar", ".tmp/fabric_installer.jar")
        try: 
            subprocess.run(f"java -jar .tmp/fabric_installer.jar client -mcversion {meta['minecraft']} -loader {meta['version']} -dir {dotminecraftpath}", shell=True, check=True)
        except Exception as e:
            print(f"Failed to install Fabric: {e}")
            return e
    elif meta['type'] == 'forge':
        print(f"Installing Forge {meta['version']} for Minecraft {meta['minecraft']}")
        # Forge installer URL format: https://maven.minecraftforge.net/net/minecraftforge/forge/{mc_version}-{forge_version}/forge-{mc_version}-{forge_version}-installer.jar
        forge_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{meta['minecraft']}-{meta['version']}/forge-{meta['minecraft']}-{meta['version']}-installer.jar"
        try:
            download(forge_url, ".tmp/forge_installer.jar")
            subprocess.run(f"java -jar .tmp/forge_installer.jar --installClient --installDir {dotminecraftpath}", shell=True, check=True)
        except Exception as e:
            print(f"Failed to install Forge: {e}")
            return e
    elif meta['type'] == 'quilt':
        print(f"Installing Quilt {meta['version']}")
        download("https://maven.quiltmc.org/repository/release/org/quiltmc/quilt-installer/1.0.0/quilt-installer-1.0.0.jar", ".tmp/quilt_installer.jar")
        try:
            subprocess.run(f"java -jar .tmp/quilt_installer.jar install client {meta['minecraft']} {meta['version']} --install-dir={dotminecraftpath}", shell=True, check=True)
        except Exception as e:
            print(f"Failed to install Quilt: {e}")
            return e
    elif meta['type'] == 'neoforge':
        print(f"Installing NeoForge {meta['version']}")
        # NeoForge installer URL format: https://maven.neoforged.net/releases/net/neoforged/neoforge/{version}/neoforge-{version}-installer.jar
        neoforge_url = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{meta['version']}/neoforge-{meta['version']}-installer.jar"
        try:
            download(neoforge_url, ".tmp/neoforge_installer.jar")
            subprocess.run(f"java -jar .tmp/neoforge_installer.jar --installClient --installDir {dotminecraftpath}", shell=True, check=True)
        except Exception as e:
            print(f"Failed to install NeoForge: {e}")
            return e
    return modLoaderJarPath

# === LAUNCHER PROFILE MANAGEMENT ===

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

# === MAIN FUNCTIONS ===

def unpack_mrpack(input_mrpack_path, dryrun: bool=False, minecraft_dir: str="Default", profile_dir: Optional[str]=None, profile_name: Optional[str]=None):
    """
    Unpacks a .mrpack file and downloads its dependencies.
    
    Args:
        input_mrpack_path (str): Path to the .mrpack file to unpack
        dryrun (bool): If True, only extract and download, don't install
        minecraft_dir (str): Path to .minecraft directory
        profile_dir (str): Directory to install the modpack
        profile_name (str): Name for the launcher profile
    """
    if os.path.isdir(".tmp"):
        print(".tmp folder found. Script may have been cancelled or crashed.")
        confirm = input("Delete it and continue? (y/N) ")
        if confirm.lower() == 'y':
            shutil.rmtree(".tmp")
        else:
            logger.warning(".tmp folder already exists! Aborting!")
            exit(1)

    zipfilepath = mrpack2zip(input_mrpack_path)
    try:
        extractzip(str(zipfilepath))
    except Exception as e:
        print(f"Failed to extract mrpack file: {e}")
        exit(1)
    try:
        with open(".tmp/modrinth.index.json") as f:
            dict_obj = jsonparse(f.read())
            if not isinstance(dict_obj, dict):
                dict_obj = dict(dict_obj)
    except Exception as e:
        print(f"Failed to access modrinth.index.json: {e}")
    if os.path.isdir("instance"):
        print("instance folder found. Script may have been cancelled or crashed.")
        confirm = input("Delete it and continue? (y/N) ")
        if confirm.lower() == 'y':
            shutil.rmtree("instance")
        else:
            logger.warning("instance folder already exists! Aborting!")
            exit(1)
    shutil.copytree(".tmp/overrides", "instance")

    files = dict_obj.get("files")
    try: 
        if files is not None:
            # Create progress bar for overall file download progress
            with tqdm(total=len(files), desc="Downloading files", unit="file") as overall_pbar:
                for i in files:
                    download(i["downloads"][0], f"instance/{i["path"]}")
                    overall_pbar.update(1)
        else:
            logger.critical("Invalid modrinth.index.json: No files entry")
    except Exception as e:
        logger.critical(f"Unable to download files: {e}")
    
    if dryrun == True:
        print("Files have been unpacked to ./instance")
        print("Cleaning up extra files...")
        try:
            shutil.rmtree('.tmp')
            os.remove(zipfilepath)
        except Exception as e:
            print(f"Couldn't cleanup temp files! Error: {e}")
            print(f"You may need to delete the .tmp folder and {zipfilepath}")
        print("Exiting due to dryrun being set.")
        exit(1)
    
    ## Now it's the fun part! Installing the profile into the Minecraft launcher
    deps = dict_obj["dependencies"]
    modloader = check_modloader(deps)
    # Determine .minecraft path based on OS if not provided
    if minecraft_dir == "Default":
        if os.name == "nt":
            dotminecraftpath = os.path.expandvars(r"%APPDATA%\.minecraft")
        elif os.name == "posix":
            dotminecraftpath = os.path.expanduser("~/.minecraft")
        else:
            logger.warning("Unknown OS, using current directory for .minecraft")
            dotminecraftpath = os.path.abspath(".minecraft")
    else:
        dotminecraftpath = minecraft_dir
    download_modloader(modloader, dotminecraftpath)
    
    # Load launcher profiles and add new modpack profile
    try:
        profiles_data = load_launcher_profiles(dotminecraftpath)
        
        # Use provided profile name or default from mrpack metadata
        actual_profile_name = profile_name if profile_name is not None else dict_obj.get("name", os.path.splitext(os.path.basename(input_mrpack_path))[0])
        
        # Determine instance/profile directory
        if profile_dir is None:
            instance_path = os.path.join(dotminecraftpath, actual_profile_name)
            # Copy instance to the profile directory
            if os.path.exists(instance_path):
                shutil.rmtree(instance_path)
            shutil.copytree("instance", instance_path)
        else:
            instance_path = os.path.abspath(profile_dir)
            # Copy instance to the specified directory
            if os.path.exists(instance_path):
                shutil.rmtree(instance_path)
            shutil.copytree("instance", instance_path)
        
        # Create modloader version string (format varies by type)
        if modloader['type'] == 'fabric':
            modloader_version = f"fabric-loader-{modloader['version']}-{modloader['minecraft']}"
        elif modloader['type'] == 'forge':
            modloader_version = f"forge-{modloader['minecraft']}-{modloader['version']}"
        elif modloader['type'] == 'quilt':
            modloader_version = f"quilt-loader-{modloader['version']}-{modloader['minecraft']}"
        elif modloader['type'] == 'neoforge':
            modloader_version = f"neoforge-{modloader['version']}"
        else:
            modloader_version = modloader['minecraft']  # Fallback to vanilla
        
        # Add the profile
        profile_id = add_modpack_profile(
            profiles_data, 
            actual_profile_name, 
            modloader['minecraft'], 
            modloader_version, 
            instance_path
        )
        
        # Save the updated profiles
        save_launcher_profiles(profiles_data, dotminecraftpath)
        
        print(f"Successfully created launcher profile: {actual_profile_name}")
        print(f"Profile ID: {profile_id}")
        
    except Exception as e:
        print(f"Failed to create launcher profile: {e}")
        print("The modpack was unpacked successfully, but you'll need to create the launcher profile manually.")

def get_defaults(input_mrpack_path):
    """
    Extract and display default options for the given mrpack file
    
    Args:
        input_mrpack_path (str): Path to the .mrpack file
    """
    try:
        # Temporarily extract to get metadata
        if os.path.isdir(".tmp"):
            shutil.rmtree(".tmp")
        
        zipfilepath = mrpack2zip(input_mrpack_path)
        extractzip(str(zipfilepath))
        
        # Parse metadata
        with open(".tmp/modrinth.index.json") as f:
            dict_obj = jsonparse(f.read())
            if not isinstance(dict_obj, dict):
                dict_obj = dict(dict_obj)
        
        # Get modloader info
        deps = dict_obj["dependencies"]
        modloader = check_modloader(deps)
        
        # Default .minecraft path based on OS
        if os.name == "nt":
            default_minecraft = os.path.expandvars(r"%APPDATA%\.minecraft")
        elif os.name == "posix":
            default_minecraft = os.path.expanduser("~/.minecraft")
        else:
            default_minecraft = os.path.abspath(".minecraft")
        
        # Extract defaults
        profile_name = dict_obj.get("name", os.path.splitext(os.path.basename(input_mrpack_path))[0])
        version_id = dict_obj.get("versionId", "1.0.0")
        
        # Default profile directory
        profile_dir = os.path.join(default_minecraft, profile_name)
        
        # Output clean JSON for programmatic use
        defaults = {
            "profile_name": profile_name,
            "version_id": version_id,
            "minecraft_dir": default_minecraft,
            "profile_dir": profile_dir
        }
        
        print(json.dumps(defaults, indent=2))
        
        # Clean up
        shutil.rmtree(".tmp")
        os.remove(zipfilepath)
        
    except Exception as e:
        print(f"Error getting defaults: {e}")
        # Clean up on error
        if os.path.isdir(".tmp"):
            shutil.rmtree(".tmp")
        if os.path.exists(zipfilepath):
            os.remove(zipfilepath)

if __name__ == "__main__":
    argp = argparse.ArgumentParser(description="mrunpack")
    argp.add_argument("input_mrpack", help="Path to the mrpack file")
    argp.add_argument("-d", "--dryrun", action='store_true', help="Don't copy files, just unpack.")
    argp.add_argument("--get-defaults", action='store_true', help="Show default options for the mrpack file and exit")
    argp.add_argument("--minecraft-dir", type=str, help="Path to .minecraft directory (auto-detected if not provided)")
    argp.add_argument("--profile-dir", type=str, help="Directory to install the modpack (default: .minecraft/{profile_name})")
    argp.add_argument("--profile-name", type=str, help="Name for the launcher profile (default: name from mrpack metadata)")
    args = argp.parse_args()
    
    if args.get_defaults:
        get_defaults(args.input_mrpack)
    else:
        # Prepare arguments for unpack_mrpack
        minecraft_dir = args.minecraft_dir if args.minecraft_dir else "Default"
        profile_dir = args.profile_dir
        profile_name = args.profile_name
        
        unpack_mrpack(args.input_mrpack, args.dryrun, minecraft_dir, profile_dir, profile_name)