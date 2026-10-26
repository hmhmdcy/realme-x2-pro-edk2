from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('storage449',Path(__file__).resolve().parents[1]/'kernel449/storage.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
mount=old.mount
