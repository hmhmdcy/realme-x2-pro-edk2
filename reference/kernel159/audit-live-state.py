from pathlib import Path
import hashlib,json,os,sqlite3,subprocess,uuid
os.umask(0o077)
out=Path('/var/lib/samurai/k159-completion-audit');assert not out.exists();out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert os.uname().version.startswith('#158 ')
assert boot==Path('/var/lib/samurai/k159-first-startup/boot-id-private.txt').read_bytes()
kernel=subprocess.check_output(['dmesg'],text=True)
counts={k:kernel.count(v) for k,v in dict(kms_init_failures='kms hw init failed',dpu_timeouts='frame done timeout',
    dsi_errors='dsi_err_worker',gpu_faults='gpu fault:',warnings='WARNING:',ufs_uic_timeouts='completion timeout').items()}
assert not any(counts.values()),counts
build=json.loads(Path('/var/lib/samurai/k159-tools/build-package-validation.json').read_text())
actual=subprocess.check_output(['sha256sum','/dev/sde32'],text=True).split()[0]
assert actual==build['logdump_sha256']
c=sqlite3.connect('file:/var/log/logbookd.db?mode=ro',uri=True)
old=uuid.UUID(Path('/var/lib/samurai/k157-first-startup/boot-id-private.txt').read_text().strip()).bytes
logs=dict(all_rows=c.execute('select count(*) from log').fetchone()[0],
    rows_for_original157_boot=c.execute('select count(*) from log where boot_id=?',(old,)).fetchone()[0],
    latest_received=c.execute('select max(received) from log').fetchone()[0]);c.close()
report=dict(actual_kernel_build=158,same159_boot=True,uptime=float(Path('/proc/uptime').read_text().split()[0]),
    counts=counts,logdump_matches_compiled158=True,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
    desktop_present={n:bool(subprocess.run(['pgrep','-u','10000','-x',n],capture_output=True).stdout) for n in ['phoc','phosh']},
    persistent_log_database=logs,pstore_backend_enabled=True,pstore_mounted=True,pstore_records_present=bool(list(Path('/sys/fs/pstore').iterdir())),
    previous157_reset_cause_unproven=True,physical_startup_transition_feedback_pending=True)
assert report['taint']==0 and all(report['desktop_present'].values())
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
