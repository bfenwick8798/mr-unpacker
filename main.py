from lib import download, mrpack2zip, extractzip, jsonparse, check_modloader
import argparse
import logging
import shutil, os
from tqdm import tqdm

# region 

# endregion
logger = logging.getLogger(__name__)

def unpack_mrpack(input_mrpack_path, dryrun: bool=False, profiledir: str="Default"):
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
    



if __name__ == "__main__":
    argp = argparse.ArgumentParser(description="A simple terminal program to unpack a .mrpack file")
    argp.add_argument("input_mrpack", help="Path to the mrpack file")
    argp.add_argument("-d", "--dryrun", action='store_true', help="Don't copy files, just unpack.")
    args = argp.parse_args()
    
    unpack_mrpack(args.input_mrpack, args.dryrun)
