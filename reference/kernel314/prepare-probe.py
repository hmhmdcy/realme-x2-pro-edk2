"""Reuse the temporary-module workflow; only the capture payload changes."""
from pathlib import Path
import hashlib,io,json,tarfile
import host
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel307/native-probe.py').read_text()
s=s.replace("b'CCI error']", "b'CCI error',b'Stream stop failed:',b'Failed to disable stream on remote pad:',b'Missing SOF tag',b'Received wm done for unmapped index',b'Unhandled context fault']")
s=s.replace("tele=len(sys.argv)>2 and sys.argv[2]=='tele'","models=sys.argv[2].split(',') if len(sys.argv)>2 else ['imx319']")
begin=s.index("    run([str(root/'pipeline-fixture')")
end=s.index('\nexcept BaseException:',begin)
s=s[:begin]+'''    for index,model in enumerate(models):
        run([str(root/'pipeline-fixture'),'/dev/media0','/usr/bin/python3',str(root/'configure-dual.py'),
             model,'pix-first' if index%2 else 'raw-first'], 'capture-'+model,timeout=32)
'''+s[end:]
begin=s.index("    text=(root/'capture.log')")
s=s[:begin]+'''    captures={model:(root/('capture-'+model+'.log')).read_text(errors='replace') if (root/('capture-'+model+'.log')).exists() else '' for model in models}
    for _ in range(30):
        if all(Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip()=='suspended' for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']):break
        time.sleep(.2)
    health={'platforms':{n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
     'rails':{(p/'name').read_text().strip():{'state':(p/'state').read_text().strip(),'users':int((p/'num_users').read_text())} for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))}}
    report=dict(stage=314,failure=failure is not None,deployment_restored=restored,
     captures={m:{'frames':t.count('DUAL_FRAME '),'probe_passed':'DUAL_RESULT success=1' in t,'fixture_restored':'FIXTURE_RESTORATION result=0' in t} for m,t in captures.items()},
     fault_delta=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),health=health,
     temporary_module_only=True,installed_files_unchanged=True)
    report['passed']=not report['failure'] and restored and all(c['probe_passed'] and c['fixture_restored'] for c in report['captures'].values()) and not any(faults.values()) and not report['taint'] and all(v=='suspended' for v in health['platforms'].values()) and all(v=={'state':'disabled','users':0} for v in health['rails'].values())
    save('complete' if report['passed'] else 'failed',terminal=True,summary=report)
    print(json.dumps(report))
'''
(HERE/'native-probe.py').write_text(s)
build=json.loads((HERE/'kernel-build-validation.json').read_text());assert build['exit_code']==0
files={'qcom-camss.ko':Path(build['module']),'pipeline-fixture':HERE.parent/'kernel313/pipeline-fixture.c'}
files['pipeline-fixture']=host.PRIVATE.parent/'kernel313/pipeline-fixture'
files.update({'dual-probe':host.PRIVATE/'dual-probe','configure-dual.py':HERE/'configure-dual.py','worker.py':HERE/'native-probe.py'})
with tarfile.open(host.PRIVATE/'probe.tar.gz','w:gz') as tar:
 for name,path in files.items():
  raw=path.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o700 if name in ['dual-probe','pipeline-fixture'] else 0o600
  tar.addfile(item,io.BytesIO(raw))
print('Prepared314 temporary streams module and dual capture probe.')
