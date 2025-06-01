import shutil
import os

folder_path = 'vids'

if os.path.exists(folder_path) and os.path.isdir(folder_path):
    shutil.rmtree(folder_path)
    print(f"Deleted folder")
else:
    print(f"vid Folder does not exist")