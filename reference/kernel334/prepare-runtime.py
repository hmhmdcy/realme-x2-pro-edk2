from pathlib import Path
import hashlib,io,json,struct,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'register-validation.json').read_text())['passed']
assert json.loads((HERE/'probe-build-validation.json').read_text())['passed']
build=json.loads((HERE/'kernel-build-validation.json').read_text());assert build['exit_code']==0 and not build['diagnostics'] and build['intree']=='Y'
module=Path(build['module']);raw=module.read_bytes();shoff=struct.unpack_from('<Q',raw,40)[0];stride,count,strings=struct.unpack_from('<HHH',raw,58)
sections=[struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*stride) for i in range(count)];names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
note=next(s for s in sections if names[s[0]:].split(b'\0')[0]==b'.note.gnu.build-id')
proof=dict(module_sha256=hashlib.sha256(raw).hexdigest(),module_note_sha256=hashlib.sha256(raw[note[4]:note[4]+note[5]]).hexdigest())
(P/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
s=(HERE.parent/'kernel318/native-probe.py').read_text().replace('stage=318','stage=334')
s=s.replace('if (p/\'comm\').read_text().strip()==name:', 'if (p/\'comm\').read_text().strip()==name and (p/\'stat\').read_text().rsplit(\')\',1)[1].split()[0]!=\'Z\':')
s=s.replace('import json, os, pwd, select, signal, subprocess, sys, time, traceback','import hashlib, json, os, pwd, select, signal, subprocess, sys, time, traceback')
s=s.replace("before=subprocess.check_output(['dmesg'])", "before=subprocess.check_output(['dmesg'])\nproof=json.loads((root/'proof.json').read_text())\nbefore_note=hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest()")
needle="    run(['insmod',str(root/'qcom-camss.ko')],'load-candidate')"
assert needle in s;s=s.replace(needle,needle+"\n    if hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest()!=proof['module_note_sha256']:raise RuntimeError('Loaded CCM module differs')")
s=s.replace("str(root/'bin/samurai-lsc'),'--pattern',str(root/'pattern-private')", "str(root/'bin/samurai-ccm'),'--pattern',str(root/'pattern-private'),str(root/'factory-ccm-private.bin')")
s=s.replace("t.count('LSC_FRAME ')","t.count('CCM_FRAME ')")
needle='        restored=True';assert needle in s
s=s.replace(needle,"        restored=hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest()==before_note\n        if not restored:raise RuntimeError('Restored module differs')")
(HERE/'native-probe.py').write_text(s)
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
files={'qcom-camss.ko':module,'worker.py':HERE/'native-probe.py','proof.json':P/'proof.json','factory-ccm-private.bin':P/'factory-ccm-private.bin',
 'pipeline-fixture':P.parent/'kernel313/pipeline-fixture','bin/samurai-ccm':P/'samurai-ccm','bin/gst-hardware-probe':sdk/'private/camss316-runtime/gst-hardware-probe'}
with tarfile.open(P/'probe.tar.gz','w:gz') as tar:
 for name,path in files.items():
  data=path.read_bytes();item=tarfile.TarInfo(name);item.size=len(data);item.mode=0o700 if name.startswith('bin/') or name=='pipeline-fixture' else 0o600;tar.addfile(item,io.BytesIO(data))
for name in ['launch-probe.py','poll-probe.py','fetch-pattern.py']:
 text=(HERE.parent/'kernel318'/name).read_text().replace('k318-lsc-','k334-ccm-')
 if name=='poll-probe.py':text=text.replace("p.read_text(errors='replace')[-4000:]", "p.read_text(errors='replace')")
 (HERE/name).write_text(text)
text=(HERE.parent/'kernel332/final-state.py').read_text().replace('stage=332','stage=334');(HERE/'final-state.py').write_text(text)
(HERE/'runtime-build-validation.json').write_text(json.dumps(dict(stage=334,temporary_camss_module=True,installed_userspace_reused=True,module_bytes=len(raw),
 module_sha256=proof['module_sha256'],module_note_sha256=proof['module_note_sha256'],factory_payload_private=True,passed=True),indent=2)+'\n')
print('Prepared temporary-module CCM pattern and four installed-stack captures with restoration.')
