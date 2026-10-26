from pathlib import Path
import hashlib,json

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
out=Path('/mnt/e/edk2-samurai-out/kernel113')
original=Path('/mnt/e/edk2-samurai-out/kernel111/source-files/k111-sensor-sources-readonly/sensors-vendor/config/msmnile_mmc5603nj.json')
payload=original.read_bytes()
assert hashlib.sha256(payload).hexdigest()=='f84bee57583cdc8b8eec7c8cc0d2aea477ac20932ac1cde4e2b5b670fb091fe4'
inside=False; escaped=False; replacements=[]; fixed=bytearray()
for index,char in enumerate(payload):
    if inside and not escaped and char<32:
        assert char==9
        fixed.extend(b'\\t');replacements.append(index)
    else: fixed.append(char)
    if escaped: escaped=False
    elif inside and char==92: escaped=True
    elif char==34: inside=not inside
assert not inside and len(replacements)==1 and len(fixed)==len(payload)+1
fixed=bytes(fixed)
assert json.loads(payload,strict=False)==json.loads(fixed)
target=out/'magnetometer-config-escaped-control-private.json'
if target.exists(): assert target.read_bytes()==fixed
else: target.write_bytes(fixed)
digest=hashlib.sha256(fixed).hexdigest()
(ref/'magnetometer-config-encoding-candidate.json').write_text(json.dumps(dict(
    original_sha256=hashlib.sha256(payload).hexdigest(),candidate_sha256=digest,
    original_bytes=len(payload),candidate_bytes=len(fixed),literal_tabs_escaped=1,
    decoded_json_values_identical=True,strict_json_valid_after=True,
    source_configuration_changed=False,persist_or_calibration_changed=False,
    runtime_trial_completed=False),indent=2)+'\n')

text=(ref/'test-sensor-ram-v16.sh').read_text()
text=text.replace('ram-v16','ram-v17').replace('RAM_V16','RAM_V17')
text=text.replace('k113-reboot-audio-clean-12/','k113-reboot-audio-clean-13/')
start=text.index('candidate=/lib/firmware/')
end=text.index('modules=/var/lib/samurai/',start)
replacement='''test "$(cat "$node/firmware")" = "$original_fw"
cat "$node/firmware" > "$dest/firmware-before.txt"
cat "$node/firmware" > "$dest/firmware-selected.txt"
sha256sum "$src/firmware"/* > "$dest/original-firmware.sha256"
'''
text=text[:start]+replacement+text[end:]
anchor='cp -a "$src/sensors-vendor/config/." "$root/sensors/config/"\n'
assert text.count(anchor)==1
patch=f'''echo '{digest}  /var/lib/samurai/k113-tools/magnetometer-config-escaped-control-private.json' | sha256sum -c - > "$dest/config-candidate-check.txt"
echo "f84bee57583cdc8b8eec7c8cc0d2aea477ac20932ac1cde4e2b5b670fb091fe4  $root/sensors/config/msmnile_mmc5603nj.json" | sha256sum -c - > "$dest/config-original-check.txt"
cp /var/lib/samurai/k113-tools/magnetometer-config-escaped-control-private.json "$root/sensors/config/msmnile_mmc5603nj.json"
echo "{digest}  $root/sensors/config/msmnile_mmc5603nj.json" | sha256sum -c - > "$dest/config-patched-check.txt"
'''
text=text.replace(anchor,anchor+patch)
(ref/'test-sensor-ram-v17.sh').write_text(text)
clean=(ref/'quiesce-clean-boot11.sh').read_text()
(ref/'quiesce-clean-boot12.sh').write_text(clean.replace('k113-reboot-audio-clean-11/','k113-reboot-audio-clean-12/'))
print('V17_ORIGINAL_FIRMWARE_WITH_ONE_RAM_ONLY_JSON_TAB_ESCAPE_PREPARED')
