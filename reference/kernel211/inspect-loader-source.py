from pathlib import Path
import json
d=json.loads(Path('/mnt/e/edk2-samurai-out/kernel211/loader-and-rules-private.json').read_text())
print(d.get('/etc/init.d/modules','missing'))
print(json.dumps(dict(modules_config=d.get('/etc/modules'),modules_load_config_names=list(d.get('/etc/modules-load.d',{})),heap_video_rules=[dict(path=path,file=n,matching_lines=[l for l in t.splitlines() if 'dma_heap' in l or 'video4linux' in l]) for path,files in d.items() if isinstance(files,dict) and 'udev' in path for n,t in files.items()]),ensure_ascii=False))
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');text=(k/'drivers/media/i2c/imx471.c').read_text();start=text.index('static int imx471_set_pad_format');print(text[start:start+2400])
