from pathlib import Path
import importlib.util,json,subprocess
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel213')
spec=importlib.util.spec_from_file_location('post_transfer_status',here.parent/'kernel200/host-before-newboot.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
native=b"from pathlib import Path\nimport json,subprocess\nassert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k213-baseline/boot-id-private.txt').read_bytes()\nrp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('*')}\npm={n:Path(p,'power/runtime_status').read_text().strip() for n,p in [('sensor','/sys/bus/i2c/devices/7-0010'),('camss','/sys/bus/platform/devices/acb3000.camss'),('cci','/sys/bus/platform/devices/ac4b000.cci')]}\nlog=subprocess.check_output(['dmesg']);print(json.dumps(dict(current213_guard_verified=True,taint=int(Path('/proc/sys/kernel/tainted').read_text()),remoteprocs=rp,camera_pm=pm,faults_zero=all(log.count(t)==0 for t in [b'WARNING:',b'Oops:',b'gpu fault:',b'fatal error received',b'Frame reassembly failed']),native_archive_present=Path('/tmp/k213-final-evidence-private.tar.gz').is_file())))\n"
try:
    p=transport.ssh('python3 -',input=native,timeout=20);report=json.loads(p.stdout);report['responsive']=True
except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as error:
    (private/'health-after-transfer-failure-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''));report=dict(responsive=False,full_health_not_revalidated_after_transfer_failure=True,last_verified_health='final-health-validation.json')
(here/'health-after-transfer-failure-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
