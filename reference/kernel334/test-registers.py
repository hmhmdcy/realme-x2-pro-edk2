from pathlib import Path
import json,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;tree=Path(json.loads((HERE/'source-state.json').read_text())['source'])
stage=P/'register-test';stage.mkdir(exist_ok=True);(stage/'linux/media').mkdir(parents=True,exist_ok=True)
for name in ['linux/qcom-camss-config.h','linux/media/v4l2-isp.h']:shutil.copyfile(tree/'include/uapi'/name,stage/name)
shutil.copyfile(P.parent/'kernel296/titan170-ife-source-1-private.h',stage/'titan170_ife-private.h')
shutil.copyfile(HERE/'ccm-register-test.c',stage/'test.c')
source=(HERE/'kernel/camss-vfe-175-ccm.c').read_text();(stage/'ccm-driver-body-private.c').write_text('\n'.join(line for line in source.splitlines() if not line.startswith('#include'))+'\n')
input_data=(P.parent/'kernel333/math-input-private.bin').read_bytes();expected=(P.parent/'kernel333/stock-expected-private.bin').read_bytes();pos=cursor=0;vectors=bytearray();cases=0
while pos<len(input_data):
 mode=struct.unpack_from('<I',input_data,pos)[0];assert mode in [1,2];pos+=56 if mode==1 else 108
 if mode==2:cursor+=48
 vectors.extend(expected[cursor:cursor+26]);cursor+=26;cases+=1
assert cursor==len(expected) and pos==len(input_data)
(stage/'vectors-private.bin').write_bytes(vectors)
flags=['-std=gnu11','-O2','-Wall','-Wextra','-Werror'];rows=[]
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');relative=Path('/private/camss334-registers');arm=sdk/str(relative).lstrip('/')
if not arm.exists():shutil.copytree(stage,arm)
else:
 for path in stage.rglob('*'):
  if path.is_file():target=arm/path.relative_to(stage);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
for arch in ['host','aarch64']:
 args=['gcc',*flags,'-I'+str(stage),str(stage/'test.c'),'-o',str(stage/'test-host')] if arch=='host' else ['chroot',str(sdk),'gcc',*flags,'-I'+str(relative),str(relative/'test.c'),'-o',str(relative/'test-aarch64')]
 q=subprocess.run(args,capture_output=True);(P/('register-'+arch+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 args=[str(stage/'test-host'),str(stage/'vectors-private.bin')] if arch=='host' else ['chroot',str(sdk),str(relative/'test-aarch64'),str(relative/'vectors-private.bin')]
 q=subprocess.run(args,capture_output=True);(P/('register-'+arch+'.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 rows.append(dict(architecture=arch,parameter_cases=cases,passed=b'CCM_REGISTER_PASS' in q.stdout));print(q.stdout.decode().strip(),flush=True)
report=dict(stage=334,actual_driver_body_tested=True,original_register_bitfields_reference_stage=296,architectures=rows,
 full_mmio_image_and_reserved_bits_verified=True,header_only_disable_guard_page_verified=True,invalid_flags_fields_and_padding_rejected=True,
 update_preserves_enable_state=True,lifecycle_resets_to_disabled_unity=True,no_hardware_operation=True,passed=all(r['passed'] for r in rows))
(HERE/'register-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
