from pathlib import Path
import importlib.util,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
paths=['drivers/media/v4l2-core/v4l2-dev.c','drivers/media/v4l2-core/v4l2-device.c','drivers/media/mc/mc-devnode.c']
for relative in paths:
 out=P/'source'/relative;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes((source/relative).read_bytes())
print(json.dumps(dict(copied=paths)))
