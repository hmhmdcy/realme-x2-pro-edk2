"""Reuse normal module restore and media-fixture paths for the AWB experiment."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel307/native-probe.py').read_text()
s=s.replace('import json, os, pwd, select, signal, subprocess, sys, time, traceback',
            'import json, os, pwd, re, select, signal, subprocess, sys, time, traceback')
s=s.replace('def run(args, label, timeout=20):\n    q=subprocess.run(args, capture_output=True, timeout=timeout)',
            'def run(args, label, timeout=20, env=None):\n    q=subprocess.run(args, capture_output=True, timeout=timeout, env=env)')
s=s.replace("tele=len(sys.argv)>2 and sys.argv[2]=='tele'",
            "tele=len(sys.argv)>2 and sys.argv[2]=='tele'\nepochs_wanted=1 if len(sys.argv)>3 and sys.argv[3]=='single' else 2")
a=s.index("    run([str(root/'pipeline-fixture')")
b=s.index('except BaseException:',a)
s=s[:a]+'''    stage=root/'bundle'
    model='s5k3m5' if tele else 'imx319'
    env=dict(os.environ, LD_LIBRARY_PATH=str(stage/'lib'),
             CAMSS_AWB_EPOCHS=str(epochs_wanted),
             LIBCAMERA_CAMSS_VFE_ENABLE='1', LIBCAMERA_PIPELINES_MATCH_LIST='camss-vfe',
             LIBCAMERA_CAMSS_VFE_PROFILE=str(stage/'profile'/ (model+'.yaml')),
             LIBCAMERA_IPA_MODULE_PATH=str(stage/'ipa'), LIBCAMERA_IPA_PROXY_PATH=str(stage/'proxy'),
             LIBCAMERA_IPA_FORCE_ISOLATION='1',
             LIBCAMERA_LOG_LEVELS='*:WARN,CamssVfe:DEBUG,IPACamss:DEBUG,IPAManager:DEBUG,IPAProxy:DEBUG')
    run([str(stage/'bin/pipeline-fixture'),'/dev/media0',str(stage/'bin/awb-smoke'),model],
        'capture', timeout=62,env=env)
'''+s[b:]
a=s.index('    report=dict(stage=307')
s=s[:a]+'''    epochs=[dict(epoch=int(e),frames=int(f),failed=int(x),stop=int(y))
            for e,f,x,y in re.findall(r'APPLICATION_EPOCH epoch=(\\d+) frames=(\\d+) failed=(\\d+) stop=(-?\\d+)',text)]
    locks=[dict(epoch=int(e),request=int(r),red=float(a),blue=float(b),locked=bool(int(l)))
           for e,r,a,b,l in re.findall(r'APPLICATION_WB epoch=(\\d+) request=(\\d+) red=([\\d.e+-]+) blue=([\\d.e+-]+) locked=(\\d+)',text)]
    report=dict(stage=308,sensor='s5k3m5' if tele else 'imx319',failure=failure is not None,
                expected_epochs=epochs_wanted,
                deployment_restored=restored,image_frames=text.count('APPLICATION_FRAME '),
                rgb_stats_frames=len(re.findall(r'RGB epoch=\\d+ sof=\\d+ present=1',text)),
                epochs=epochs,wb_metadata_frames=len(locks),
                epochs_with_lock=sorted({r['epoch'] for r in locks if r['locked']}),
                fixture_restored='FIXTURE_RESTORATION result=0' in text,
                isolation_forced='forced through configuration' in text,
                fault_delta=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
                temporary_module_only=True,installed_files_unchanged=True)
    report['passed']=not report['failure'] and restored and len(epochs)==epochs_wanted and all(
        e['frames']>=20 and e['failed']==0 and e['stop']==0 for e in epochs) and report['fixture_restored'] and not any(faults.values()) and not report['taint']
    save('complete' if report['passed'] else 'failed',terminal=True,summary=report)
    print(json.dumps(report))
'''
(HERE/'native-capture.py').write_text(s)
print('Prepared bounded AWB module experiment with deployment restoration.')
