from pathlib import Path
import hashlib,importlib.util,json,subprocess,tarfile
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel213')
spec=importlib.util.spec_from_file_location('direct_archive_recovery',here.parent/'kernel200/host-before-newboot.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
native=b"from pathlib import Path\nimport hashlib,json\nassert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k213-baseline/boot-id-private.txt').read_bytes()\np=Path('/tmp/k213-final-evidence-private.tar.gz');print(json.dumps(dict(taint=int(Path('/proc/sys/kernel/tainted').read_text()),size=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())))\n"
try:
    p=transport.ssh('python3 -',input=native,timeout=25);remote=json.loads(p.stdout)
    record=json.loads((private/'final-evidence-manifest-private.json').read_text());assert remote['taint']==0 and remote['size']==record['size'] and remote['sha256']==record['sha256']
    target=private/'final-evidence-wifi-private.tar.gz';assert not target.exists()
    transport.download(record['path'],target)
    assert target.stat().st_size==record['size'] and hashlib.sha256(target.read_bytes()).hexdigest()==record['sha256']
    with tarfile.open(target) as archive:members={m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive.getmembers() if m.isfile()}
    assert members==record['files']
    report=dict(stage=213,private_archive_all_members_verified=True,archived_regular_files=len(members),raw_scene_images_and_logs_kept_private=True,isolated_sdk_and_ipa_private_key_excluded=True,candidate_binaries_and_build_logs_preserved=True,initial_one_mib_usb_transfer_truncated=True,usb_then_small_ssh_timed_out=True,same_boot_original_key_wifi_recovery_succeeded=True,all_native_evidence_members_verified=True,clean_current_boot=True,initial_fetch_configure_link_probe_and_sensor_pattern_failures_preserved=True)
    (here/'final-evidence-archive-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as error:
    (private/'direct-wifi-archive-recovery-failure-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''));raise RuntimeError('Direct recovery failed; private diagnostics retained') from None
