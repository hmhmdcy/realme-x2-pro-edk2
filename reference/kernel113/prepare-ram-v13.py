from pathlib import Path
import hashlib,json,tarfile
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
out=Path('/mnt/e/edk2-samurai-out/kernel113')
source=out/'c28-reference-private/firmware'
proof=json.loads((ref/'c28-reference-validation.json').read_text())
assert proof['same_linked_base'] and proof['candidate_span_fits_original']
for name,digest in proof['files'].items():
    assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest
package=out/'c28-slpi-candidate-private.tar'
assert not package.exists()
with tarfile.open(package,'w') as tar:
    for path in sorted(source.iterdir()):
        tar.add(path,arcname=path.name,recursive=False)
text=(ref/'test-sensor-ram-v11.sh').read_text()
text=text.replace('k113-reboot-audio-clean-7/','k113-reboot-audio-clean-9/')
text=text.replace('ram-v11','ram-v13').replace('RAM_V11','RAM_V13')
text=text.replace('owner=\nrecover_owner=', 'original_fw=qcom/sm8150/realme/samurai/slpi.mdt\nowner=\nrecover_owner=')
anchor='    cat "$power" > "$dest/power-final.txt"'
assert text.count(anchor)==1
text=text.replace(anchor,'''    if [ "$(cat "$node/state")" = offline ]; then
        printf '%s\\n' "$original_fw" > "$node/firmware"
    fi
    cat "$node/firmware" > "$dest/firmware-final.txt"
'''+anchor)
anchor='modules=/var/lib/samurai/k113-modules-candidate'
assert text.count(anchor)==1
text=text.replace(anchor,'''candidate=/lib/firmware/qcom/sm8150/realme/samurai-c28-trial
test "$(cat "$node/firmware")" = "$original_fw"
cat "$node/firmware" > "$dest/firmware-before.txt"
(cd "$candidate" && sha256sum -c SHA256SUMS) > "$dest/candidate-firmware-check.txt"
cp "$candidate/SHA256SUMS" "$dest/candidate-firmware.sha256"
printf 'qcom/sm8150/realme/samurai-c28-trial/slpi.mdt\\n' > "$node/firmware"
test "$(cat "$node/firmware")" = qcom/sm8150/realme/samurai-c28-trial/slpi.mdt
cat "$node/firmware" > "$dest/firmware-selected.txt"
'''+anchor)
(ref/'test-sensor-ram-v13.sh').write_text(text)
clean=(ref/'quiesce-clean-boot7.sh').read_text()
clean=clean.replace('k113-reboot-audio-clean-7/','k113-reboot-audio-clean-8/')
(ref/'quiesce-clean-boot8.sh').write_text(clean)
digest=hashlib.sha256(package.read_bytes()).hexdigest()
stager='''#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#113 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-reboot-audio-clean-8/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
test "$(cat /sys/class/remoteproc/remoteproc0/firmware)" = qcom/sm8150/realme/samurai/slpi.mdt
echo '@SHA@  /tmp/k113-c28-slpi-candidate-private.tar' | sha256sum -c - >/run/k113-c28-staging-check.txt
dest=/lib/firmware/qcom/sm8150/realme/samurai-c28-trial
test ! -e "$dest"
mkdir -m700 "$dest"
tar -C "$dest" -xf /tmp/k113-c28-slpi-candidate-private.tar
(cd "$dest" && sha256sum -c SHA256SUMS) >> /run/k113-c28-staging-check.txt
test -z "$(find "$dest" -type l -print)"
find "$dest" -type f -exec chmod 440 '{}' ';'
chmod 550 "$dest"
sync
echo C28_SLPI_SEPARATE_READONLY_FILES_STAGED_NO_DSP_STARTED
'''.replace('@SHA@',digest)
(ref/'stage-c28-reference.sh').write_text(stager)
(ref/'c28-candidate-package.json').write_text(json.dumps(dict(sha256=digest,bytes=package.stat().st_size,
    separate_linux_files=True,stock_firmware_overwritten=False,linux_trial_started=False),indent=2)+'\n')
print('C28_SLPI_SEPARATE_FILES_AND_BOOT9_TRIAL_PREPARED')
