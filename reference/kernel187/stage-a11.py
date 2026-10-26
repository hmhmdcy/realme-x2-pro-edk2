"""Stage only hash-verified handset SLPI files in a separate read-only directory."""
from pathlib import Path
import hashlib,json,subprocess,tarfile
import host

ref=Path(__file__).resolve().parent
proof=json.loads((ref.parent/'kernel186/a11-reference-validation.json').read_text())
assert proof['same_linked_base'] and proof['candidate_span_fits_original'] and proof['split_file_sizes_match_mdt']
source=host.PRIVATE.parent/'kernel186/a11-reference-private/firmware'
assert all(hashlib.sha256((source/name).read_bytes()).hexdigest()==digest for name,digest in proof['files'].items())
archive=host.PRIVATE/'a11-slpi-candidate-private.tar'
assert not archive.exists()
with tarfile.open(archive,'w') as tar:
    for name in sorted(proof['files']):
        path=source/name
        assert path.is_file() and not path.is_symlink()
        item=tar.gettarinfo(str(path),arcname=name)
        item.uid=item.gid=0;item.uname=item.gname='root';item.mode=0o440
        with path.open('rb') as f:tar.addfile(item,f)
    raw=''.join(digest+'  '+name+'\n' for name,digest in proof['files'].items()).encode()
    import io
    item=tarfile.TarInfo('SHA256SUMS');item.size=len(raw);item.mode=0o440
    tar.addfile(item,io.BytesIO(raw))
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
host.upload(archive,'/tmp/k187-a11-slpi-candidate-private.tar')
script='''#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#183 '
cmp /proc/sys/kernel/random/boot_id /var/lib/samurai/k186-reboot-runtime-r2/boot-id-private.txt
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
test "$(cat /sys/class/remoteproc/remoteproc0/firmware)" = qcom/sm8150/realme/samurai/slpi.mdt
dest=/lib/firmware/qcom/sm8150/realme/samurai-a11-r187
test ! -e "$dest"
echo '%s  /tmp/k187-a11-slpi-candidate-private.tar' | sha256sum -c - >/run/k187-staging-private.txt
mkdir -m700 "$dest"
tar -C "$dest" -xf /tmp/k187-a11-slpi-candidate-private.tar
(cd "$dest" && sha256sum -c SHA256SUMS) >>/run/k187-staging-private.txt
test -z "$(find "$dest" -type l -print)"
find "$dest" -type f -exec chmod 440 '{}' ';'
chmod 550 "$dest"
sync
echo A11_SEPARATE_FILES_STAGED_NO_DSP_START
'''%digest
path=ref/'stage-a11.sh'
path.write_text(script)
subprocess.run(['sh','-n',str(path)],check=True)
host.ssh('test ! -e /var/lib/samurai/k187-tools && mkdir -m700 /var/lib/samurai/k187-tools')
host.upload(path,'/var/lib/samurai/k187-tools/stage-a11.sh')
p=host.ssh('sh /var/lib/samurai/k187-tools/stage-a11.sh',timeout=45)
(host.PRIVATE/'a11-stage-host-private.log').write_bytes(p.stdout+p.stderr)
report=dict(stage=187,candidate_archive_sha256=digest,firmware_versions=proof['firmware_versions'],
    separate_readonly_firmware_directory=True,original_firmware_not_overwritten=True,
    no_modem_image_flashed=True,no_dsp_started=True,current_kernel_build=183)
(ref/'a11-staging-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
