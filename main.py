from lib import download, mrpack2zip, extractzip, jsonparse, check_modloader, load_launcher_profiles, save_launcher_profiles, add_modpack_profile, download_modloader
import argparse
import logging
import shutil, os
from tqdm import tqdm
from typing import Optional

# region 

# endregion
logger = logging.getLogger(__name__)

def unpack_mrpack(input_mrpack_path, dryrun: bool=False, minecraft_dir: str="Default", profile_dir: Optional[str]=None, profile_name: Optional[str]=None):
    """
    Unpacks a .mrpack file and downloads its dependencies.
    
    Args:
        input_mrpack_path (str): Path to the .mrpack file to unpack
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
        minecraft_version = modloader.get('minecraft', 'unknown')
        modloader_type = modloader.get('type', 'unknown')
        modloader_version = modloader.get('version', 'unknown')
        
        # Default profile directory
        profile_dir = os.path.join(default_minecraft, profile_name)
        
        # Create modloader version string for launcher
        if modloader_type == 'fabric':
            launcher_version = f"fabric-loader-{modloader_version}-{minecraft_version}"
        elif modloader_type == 'forge':
            launcher_version = f"forge-{minecraft_version}-{modloader_version}"
        elif modloader_type == 'quilt':
            launcher_version = f"quilt-loader-{modloader_version}-{minecraft_version}"
        elif modloader_type == 'neoforge':
            launcher_version = f"neoforge-{modloader_version}"
        else:
            launcher_version = minecraft_version
        
        # Output clean JSON for programmatic use
        defaults = {
            "profile_name": profile_name,
            "version_id": version_id,
            "minecraft_dir": default_minecraft,
            "profile_dir": profile_dir
        }
        
        import json
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
    argp = argparse.ArgumentParser(description="A simple terminal program to unpack a .mrpack file")
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
