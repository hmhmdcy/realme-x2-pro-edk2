from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('storage418',Path(__file__).resolve().parent.parent/'kernel418/storage.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
SDK=previous.SDK
candidate=previous.candidate
sdk_candidate=previous.sdk_candidate
