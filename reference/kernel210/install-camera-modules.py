from pathlib import Path
import hashlib,json,os,shutil,subprocess
os.umask(0o077)
root=Path('/var/lib/samurai');stage=root/'k210-module-stage';out=root/'k210-module-install';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k210-baseline/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert not any(Path('/sys/module/'+n).exists() for n in ['imx471','v4l2_cci','qcom_pm8008','qcom_pm8008_regulator'])
modules=Path('/usr/lib/modules')/os.uname().release
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=json.loads((root/'k210-install-before-r2/module-inventory-private.json').read_text())
assert before=={str(p.relative_to(modules)):sha(p) for p in modules.rglob('*') if p.is_file()}
build=json.loads((stage/'camera-module-build-validation.json').read_text())
assert build['persistent_camera_config_enabled'] and build['w1_diagnostics']==0
intended={str(Path('kernel')/m['path']):m['sha256'] for m in build['modules']}
for name,digest in intended.items():assert sha(stage/Path(name).name)==digest
assert len(intended)==3
before_log=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before_log)
for name,digest in intended.items():
    target=modules/name;target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_name(target.name+'.k210-new');assert not temp.exists()
    shutil.copyfile(stage/Path(name).name,temp);temp.chmod(0o644)
    assert sha(temp)==digest;os.replace(temp,target)
order=modules/'modules.order';lines=order.read_text().splitlines()
assert len(lines)==770
for name in intended:
    if name not in lines:lines.append(name)
assert len(lines)==772;order.write_text('\n'.join(lines)+'\n')
for i,args in enumerate([['depmod','-a'],['modprobe','--show-depends','imx471']]):
    p=subprocess.run(args,capture_output=True,timeout=60);(out/('metadata-'+str(i)+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
    if i==1:
        assert b'v4l2-cci.ko' in p.stdout and b'imx471.ko' in p.stdout
after={str(p.relative_to(modules)):sha(p) for p in modules.rglob('*') if p.is_file()}
assert sum(n.endswith('.ko') for n in after)==772
assert {n for n in before.keys()|after.keys() if n.endswith('.ko') and before.get(n)!=after.get(n)}==set(intended)
assert set(after)-set(before)==set(intended)-set(before)
assert set(before)<=set(after)
assert all(before[n]==after[n] for n in before if n.endswith('.ko') and n not in intended)
# Current DT has no external sensor/PMIC nodes, so this checks native linking
# without bringing camera hardware up. Unload again before the transition.
for i,args in enumerate([['modprobe','imx471'],['modprobe','qcom-pm8008'],['rmmod','imx471'],['rmmod','v4l2_cci'],['rmmod','qcom_pm8008']]):
    p=subprocess.run(args,capture_output=True,timeout=20);(out/('link-check-'+str(i)+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
assert not any(Path('/sys/module/'+n).exists() for n in ['imx471','v4l2_cci','qcom_pm8008'])
after_log=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after_log)
assert after_log.startswith(before_log)
added=after_log[len(before_log):]
assert not any(x in added for x in [b'WARNING:',b'Oops:',b'Unknown symbol',b'disagrees about version'])
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
(out/'module-inventory-after-private.json').write_text(json.dumps(after,indent=2)+'\n')
(out/'module-tree.sha256').write_text(''.join(digest+'  '+name+'\n' for name,digest in sorted(after.items())))
report=dict(stage=210,installed=True,installed_modules=772,installed_regular_files=len(after),only_three_intended_module_paths_changed=True,all_769_unrelated_modules_preserved=True,custom_camss_bt_preserved=True,metadata_regenerated=True,native_modprobe_and_unload_passed=True,no_external_camera_dt_nodes_in_this_boot=True,hardware_probe_not_yet_tested=True,taint=0,no_new_kernel_faults=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
