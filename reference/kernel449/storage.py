from pathlib import Path
import importlib.util
s=importlib.util.spec_from_file_location('storage448',Path(__file__).resolve().parents[1]/'kernel448/storage.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
mount=old.mount;SDK=old.SDK;candidate=old.candidate;sdk_candidate=old.sdk_candidate
