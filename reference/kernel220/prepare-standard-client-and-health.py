from pathlib import Path
import ast,hashlib,json,shutil
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel220');prior=here.parent/'kernel219'
proof=json.loads((prior/'gst-client-build-validation.json').read_text());data=(private.parent/'kernel219/probes/gst-camera219-probe').read_bytes();assert hashlib.sha256(data).hexdigest()==proof['sha256']
(private/'probes').mkdir(mode=0o700);(private/'probes/gst-camera220-probe').write_bytes(data)
proof.update(stage=220,retained_stage219_standard_gstreamer_binary=True,new_camera_framework_test_pending=True)
(here/'gst-client-build-validation.json').write_text(json.dumps(proof,indent=2)+'\n')
text=(prior/'run-standard-r6-client.py').read_text().replace('new_r6_camera_libraries_loaded','new_r7_camera_libraries_loaded')
text=text.replace('gst-camera219-probe','gst-camera220-probe').replace('samurai-camera219-probes','samurai-camera220-probes').replace('installed-r6-standard-','installed-r7-standard-').replace('camera219-r6-client-registry','camera220-r7-client-registry')
text=text.replace("code=(here/'native-mode-runner.py').read_text()","code=(here.parent/'kernel219/native-mode-runner.py').read_text()")
text=text.replace('/run/samurai-camera220-probes/native-mode-probe','/run/samurai-camera219-probes/native-mode-probe')
text=text.replace(";assert not p.exists();d=gzip", ";p.parent.mkdir(mode=0o755,exist_ok=True);assert not p.exists();d=gzip")
text=text.replace("code=code.replace('report=dict(stage=219,','report=dict(stage=219,", "code=code.replace('report=dict(stage=219,','report=dict(stage=220,")
text=text.replace("compile(code,'native-standard-r6-client','exec')","code=code.replace('k219-runtime/boot-id-private.txt','k220-baseline/boot-id-private.txt').replace(\"'k219-capture-'\",\"'k220-capture-'\")\ncompile(code,'native-standard-r7-client','exec')")
compile(text,'standard-client220','exec');(here/'run-standard-r7-client.py').write_text(text)
old=ast.parse((prior/'final-health.py').read_text());code=next(ast.literal_eval(n.value) for n in old.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets))
code=code.replace("out=root/'k219-final-health-r2'","out=root/'k220-final-health'").replace("base=root/'k219-runtime'","base=root/'k220-baseline'")
code=code.replace('k219-r6-package-transaction','k220-r7-package-transaction').replace('k219-r6-package-candidates','k220-r7-package-candidates').replace('stage=219','stage=220')
compile(code,'native-health220','exec')
header="from pathlib import Path\nimport host,json\nhere=Path(__file__).resolve().parent\n"
header+="for w,h in [(1920,1088),(2296,1728),(4608,3456)]:\n r=json.loads((here/f'exposure-metadata-system-r7-{w}x{h}-validation.json').read_text());assert r['program_exit']==0 and r['frame_count']==36 and r['maximum_metadata_conversion_error_us']<1\n"
header+="r=json.loads((here/'standard-gstreamer-validation.json').read_text());assert r['program_exit']==0 and r['frame_count']==6\n"
header+='code='+repr(code)+'\n'
header+="p=host.ssh('python3 -',input=code.encode(),timeout=100)\n(host.PRIVATE/'final-health-host-private.log').write_bytes(p.stdout+p.stderr)\nr=json.loads(p.stdout);(here/'final-health-validation.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r))\n"
compile(header,'health220','exec');(here/'final-health.py').write_text(header)
print('Retained standard GStreamer client and current r7/219-boot health collector prepared')
