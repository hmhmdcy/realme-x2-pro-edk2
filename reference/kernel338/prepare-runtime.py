from pathlib import Path
import hashlib,io,json,struct,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'probe-build-validation.json').read_text())['passed']
build=json.loads((HERE/'kernel-build-validation.json').read_text());assert build['exit_code']==0 and not build['diagnostics'] and build['intree']=='Y'
module=Path(build['module']);raw=module.read_bytes();shoff=struct.unpack_from('<Q',raw,40)[0];stride,count,strings=struct.unpack_from('<HHH',raw,58)
sections=[struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*stride) for i in range(count)];names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
note=next(s for s in sections if names[s[0]:].split(b'\0')[0]==b'.note.gnu.build-id')
proof=dict(module_sha256=hashlib.sha256(raw).hexdigest(),module_note_sha256=hashlib.sha256(raw[note[4]:note[4]+note[5]]).hexdigest());(P/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
s=(HERE.parent/'kernel334/native-probe.py').read_text().replace('stage=334','stage=338')
s=s.replace("if selection=='pattern':\n            app=[str(root/'bin/samurai-ccm'),'--pattern',str(root/'pattern-private'),str(root/'factory-ccm-private.bin')]", "if selection.startswith('stats:'):\n            model=selection.split(':',1)[1]\n            app=[str(root/'bin/stats-grid-probe'),'--capture',model,str(root/('sample-'+model))]")
s=s.replace("('capture-'+selection+'.log')","('capture-'+selection.replace(':','-')+'.log')")
s=s.replace("        if selection.startswith('stats:'):",'''        if selection.startswith('awb:'):
            model=selection.split(':',1)[1]
            devices=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith(model+' ')]
            if len(devices)!=1:raise RuntimeError('Sensor node not unique')
            sizes={'s5kgw1':'4608x3456','imx471':'2304x1728','imx319':'1632x1224','s5k3m5':'2104x1560'}
            app=[str(root/'pipeline-fixture'),'/dev/media0',str(root/'bin/awb-grid-smoke'),model,'/dev/'+devices[0].name,str(root/('sample-'+model)),'320x240',sizes[model],'2' if model=='s5kgw1' else '3']
        elif selection.startswith('stats:'):''')
s=s.replace("if selection=='pattern' else 'bus-errors=0 result=0'","if selection.startswith('stats:') else 'bus-errors=0 result=0'")
s=s.replace("if ret or expected not in text:","if selection.startswith('awb:'):expected=' failed=0 result=0'\n        if ret or expected not in text:")
s=s.replace("t.count('CCM_FRAME ')","t.count('GRID_FRAME ')")
s=s.replace("t.count('GRID_FRAME ')+t.count('GST_IMAGE ')","t.count('GRID_FRAME ')+t.count('AWB_FRAME ')+t.count('GST_IMAGE ')")
s=s.replace("if m=='pattern' else", "if m.startswith('stats:') else")
s=s.replace("else ('bus-errors=0 result=0' in t)","else ((' failed=0 result=0' in t) if m.startswith('awb:') else ('bus-errors=0 result=0' in t))")
(HERE/'native-probe.py').write_text(s)
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
files={'qcom-camss.ko':module,'worker.py':HERE/'native-probe.py','proof.json':P/'proof.json','pipeline-fixture':P.parent/'kernel313/pipeline-fixture',
 'bin/stats-grid-probe':P/'stats-grid-probe','bin/gst-hardware-probe':sdk/'private/camss316-runtime/gst-hardware-probe'}
awb=sdk/'private/camss338-runtime/awb-grid-smoke'
if awb.is_file():files['bin/awb-grid-smoke']=awb
with tarfile.open(P/'probe.tar.gz','w:gz') as tar:
 for name,path in files.items():
  data=path.read_bytes();item=tarfile.TarInfo(name);item.size=len(data);item.mode=0o700 if name.startswith('bin/') or name=='pipeline-fixture' else 0o600;tar.addfile(item,io.BytesIO(data))
for name in ['launch-probe.py','poll-probe.py','final-state.py']:
 text=(HERE.parent/'kernel334'/name).read_text().replace('k334-ccm-','k338-grid-').replace('stage=334','stage=338');(HERE/name).write_text(text)
(HERE/'runtime-build-validation.json').write_text(json.dumps(dict(stage=338,temporary_camss_module=True,installed_userspace_reused=True,module_bytes=len(raw),**proof,
 four_sensor_stats_dump=True,existing_gstreamer_probe_reused=True,passed=True),indent=2)+'\n')
print('Prepared temporary32x16 module with direct statistics and installed-stack probes.')
