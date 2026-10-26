"""Read retained OEM references and current candidate, without device changes."""
from pathlib import Path
import importlib.util, subprocess
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('storage284', HERE.parent/'kernel284/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
base = storage.mounted_build().parent
private = Path('/mnt/e/edk2-samurai-out/kernel422'); private.mkdir(mode=0o700, exist_ok=True)
hal = private.parent/'kernel281/camera.qcom.so-private'
for name, start, end in [('ltm-before-curves', 0x35e8c0, 0x35ec64),
                         ('ltm-scalars-inverse', 0x360c3c, 0x362774),
                         ('ltm-after-curves', 0x364598, 0x365860)]:
    data = subprocess.check_output(['aarch64-linux-gnu-objdump', '-d', '--start-address='+hex(start), '--stop-address='+hex(end), str(hal)])
    (private/(name+'-private.asm')).write_bytes(data)
source = private.parent/'kernel403/sources/ltm13setting.cpp'
lines = source.read_text().splitlines()
keys = ['CalculateHWSetting', 'pReserveType->', 'la_curve', 'mask_rect', 'weight_', 'LA_curve', 'LA_CURVE', 'IGamma', 'InverseGamma', 'RGB2Y']
for i,line in enumerate(lines):
    if any(k in line for k in keys):
        print(str(i+1)+': '+line)
tree=base/'libcamera421-frame-history/src/libcamera-v0.7.2'
for file in ['src/ipa/camss-vfe/camss.cpp','src/libcamera/pipeline/camss-vfe/camss_vfe.cpp','src/libcamera/pipeline/camss-vfe/ipe.cpp']:
    path=tree/file
    if not path.exists(): continue
    lines=path.read_text().splitlines()
    print('CANDIDATE',file)
    for i,line in enumerate(lines):
        if any(k in line for k in ['Ipe','ipe','ltm','Ltm']) and any(k in line for k in ['prepare','parameters','Parameters','Gamma','gamma','ltm','Ltm','bypass','Bypass']):
            print(str(i+1)+': '+line[:220])
