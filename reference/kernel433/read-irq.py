from pathlib import Path
import importlib.util,subprocess
import host
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('storage433irq',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);kernel=m.mounted_build().parent/'source354'
for name in ['camss-vfe-17x.c','camss-video.h','camss-video.c']:(host.PRIVATE/'kernel-before'/name).write_bytes((kernel/'drivers/media/platform/qcom/camss'/name).read_bytes())
