from pathlib import Path
import shutil
import storage
HERE=Path(__file__).resolve().parent
shutil.copyfile(HERE/'ipa/lux_profile.cpp',storage.candidate()/'src/libcamera-v0.7.2/src/ipa/camss-vfe/lux_profile.cpp')
