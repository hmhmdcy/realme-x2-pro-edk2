"""Build only the static DT; retain the installed363 Image and modules."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,time
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';state=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
assert not (P/'dt-build-private.log').exists()
image=P.parent/'kernel363/Image-k363-private';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((HERE.parent/'kernel363/boot-package-validation.json').read_text());assert sha(image)==old['image_sha256']
old_dtb=subprocess.check_output(['mcopy','-i',str(P.parent/'kernel363/logdump-k363-candidate-private.img'),'::/samurai.dtb','-'])
assert hashlib.sha256(old_dtb).hexdigest()==old['dtb_sha256']
(P/'dtb-before-private.dtb').write_bytes(old_dtb)
start=time.monotonic()
q=subprocess.run(['make','-C',str(source),'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','-j8','W=1','KERNELRELEASE='+old['release'],'qcom/sm8150-samurai.dtb'],capture_output=True)
(P/'dt-build-private.log').write_bytes(q.stdout+q.stderr);q.check_returncode()
dtb=build/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb';shutil.copyfile(dtb,P/'samurai365-private.dtb')
ns={};exec((HERE.parent/'kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],ns)
nodes=ns['fdt_nodes'](dtb.read_bytes());before=ns['fdt_nodes'](old_dtb)
icp=nodes['/soc@0/icp@ac10000'];camera=nodes['/reserved-memory/memory@9ab00000']
assert icp['status']==b'disabled\0' and icp['memory-region']==camera['phandle'] and camera['phandle']!=bytes(4)
assert icp['memory-region-names']==b'firmware\0' and 'no-map' in camera
assert camera['reg']==before['/reserved-memory/memory@9ab00000']['reg']
assert set(nodes)-set(before)=={'/soc@0/icp@ac10000'} and not set(before)-set(nodes)
changed={p:[key for key in before[p].keys()|nodes[p].keys() if before[p].get(key)!=nodes[p].get(key)] for p in before}
changed={p:keys for p,keys in changed.items() if keys}
# DTC can renumber existing phandles when the new hardware node references
# an existing supplier earlier. Verify every changed reference by target path.
exec(compile((HERE/'verify-dt.py').read_text(),str(HERE/'verify-dt.py'),'exec'))
