from pathlib import Path
import importlib.util,json
import host
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
names=['drivers/media/common/videobuf2/videobuf2-dma-sg.c','drivers/media/common/videobuf2/videobuf2-vmalloc.c','drivers/media/common/videobuf2/videobuf2-core.c','include/media/videobuf2-core.h','include/linux/dma-resv.h','include/linux/dma-buf.h','drivers/dma-buf/dma-buf.c','drivers/media/platform/qcom/camss/camss-video.c']
for name in names:
 target=host.PRIVATE/'framework'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((source/name).read_bytes())
print(json.dumps(dict(files=names,configured_dma_sg=[line for line in (source.parent/'build/.config').read_text().splitlines() if 'CONFIG_VIDEOBUF2_DMA_SG=' in line])))
