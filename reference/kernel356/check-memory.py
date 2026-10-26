from pathlib import Path
import importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
stage=storage.mounted_build().parent/'icp356-tests';stage.mkdir(exist_ok=True)
def strip(text):return '\n'.join(l for l in text.splitlines() if not l.startswith('#include'))+'\n'
(stage/'actual-header-private.h').write_text(strip((HERE/'kernel/camss-icp-a5.h').read_text()))
(stage/'actual-memory-private.c').write_text(strip((HERE/'kernel/camss-icp-a5-memory.c').read_text()))
shutil.copyfile(HERE/'memory-test.c',stage/'memory-test.c');rows=[];arm=SDK/'private/camss356-memory'
for arch in ['host','aarch64']:
 mounted=False
 try:
  if arch=='aarch64':
   arm.mkdir(exist_ok=True);assert not list(arm.iterdir());subprocess.run(['mount','--bind',str(stage),str(arm)],check=True,capture_output=True);mounted=True
  flags=['-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-parameter']
  command=['gcc',*flags,str(stage/'memory-test.c'),'-o',str(stage/'memory-host')] if arch=='host' else ['chroot',str(SDK),'gcc',*flags,'/private/camss356-memory/memory-test.c','-o','/private/camss356-memory/memory-aarch64']
  q=subprocess.run(command,capture_output=True);(P/(arch+'-memory-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
  command=[str(stage/'memory-host')] if arch=='host' else ['chroot',str(SDK),'/private/camss356-memory/memory-aarch64']
  q=subprocess.run(command,capture_output=True,timeout=30);(P/(arch+'-memory-test.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stdout.decode()+q.stderr.decode();assert b'MEMORY_PASS' in q.stdout
  rows.append(dict(architecture=arch,output=q.stdout.decode().strip(),passed=True));print(q.stdout.decode(),flush=True)
 finally:
  if mounted:subprocess.run(['umount',str(arm)],check=True,capture_output=True)
report=dict(stage=356,actual_memory_backend_compiled=True,carveout_map_unmap_and_error_preserves_backing_tested=True,firmware_privileged_and_shared_heap_unprivileged_verified=True,nonzero_shared_heap_and_32bit_end_aliases_tested=True,architectures=rows,scattered_physical_pages_above_4GiB_verified=True,
 missing_or_wrong_reservation_and_bad_dma_domain_rejected=True,mapping_failures_roll_back_and_preserve_backing=True,
 failed_unmap_refuses_free_until_successful_retry=True,foreign_mapping_never_overwritten_or_unmapped=True,
 domain_switch_rejected_without_touching_mapping_or_backing=True,api_stubs_not_real_iommu=True,sdk_bind_released=True,phone_changed=False,passed=True)
(HERE/'memory-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
