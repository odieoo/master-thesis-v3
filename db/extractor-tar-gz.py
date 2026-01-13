import tarfile
import os

def is_within_directory(directory, target):
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)
    return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])

def safe_extract(tar, path="."):
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        if not is_within_directory(path, member_path):
            raise Exception("Unsafe tar file detected!")
    tar.extractall(path)

file_path = "ds21_mysql.tar.gz"
output_dir = "extracted_files"

with tarfile.open(file_path, "r:gz") as tar:
    safe_extract(tar, output_dir)

print("Safe extraction completed.")
