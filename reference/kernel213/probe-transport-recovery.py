from pathlib import Path
import importlib.util,json,subprocess
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel213')
spec=importlib.util.spec_from_file_location('wifi_recovery',here.parent/'kernel200/host-before-newboot.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
native=b"from pathlib import Path\nimport json\nassert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k213-baseline/boot-id-private.txt').read_bytes()\nprint(json.dumps(dict(current213_guard_verified=True,taint=int(Path('/proc/sys/kernel/tainted').read_text()),archive_still_present=Path('/tmp/k213-final-evidence-private.tar.gz').is_file())))\n"
try:
    p=transport.ssh('python3 -',input=native,timeout=20);report=json.loads(p.stdout);report['strict_original_key_wifi_responsive']=True
except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as error:
    (private/'wifi-recovery-probe-failed-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''));report=dict(strict_original_key_wifi_responsive=False)
(here/'transport-recovery-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
