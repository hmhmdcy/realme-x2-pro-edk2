from pathlib import Path
import hashlib, json, re, struct

out=Path('/mnt/e/edk2-samurai-out/kernel111')
src=out/'source-files/k111-sensor-sources-readonly'
mdt=(src/'firmware/slpi.mdt').read_bytes()
assert mdt[:7]==b'\x7fELF\x01\x01\x01'
header=struct.unpack_from('<16sHHIIIIIHHHHHH',mdt)
phoff, phentsize, phnum=header[5],header[9],header[10]
assert phentsize==32 and phoff+phentsize*phnum<=len(mdt)
segments=[]
for index in range(phnum):
    typ,offset,virtual,physical,size,memsize,flags,align=struct.unpack_from('<IIIIIIII',mdt,phoff+index*phentsize)
    file=src/f'firmware/slpi.b{index:02d}'
    if size and typ==1 and ((flags>>24)&7)!=2:
        assert file.is_file() and file.stat().st_size==size
        segments.append(dict(index=index,offset=offset,physical=physical,file_bytes=size,
                             memory_bytes=memsize,flags=flags,sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
assert segments
# Source collection includes per-device calibration; only coarse facts leave this directory.
registry=src/'sensors-persist/registry/registry'
assert registry.is_dir()
configs=src/'sensors-vendor/config'
assert configs.is_dir()
models=['lsm6ds3c','mmc5603x','stk3331','stk2x3x']
model_files={model:[p.name for p in registry.rglob('*') if p.is_file() and model.lower() in p.name.lower()] for model in models}
assert model_files['lsm6ds3c'] and model_files['mmc5603x']
report=dict(firmware_program_headers=phnum,load_segments=len(segments),
            registry_files=sum(p.is_file() for p in registry.rglob('*')),
            vendor_config_files=sum(p.is_file() for p in configs.rglob('*')),
            present_stock_sensor_groups=[m for m,f in model_files.items() if f],
            source_partitions_unchanged=True,source_mounts_closed=True)
(out/'slpi-segments-private.json').write_text(json.dumps(segments,indent=2)+'\n')
(out/'sensor-registry-names-private.json').write_text(json.dumps(model_files,indent=2)+'\n')
(out/'sensor-source-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
