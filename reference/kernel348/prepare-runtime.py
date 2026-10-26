from pathlib import Path
import hashlib,io,json,struct,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'register-validation.json').read_text())['passed']
assert json.loads((HERE/'probe-build-validation.json').read_text())['passed']
build=json.loads((HERE/'kernel-build-validation.json').read_text());assert build['exit_code']==0 and not build['diagnostics'] and build['intree']=='Y'
raw=Path(build['module']).read_bytes();shoff=struct.unpack_from('<Q',raw,40)[0];stride,count,strings=struct.unpack_from('<HHH',raw,58)
sections=[struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*stride) for i in range(count)];names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
note=next(s for s in sections if names[s[0]:].split(b'\0')[0]==b'.note.gnu.build-id')
proof=dict(module_sha256=hashlib.sha256(raw).hexdigest(),module_note_sha256=hashlib.sha256(raw[note[4]:note[4]+note[5]]).hexdigest())
(P/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
s=(HERE.parent/'kernel334/native-probe.py').read_text().replace('stage=334','stage=348').replace('Loaded CCM module differs','Loaded Gamma module differs')
s=s.replace("str(root/'bin/samurai-ccm')","str(root/'bin/samurai-gamma')").replace("str(root/'factory-ccm-private.bin')","str(root/'factory-gamma-private.bin')").replace("t.count('CCM_FRAME ')","t.count('GAMMA_FRAME ')")
(HERE/'native-probe.py').write_text(s)
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
files={'qcom-camss.ko':Path(build['module']),'worker.py':HERE/'native-probe.py','proof.json':P/'proof.json',
 'factory-gamma-private.bin':P/'factory-gamma-private.bin','pipeline-fixture':P.parent/'kernel313/pipeline-fixture',
 'bin/samurai-gamma':P/'samurai-gamma','bin/gst-hardware-probe':sdk/'private/camss316-runtime/gst-hardware-probe'}
with tarfile.open(P/'probe.tar.gz','w:gz') as tar:
 for name,path in files.items():
  data=path.read_bytes();item=tarfile.TarInfo(name);item.size=len(data);item.mode=0o700 if name.startswith('bin/') or name=='pipeline-fixture' else 0o600;tar.addfile(item,io.BytesIO(data))
for name in ['launch-probe.py','poll-probe.py','fetch-pattern.py']:
 text=(HERE.parent/'kernel334'/name).read_text().replace('k334-ccm-','k348-gamma-');(HERE/name).write_text(text)
text=(HERE.parent/'kernel334/final-state.py').read_text().replace('stage=334','stage=348');(HERE/'final-state.py').write_text(text)
(HERE/'runtime-build-validation.json').write_text(json.dumps(dict(stage=348,temporary_camss_module=True,installed_userspace_reused=True,
 module_bytes=len(raw),**proof,factory_payload_private=True,passed=True),indent=2)+'\n')
print('Prepared temporary348 module experiment; deployed338 module and existing services will be restored.')
