"""Adapt the established health collector to current boot/module/package identities."""
from pathlib import Path
here=Path(__file__).resolve().parent
text=(here.parent/'kernel214/final-health.py').read_text();code=text.split("code=r'''",1)[1].split("'''",1)[0]
code=code.replace("out=root/'k214-final-health'","out=root/'k219-final-health-r2'").replace("base=root/'k214-baseline'","base=root/'k219-runtime'")
code=code.replace("root/'k214-package-transaction/", "root/'k219-r6-package-transaction/").replace("root/'k214-package-candidates/", "root/'k219-r6-package-candidates/")
code=code.replace("original=json.loads((base/'products-before-private.json').read_text())","original=json.loads((root/'k214-baseline/products-before-private.json').read_text())")
code=code.replace("if name.lstrip('/') not in paths:","if name.lstrip('/') not in paths and not name.endswith('/kernel/drivers/media/i2c/imx471.ko'):")
old="wp=Path('/proc',str(policy['new_pid']));assert (wp/'comm').read_text().strip()=='wireplumber' and 'libcamera.so' in (wp/'maps').read_text()"
new="""wps=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        if (p/'comm').read_text().strip()=='wireplumber' and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:wps.append(p)
    except OSError:pass
assert len(wps)==1;wp=wps[0];assert 'libcamera.so' in (wp/'maps').read_text()
for line in (wp/'maps').read_text().splitlines():
    if '/usr/lib/libcamera' in line:
        path=Path(line.split()[-1]);assert path.is_file()
        expected=[item['sha256'] for package in manifest['packages'] for name,item in package['files'].items() if name==str(path).lstrip('/') and item['kind']=='file'];assert len(expected)==1 and hashlib.sha256(path.read_bytes()).hexdigest()==expected[0]
import struct
module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/imx471.ko'
data=module.read_bytes();assert hashlib.sha256(data).hexdigest()=='e49dab26b05a325df8da64bb5c4b57c29cd51d1dcf15f5d4ed4dcb53033e66f1'
offset=struct.unpack_from('<Q',data,40)[0];size,count,strings=struct.unpack_from('<HHH',data,58)
headers=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*size) for i in range(count)];header=headers[strings];names=data[header[4]:header[4]+header[5]]
notes=[data[h[4]:h[4]+h[5]] for h in headers if names[h[0]:].split(b'\\0',1)[0]==b'.note.gnu.build-id'];assert len(notes)==1 and notes[0]==Path('/sys/module/imx471/notes/.note.gnu.build-id').read_bytes()
assert Path('/sys/module/imx471/parameters/unprocessed_fullres').read_text().strip()=='N'
assert Path('/sys/bus/i2c/devices/7-0010/of_node/port/endpoint/link-frequencies').read_bytes()==struct.pack('>QQQ',200000000,400000000,748800000)
before={}
for block in (root/'k219-r6-package-transaction/installed-before-private.txt').read_text().split('\\n\\n'):
    ns=[l[2:] for l in block.splitlines() if l.startswith('P:')]
    if ns:before[ns[0]]=block
after={}
for block in Path('/lib/apk/db/installed').read_text().split('\\n\\n'):
    ns=[l[2:] for l in block.splitlines() if l.startswith('P:')]
    if ns:after[ns[0]]=block
selected={p['name'] for p in manifest['packages']};assert set(after)==set(before) and all(after[name]==block for name,block in before.items() if name not in selected)
"""
assert code.count(old)==1;code=code.replace(old,new)
code=code.replace('stage=214,same_boot_after_package_upgrade=True,kernel183_and_boot211_unchanged=True,','stage=219,same_current219_boot=True,kernel183_and_boot219_deployment_retained=True,timing_module_file_and_loaded_note_verified=True,experimental_full_mode_disabled=True,unrelated_937_package_records_unchanged=True,')
start=code.index('for args,name in ');end=code.index('records={}',start)
assert 'k212-before-reboot/userspace-check.sha256' in code[start:end]
code=code[:start]+r'''
with (out/'nv-check-private.txt').open('wb') as log:
    subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=30)
legacy_checked=0;camera_owned=[];status=[]
for line in (root/'k212-before-reboot/userspace-check.sha256').read_text().splitlines():
    digest,name=line.split(maxsplit=1);name=name.lstrip(' *');p=Path(name)
    assert p.is_absolute() and len(digest)==64
    if name.lstrip('/') in paths:
        camera_owned.append(name);continue
    assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
    legacy_checked+=1;status.append(name+': OK')
assert '/etc/libcamera/configuration.yaml' in camera_owned
(out/'noncamera-product-check-private.txt').write_text('\n'.join(status)+'\n')
''' + code[end:]
code=code.replace('report=dict(stage=219,','report=dict(stage=219,legacy_non_camera_product_entries_verified=legacy_checked,camera_owned_legacy_entries_verified_against_current_signed_package=len(camera_owned),')
compile(code,'native-final-health219','exec')
wrapper="from pathlib import Path\nimport host,json\nhere=Path(__file__).resolve().parent\n"
wrapper+="for client in ['cam','gstreamer']:\n r=json.loads((here/('standard-'+client+'-validation.json')).read_text());assert r['program_exit']==0 and r['frame_count']==6\n"
wrapper+='code='+repr(code)+'\n'
wrapper+="p=host.ssh('python3 -',input=code.encode(),timeout=100)\n(host.PRIVATE/'final-health-host-private.log').write_bytes(p.stdout+p.stderr)\nr=json.loads(p.stdout);(here/'final-health-validation.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r))\n"
compile(wrapper,'final-health219','exec');(here/'final-health.py').write_text(wrapper)
print('Final collector prepared for current boot219/e49 module and r6/r1 stack')
