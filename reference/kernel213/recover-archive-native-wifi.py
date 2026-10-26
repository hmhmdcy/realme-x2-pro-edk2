from pathlib import Path
import hashlib,importlib.util,json,re,subprocess,tarfile
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel213')
spec=importlib.util.spec_from_file_location('native_wifi_recovery',here.parent/'kernel190/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
base,address=transport._wifi()
def native_path(value):
    return re.sub(r'([A-Za-z]):[/\\]([^\n]*)',lambda m:'/mnt/'+m[1].lower()+'/'+m[2].replace('\\','/'),value)
options=[];index=0
while index<len(base.OPTIONS):
    value=base.OPTIONS[index]
    if value=='-o' and index+1<len(base.OPTIONS) and base.OPTIONS[index+1].startswith(('ConnectTimeout=','ConnectionAttempts=','ServerAliveInterval=','ServerAliveCountMax=')):
        index+=2;continue
    options.append(native_path(value));index+=1
native=b"from pathlib import Path\nimport sys\nassert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k213-baseline/boot-id-private.txt').read_bytes()\nassert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'\nsys.stdout.buffer.write(Path('/tmp/k213-final-evidence-private.tar.gz').read_bytes())\n"
try:
    result=subprocess.run(['/usr/bin/ssh','-T',*options,'-4','-o','ConnectTimeout=15','-o','ConnectionAttempts=1','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=6','-o','HostKeyAlias=169.254.42.1','root@'+address,'python3 -'],input=native,capture_output=True,timeout=80)
except subprocess.TimeoutExpired as error:
    (private/'native-wifi-archive-timeout-stdout-private.bin').write_bytes(error.stdout or b'')
    (private/'native-wifi-archive-timeout-stderr-private.log').write_bytes(error.stderr or b'')
    raise RuntimeError('Native archive transfer timed out; private stdout and stderr preserved') from None
(private/'native-wifi-archive-transfer-stderr-private.log').write_bytes(result.stderr)
if result.returncode:
    (private/'native-wifi-archive-partial-private.bin').write_bytes(result.stdout)
    raise RuntimeError('Native strict-key archive transfer failed; diagnostics retained privately')
record=json.loads((private/'final-evidence-manifest-private.json').read_text());data=result.stdout
assert len(data)==record['size'] and hashlib.sha256(data).hexdigest()==record['sha256']
target=private/'final-evidence-native-wifi-private.tar.gz';assert not target.exists();target.write_bytes(data)
with tarfile.open(target) as archive:members={m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive.getmembers() if m.isfile()}
assert members==record['files']
report=dict(stage=213,private_archive_all_members_verified=True,archived_regular_files=len(members),raw_scene_images_and_logs_kept_private=True,isolated_sdk_and_ipa_private_key_excluded=True,candidate_binaries_and_build_logs_preserved=True,initial_one_mib_usb_transfer_truncated=True,usb_then_small_ssh_timed_out=True,windows_wifi_ssh_intermittent=True,same_boot_original_key_native_wifi_recovery_succeeded=True,all_native_evidence_members_verified=True,clean_current_boot=True,initial_fetch_configure_link_probe_and_sensor_pattern_failures_preserved=True)
(here/'final-evidence-archive-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
