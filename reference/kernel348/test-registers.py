from pathlib import Path
import importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage);storage.mounted_build()
tree=Path(json.loads((HERE/'source-state.json').read_text())['source']);stage=P/'register-test';stage.mkdir(exist_ok=True)
(stage/'linux/media').mkdir(parents=True,exist_ok=True)
for name in ['linux/qcom-camss-config.h','linux/media/v4l2-isp.h']:shutil.copyfile(tree/'include/uapi'/name,stage/name)
shutil.copyfile(HERE/'gamma-register-test.c',stage/'test.c')
for name in ['gamma','lsc']:
 raw=(tree/('drivers/media/platform/qcom/camss/camss-vfe-175-'+name+'.c')).read_text()
 (stage/(name+'-driver-body-private.c')).write_text('\n'.join(l for l in raw.splitlines() if not l.startswith('#include'))+'\n')
for name in ['gamma','lsc']:
 shutil.copyfile(tree/('drivers/media/platform/qcom/camss/camss-vfe-175-'+name+'.h'),stage/('camss-vfe-175-'+name+'.h'))
# Reuse the validated private factory output; no literal factory knots in sources.
expected=(P.parent/'kernel347/expected-private.bin').read_bytes()
assert expected[:4]==b'\1\0\0\0';(stage/'factory-lut-private.bin').write_bytes(expected[4:260])
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');arm=sdk/'private/camss348-registers'
shutil.copytree(stage,arm,dirs_exist_ok=True)
rows=[];flags=['-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fno-strict-aliasing']
for arch in ['host','aarch64']:
 command=['gcc',*flags,'-I'+str(stage),str(stage/'test.c'),'-o',str(stage/'test-host')] if arch=='host' else ['chroot',str(sdk),'gcc',*flags,'-I/private/camss348-registers','/private/camss348-registers/test.c','-o','/private/camss348-registers/test-aarch64']
 q=subprocess.run(command,capture_output=True);(P/(arch+'-register-build.log')).write_bytes(q.stdout+q.stderr)
 if q.returncode:print(q.stderr.decode());raise SystemExit(q.returncode)
 command=[str(stage/'test-host'),str(stage/'factory-lut-private.bin')] if arch=='host' else ['chroot',str(sdk),'/private/camss348-registers/test-aarch64','/private/camss348-registers/factory-lut-private.bin']
 q=subprocess.run(command,capture_output=True,timeout=25);(P/(arch+'-register-test.log')).write_bytes(q.stdout+q.stderr)
 if q.returncode:print(q.stderr.decode());raise SystemExit(q.returncode)
 rows.append(dict(architecture=arch,passed=b'GAMMA_REGISTER_PASS' in q.stdout));print(q.stdout.decode(),flush=True)
report=dict(stage=348,architectures=rows,actual_gamma_and_lsc_driver_bodies=True,shared_dmi_both_orders_verified=True,
 all_eight_bank_combinations_verified=True,inactive_bank_only_uploads=True,header_only_disable_guard_page_verified=True,
 enable_update_bypass_and_restart_verified=True,all_field_positions_validated=True,old_format_initialization_retained=True,
 actual_sof_and_pixels_not_yet_tested=True,phone_changed=False,passed=all(r['passed'] for r in rows))
(HERE/'register-validation.json').write_text(json.dumps(report,indent=2)+'\n')
