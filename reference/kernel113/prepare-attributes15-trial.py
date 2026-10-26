from pathlib import Path
import hashlib,json,subprocess
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
source=(ref/'test-sensor-ram-census14.sh').read_text()
text=source.replace('ram-census14','ram-attributes15').replace('RAM_CENSUS14','RAM_ATTRIBUTES15')
text=text.replace('k113-reboot-audio-clean-14/','k113-reboot-audio-clean-15/')
start=text.index("echo '7618fe7e4f54b6ce8e9b9437961afc245d7c35b856b0d09e785a391958ad2656")
end=text.index("printf 'PROXIMITY_AUTOMATIC_SAMPLE_OPEN_10_SECONDS",start)
digest=hashlib.sha256((ref/'ssc-attribute-census.py').read_bytes()).hexdigest()
assert digest==json.loads((ref/'ssc-attribute-census-host-validation.json').read_text())['client_sha256']
queries=f'''echo '{digest}  /var/lib/samurai/k113-tools/ssc-attribute-census.py' | sha256sum -c - > "$dest/attribute-client-check.txt"
printf 'SSC_ALL_INSTANCE_ATTRIBUTE_CENSUS_OPEN_25_SECONDS\\n'
set +e
timeout -s TERM -k 2 45 python3 -B /var/lib/samurai/k113-tools/ssc-attribute-census.py --output "$dest/attributes" --duration 25 > "$dest/attributes-host.txt" 2>&1
printf '%s\\n' "$?" > "$dest/attributes-exit.txt"
set -e
test "$(cat "$node/state")" = running
kill -0 "$owner"
printf 'SSC_ATTRIBUTE_CENSUS_CLOSED_CONTINUING_SIX_CLI_CONTROLS\\n'
'''
text=text[:start]+queries+text[end:]
path=ref/'test-sensor-ram-attributes15.sh'
if path.exists():assert path.read_text()==text
else:path.write_text(text)
subprocess.run(['sh','-n',str(path)],check=True)
quiesce=(ref/'quiesce-clean-boot13.sh').read_text().replace('k113-reboot-audio-clean-13/','k113-reboot-audio-clean-14/')
path=ref/'quiesce-clean-boot14.sh'
if path.exists():assert path.read_text()==quiesce
else:path.write_text(quiesce)
subprocess.run(['sh','-n',str(path)],check=True)
files={name:hashlib.sha256((ref/name).read_bytes()).hexdigest() for name in
    ['ssc-attribute-census.py','test-sensor-ram-attributes15.sh','quiesce-clean-boot14.sh']}
(ref/'attributes15-trial-preparation.json').write_text(json.dumps(dict(files=files,
    fresh_boot_checkpoint_required='reboot-audio-clean-15',firmware_reference='original 00121',
    base_configuration='same RAM v17 escaped TAB values',only_new_variable='Read attributes for each full-directory UID',
    attribute_message_ids=[1,128],measurement_stream_requested_by_new_client=False,
    calibration_changed=False,firmware_changed=False,phone_trial_completed=False),indent=2)+'\n')
print(json.dumps(dict(files=files,syntax_valid=True,phone_changed=False)))
