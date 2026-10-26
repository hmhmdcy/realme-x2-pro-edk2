from pathlib import Path
import hashlib,json,subprocess

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
source=(ref/'test-sensor-ram-v17.sh').read_text()
text=source.replace('ram-v17','ram-census14').replace('RAM_V17','RAM_CENSUS14')
text=text.replace('k113-reboot-audio-clean-13/','k113-reboot-audio-clean-14/')
client=ref/'ssc-suid-census.py'
digest=hashlib.sha256(client.read_bytes()).hexdigest()
assert digest==json.loads((ref/'ssc-suid-census-host-validation.json').read_text())['client_sha256']
anchor="sleep 20\nprintf 'PROXIMITY_AUTOMATIC_SAMPLE_OPEN_10_SECONDS\\n'"
assert text.count(anchor)==1
queries=f'''sleep 20
echo '{digest}  /var/lib/samurai/k113-tools/ssc-suid-census.py' | sha256sum -c - > "$dest/census-client-check.txt"
printf 'SSC_ALL_INSTANCE_CENSUS_OPEN_18_SECONDS\\n'
set +e
timeout -s TERM -k 2 40 python3 /var/lib/samurai/k113-tools/ssc-suid-census.py --output "$dest/census-all" --duration 18 > "$dest/census-all-host.txt" 2>&1
printf '%s\\n' "$?" > "$dest/census-all-exit.txt"
set -e
test "$(cat "$node/state")" = running
kill -0 "$owner"
printf 'SSC_DEFAULT_INSTANCE_CONTROL_OPEN_18_SECONDS\\n'
set +e
timeout -s TERM -k 2 40 python3 /var/lib/samurai/k113-tools/ssc-suid-census.py --output "$dest/census-default" --duration 18 --default > "$dest/census-default-host.txt" 2>&1
printf '%s\\n' "$?" > "$dest/census-default-exit.txt"
set -e
test "$(cat "$node/state")" = running
kill -0 "$owner"
printf 'SSC_CENSUS_CLOSED_CONTINUING_SIX_EXISTING_CLI_CONTROLS\\n'
printf 'PROXIMITY_AUTOMATIC_SAMPLE_OPEN_10_SECONDS\\n' '''.rstrip()
text=text.replace(anchor,queries)
path=ref/'test-sensor-ram-census14.sh'
if path.exists():assert path.read_text()==text
else:path.write_text(text)
subprocess.run(['sh','-n',str(path)],check=True)
files={name:hashlib.sha256((ref/name).read_bytes()).hexdigest() for name in
    ['test-sensor-ram-census14.sh','ssc-suid-census.py','quiesce-clean-boot13.sh']}
(ref/'census14-trial-preparation.json').write_text(json.dumps(dict(files=files,
    fresh_boot_checkpoint_required='reboot-audio-clean-14',base_configuration='RAM v17 identical escaped TAB copy',
    firmware_reference='original 00121',only_new_variable='Independent full/default SUID census before existing CLI queries',
    query_measurement_stream=False,calibration_changed=False,firmware_changed=False,
    trial_completed=False,phone_changed=False),indent=2)+'\n')
print(json.dumps(dict(trial_script_syntax_valid=True,files=files,phone_changed=False)))
