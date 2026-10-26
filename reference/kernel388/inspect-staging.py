from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
code="""from pathlib import Path
import json
root=Path('/var/lib/samurai/k388-pipeline-r1')
processes=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  cmd=(p/'cmdline').read_bytes()
  if str(root).encode() in cmd and b'python3 -c' not in cmd:processes.append(dict(pid=int(p.name),cmd=cmd.replace(b'\\0',b' ').decode(errors='replace'),state=(p/'stat').read_text().rsplit(')',1)[1].split()[0]))
 except OSError:pass
print(json.dumps(dict(root_exists=root.exists(),files={p.name:p.stat().st_size for p in root.iterdir() if p.is_file()} if root.exists() else {},processes=processes,
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),candidate_modules_present=[n for n in ['qcom_camss_icp_a5_core','camss_icp_a5_boot_test','camss_icp_a5_m2m','v4l2_mem2mem'] if Path('/sys/module',n).exists()],
 firmware_present=Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists(),
 camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']})))
"""
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);(host.PRIVATE/'staging-r1-observation-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout);print(json.dumps(d,indent=2))
assert not d['candidate_modules_present'] and not d['firmware_present'] and d['taint']==0
assert 'state.json' not in d['files'] and not any(p['state']!='Z' for p in d['processes'])
report=dict(stage=388,pipeline_staging_run='r1',upload_interrupted=True,worker_never_launched=True,manifest_absent='manifest.json' not in d['files'],partial_files_retained=True,phone_camera_resources_idle=all(v=='suspended' for v in d['camera_pm'].values()),no_live_transaction_process=True,taint=0,passed=True)
(HERE/'staging-r1-validation.json').write_text(json.dumps(report,indent=2)+'\n')
