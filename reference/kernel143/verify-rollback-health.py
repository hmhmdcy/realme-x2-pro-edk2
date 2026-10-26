from pathlib import Path
import hashlib
import json
import tarfile
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel143');out=Path('/mnt/e/edk2-samurai-out/kernel143')
def load(name,boot=None):
    with tarfile.open(out/name) as tf:data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
    for line in data['SHA256SUMS'].decode().splitlines():
        digest,key=line.split('  ',1);assert hashlib.sha256(data[key.removeprefix('./')]).hexdigest()==digest
    assert data['boot-id-private.txt']==(boot if boot is not None else out.joinpath('embedded-boot-id-private.txt').read_bytes())
    return data
data=load('rollback-settled-health-private.tar.gz');report=json.loads(data['health-validation.json'])
assert report['current_kernel']==140 and report['same_boot'] and report['samples']==8
assert report['taint_values']==[0] and report['counters_unchanged']
assert report['desktop_pids_unchanged'] and report['phosh_present_final'] and report['phoc_present_final']
cleanup=load('recorder-cleanup-private.tar.gz',out.joinpath('rejected-boot-id-private.txt').read_bytes())
removed=json.loads(cleanup['cleanup-validation.json'])
assert all(removed[key] for key in ['recorder_already_terminal','recorder_service_removed','boot_link_removed','recorder_pidfile_removed','own_trace_instance_absent','gui_three_files_preserved'])
report.update(archive_manifest_verified=True,boot_logdump_gpt_live_dtb_and770_modules_verified=True,
    rejected143_threaded_console_not_running=True,temporary_recorder_cleanup_archive_verified=True,rollback_goal_not_complete=True)
ref.joinpath('rollback-health-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
