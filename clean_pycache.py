import os
import shutil


def remove_pycache_dirs(root_dir):
    removed = 0
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if "__pycache__" in dirnames:
            pycache_path = os.path.join(dirpath, "__pycache__")
            try:
                shutil.rmtree(pycache_path)
                print(f"Removed: {pycache_path}")
                removed += 1
            except Exception as e:
                print(f"Failed to remove {pycache_path}: {e}")
    return removed

def remove_pyc_pyo_files(root_dir):
    removed = 0
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.pyc') or filename.endswith('.pyo'):
                file_path = os.path.join(dirpath, filename)
                try:
                    os.remove(file_path)
                    print(f"Removed: {file_path}")
                    removed += 1
                except Exception as e:
                    print(f"Failed to remove {file_path}: {e}")
    return removed

def main():
    root = os.path.dirname(os.path.abspath(__file__))
    print(f"Cleaning Python cache files in: {root}")
    d = remove_pycache_dirs(root)
    f = remove_pyc_pyo_files(root)
    print(f"\n✅ Removed {d} __pycache__ directories and {f} .pyc/.pyo files.")

if __name__ == "__main__":
    main()
