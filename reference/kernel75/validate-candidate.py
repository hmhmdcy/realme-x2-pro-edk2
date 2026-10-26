from pathlib import Path
import hashlib, json, subprocess

ref=Path(__file__).resolve().parent
out=Path('/mnt/e/edk2-samurai-out/kernel75')
k=Path('/home/cy122/x2pro-linux/linux')
base=(ref.parent/'kernel73/verify-firmware.py').read_text()
ns={}
exec(base.split('\nimport runpy')[0].replace("'/mnt/e/edk2-samurai-out/kernel73'","'/mnt/e/edk2-samurai-out/kernel75'"),ns)
parse=ns['fdt_nodes']
before=parse((out/'firmware-before.dtb').read_bytes())
after=parse((out/'firmware-after.dtb').read_bytes())
assert before.keys()==after.keys()
changes=[]
for path in before:
    assert before[path].keys()==after[path].keys(),path
    for name,value in before[path].items():
        if value!=after[path][name]:
            changes.append({'path':path,'property':name,'before':value.hex(),'after':after[path][name].hex()})
assert len(changes)==3,changes
assert {c['property'] for c in changes}=={'status','firmware-name'}
for c in changes:
    if c['property']=='status':
        assert c['path'].endswith(('/gpu@2c00000','/gmu@2c6a000')),c
        assert bytes.fromhex(c['before'])==b'disabled\0' and bytes.fromhex(c['after'])==b'okay\0',c
    else:
        assert c['path'].endswith('/gpu@2c00000/zap-shader'),c
        assert bytes.fromhex(c['after'])==b'qcom/sm8150/realme/samurai/a640_zap.mbn\0',c
(out/'dtb-validation.json').write_text(json.dumps({'exactly_three_semantic_properties_changed':True,'changes':changes},indent=2)+'\n')
src=base.replace("root = Path(sys.argv[1]) if len(sys.argv)>1 else Path('/mnt/e/edk2-samurai-out/kernel73')","root = Path('/mnt/e/edk2-samurai-out/kernel75')")
src=src.replace("import runpy\nrunpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel73/validate-dtb.py')",'')
src=src.replace('boot-k73-display.img','boot-k75-gpu.img').replace("version_before='0819bd5'","version_before='bd23aaa'").replace("version_after='bd23aaa'","version_after='20a1d60'")
src=src.replace('native_display_dtb','gpu_gmu_status_and_board_zap_path')
(ref/'verify-firmware.py').write_text(src)
subprocess.run(['python3',str(ref/'verify-firmware.py')],check=True,stdout=(out/'firmware-audit.txt').open('w'))
subprocess.run(['python3',str(ref/'validate-initramfs.py')],check=True)
hashes=json.loads((ref/'sources-before.json').read_text())
preserved={}
for n,expected in hashes.items():
    if n.endswith('sm8150-samurai.dts'): continue
    src=Path('/home/cy122/x2pro-linux/initramfs')/('init' if n=='init' else 'usr/sbin/samurai-usb') if n in ('init','samurai-usb') else k/n
    actual=hashlib.sha256(src.read_bytes()).hexdigest()
    assert actual==expected,n
    preserved[n]=actual
(out/'core-preservation.json').write_text(json.dumps(preserved,indent=2)+'\n')
assert (k/'.config').read_bytes()==(out/'config-before').read_bytes()
manifest=json.loads((ref/'gpu-installed-manifest.json').read_text())
for name,item in manifest.items():
    src=Path('/home/cy122/x2pro-linux/initramfs/lib/firmware')/name
    assert hashlib.sha256(src.read_bytes()).hexdigest()==item['sha256']
artifacts={name:{'bytes':(out/name).stat().st_size,'sha256':hashlib.sha256((out/name).read_bytes()).hexdigest()} for name in ('boot-before.img','logdump-before.img','boot-k75-gpu.img','logdump-k75-gpu.img','Image-gpu','firmware-after.dtb')}
(out/'candidate-manifest.json').write_text(json.dumps(artifacts,indent=2)+'\n')
print('Candidate passes: exact DT changes, firmware FV/FFS/Android/gzip, unchanged kernel config, preserved EUD/touch/panel/DPU/init/SSH source.')
