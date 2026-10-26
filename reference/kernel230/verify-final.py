"""Verify deployed evidence and the preserved source/artifact chain."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
ref=Path(__file__).resolve().parent;root=ref.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel230')
spec=importlib.util.spec_from_file_location('prepare227',ref.parent/'kernel227/prepare-fastrpc.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
assert p.snapshot()==json.loads((private.parent/'kernel228/canonical-after-private.json').read_text())
lock=json.loads((root/'linux-port/ssc/kernel/source-lock.json').read_text())
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
assert sha(root/'linux-port/ssc/kernel/fastrpc.c')==lock['source_sha256']==sha(p.KERNEL/'drivers/misc/fastrpc.c')
assert sha(root/'linux-port/ssc/kernel/0001-fastrpc-publication-lifetime.patch')==lock['patch_sha256']
assert sha(private.parent/'kernel228/fastrpc228-intree-private.ko')==lock['loaded_this_boot']['module_sha256']==lock['rootfs_default']['module_sha256']
assert lock['loaded_this_boot']['intree'] and lock['loaded_this_boot']['taint']==0 and lock['rootfs_default']['clean_boot_verified']
runtime=json.loads((ref/'runtime-validation.json').read_text());native=json.loads((ref/'native-sensors-validation.json').read_text());health=json.loads((ref/'final-health-validation.json').read_text());evidence=json.loads((ref/'evidence-validation.json').read_text());recovery=json.loads((ref/'preboot-recovery-validation.json').read_text())
assert runtime['new_boot_identity_verified'] and runtime['ssc_automatic_start_real_readiness'] and runtime['candidate_loaded_note_verified']
assert runtime['fastrpc_module_sha256']==lock['loaded_this_boot']['module_sha256'] and runtime['partitions_flashed']==[]
assert native['real_module_pin']==dict(device='fastrpc-adsp',before=1,while_open=2,after_close=1)
assert len(native['five_real_sensor_streams'])==5 and all(v['measurements']>0 and v['clean_disable'] for v in native['five_real_sensor_streams'].values())
assert native['ordinary_uid10000_claims']['uid']==10000 and len(native['ordinary_uid10000_claims']['claimed_and_released'])==3 and native['active_wayland_claim_child_verified'] and native['polkit_policy_unchanged']
for report,key in [(runtime,'faults'),(native,'fault_increments'),(health,'fault_counts')]:assert report['taint']==0 and not any(report[key].values())
assert health['boot219_logdump183_persist_nv_exact'] and health['package_database_unchanged'] and health['camera_e49_fae1_and_r13_r8_preserved'] and health['module_tree786_and_unrelated785_exact']
assert evidence['all_members_verified'] and recovery['failed_precondition_workers_retained']==2 and recovery['final_quiesce_exit_code']==0
scripts=list(ref.glob('*.py'))
for f in scripts:compile(f.read_text(),str(f),'exec')
shells=list(ref.glob('*.sh'))
for f in shells:subprocess.run(['bash','-n',str(f)],check=True)
checkpoint=root/'NEXT-SESSION.md';assert len(checkpoint.read_bytes())<=6500
for heading in ['## 源码、产物与回退依据','## 续作与已知风险']:assert heading in checkpoint.read_text()
report=dict(stage=230,current_guard='/var/lib/samurai/k230-runtime/boot-id-private.txt',clean_intree_loaded_and_native_sensors_verified=True,canonical_after228_preserved=True,public_source_patch_and_actual_module_locked=True,python_compile=len(scripts),shell_syntax=len(shells),precondition_failures_retained=True,private_native_members=evidence['private_native_archive_members'],checkpoint_bytes=len(checkpoint.read_bytes()),full_peripheral_goal_active=True)
(ref/'source-final-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
