"""Reuse the tested348 swap/restore worker with fresh boot and r28 request probe."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel349/native-probe.py').read_text()
s=s.replace('Temporary Gamma IPA+348 module validation with338 restoration.','Temporary r28 EV/flicker/Gamma validation with338 restoration.')
s=s.replace("Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes()","Path(proof['boot_guard']).read_bytes()")
s=s.replace("if Path('/proc/sys/kernel/tainted').read_text().strip()!='0':", "if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=proof['expected_boot']:raise RuntimeError('Unexpected recovered boot')\n if Path('/proc/sys/kernel/tainted').read_text().strip()!='0':")
s=s.replace("LIBCAMERA_IPA_MODULE_PATH=str(root/'ipa'),LD_LIBRARY_PATH=str(root/'lib'))", "LIBCAMERA_IPA_MODULE_PATH=str(root/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(root/'proxy'),LD_LIBRARY_PATH=str(root/'lib'))")
a=s.index(" app=[str(root/'pipeline-fixture')");b=s.index(" with (root/('capture-",a)
s=s[:a]+''' if item['isolation']:env['LIBCAMERA_IPA_FORCE_ISOLATION']='1'
 app=[str(root/'pipeline-fixture'),'/dev/media0',str(root/'bin/adaptation-smoke'),model,'/dev/'+devices[0].name,item['sensor_size'],str(item['test_pattern'])]
'''+s[b:]
a=s.index(' # A configured override must fail clearly');b=s.index(" wait_idle();save('unloading-deployed')",a)
s=s[:a]+" negative=proof['old_kernel_reference']\n if not all(negative.values()):raise RuntimeError('Retained349 old-kernel evidence incomplete')\n"+s[b:]
a=s.index("  captures[selection]=dict(");b=s.index('\nexcept BaseException:',a)
s=s[:a]+'''  import re
  appPids=[int(p) for p in re.findall(r'ADAPT_PID value=(\\d+)',text)]
  statsPids={int(p) for p in re.findall(r'IPA stats pid=(\\d+)',text)}
  libraries=set(re.findall(r'ADAPT_LIBRARY path=(\\S+)',text))
  librariesOk=all(str(root/'lib'/name) in libraries for name in ['libcamera.so.0.7.2','libcamera-base.so.0.7.2'])
  transportOk=len(appPids)==1 and bool(statsPids) and all((pid!=appPids[0])==cases[selection]['isolation'] for pid in statsPids)
  captures[selection]=dict(frames=text.count('ADAPT_FRAME '),completed_phases=text.count('ADAPT_PHASE '),
   probe_passed=ret==0 and ' failed=0 result=0' in text,gamma_ack_count=text.count('GAMMA_APPLIED '),
   isolation_requested=cases[selection]['isolation'],actual_transport_verified=transportOk,
   candidate_libraries_verified=librariesOk,
   actual_auto_updates=text.count('AE update epoch='),cleanup_restored=True)
  item=captures[selection]
  if not item['probe_passed'] or item['gamma_ack_count']!=1 or item['completed_phases']!=5 or not transportOk or not librariesOk or not item['actual_auto_updates']:raise RuntimeError(selection+' request integration failed')
'''+s[b:]
s=s.replace('stage=349','stage=361').replace("report['old_kernel_rejection_reused']=(root/'old-kernel-reference.json').exists()","report['old_kernel_rejection_reused']=True")
(HERE/'native-probe.py').write_text(s)
print('Prepared fresh request probe worker; reused349 resource restoration, no ICP bootstrap.')
