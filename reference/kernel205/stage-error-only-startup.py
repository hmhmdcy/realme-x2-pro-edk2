from pathlib import Path
import hashlib,json,subprocess
import host

text=(host.PRIVATE/'bluetooth-startup-source-private.txt').read_text();needle='/bin/insmod "$path"';assert text.count(needle)==1
text=text.replace(needle,'''if [ "$module" = hci_uart ]; then
                /bin/insmod "$path" samurai_rx_diag=1
            else
                /bin/insmod "$path"
            fi''')
helper=host.PRIVATE/'samurai-bluetooth-error-only-private.sh';helper.write_text(text);subprocess.run(['sh','-n',str(helper)],check=True)
digest=hashlib.sha256(helper.read_bytes()).hexdigest();host.upload(helper,'/var/lib/samurai/k205-tools/samurai-bluetooth-error-only.sh')
native=r'''
from pathlib import Path
import hashlib,json,os,shutil
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k205-runtime/boot-id-private.txt').read_bytes()
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();capture=json.loads((root/'k205-boottrace'/boot/'summary.json').read_text());assert capture['finite_40_second_capture_completed'] and not Path('/sys/kernel/tracing/instances/k205-bt-boot').exists()
out=root/'k205-error-only-stage';assert not out.exists();out.mkdir(mode=0o700)
target=Path('/usr/sbin/samurai-bluetooth');assert hashlib.sha256(target.read_bytes()).hexdigest()=='30af7a16128f1c2659b34f3a28acd2ca40dc37e1fd66537e0fabb523baf3fd9f';shutil.copyfile(target,out/'helper-with-trace-original.sh')
raw=(root/'k205-tools/samurai-bluetooth-error-only.sh').read_bytes();assert hashlib.sha256(raw).hexdigest()==EXPECTED
temporary=target.with_name('samurai-bluetooth.k205-error-only');temporary.write_bytes(raw);temporary.chmod(0o755);os.replace(temporary,target)
r=dict(stage=205,error_only_boot_helper_sha256=EXPECTED,uart_trace_hook_removed_for_control=True,diagnostic_module_unchanged=True,no_runtime_restart_performed=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
p=host.ssh('python3 -',input=native.replace('EXPECTED',repr(digest)).encode());(host.PRIVATE/'error-only-stage-private.log').write_bytes(p.stdout+p.stderr);(Path(__file__).resolve().parent/'error-only-staging-validation.json').write_bytes(p.stdout);print(p.stdout.decode())
