"""Guard existing ext4;490 uses only its new package area and never the SDK."""
from pathlib import Path
import importlib.util


def workspace():
    spec=importlib.util.spec_from_file_location('storage461_for490',Path(__file__).resolve().parents[1]/'kernel461/storage.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    return old.mount.mounted_build().parent/'camera490-package'
