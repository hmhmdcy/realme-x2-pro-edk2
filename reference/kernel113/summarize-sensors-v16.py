from pathlib import Path
import hashlib,json,re,sys,tarfile

out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
trial=sys.argv[1] if len(sys.argv)>1 else 'v16'
assert trial in ('v16','v17','census14','attributes15')
number={'v16':12,'v17':13,'census14':14,'attributes15':15}[trial]
selection=('qcom/sm8150/realme/samurai-c35-trial/slpi.mdt' if trial=='v16' else 'qcom/sm8150/realme/samurai/slpi.mdt')
path=out/f'sensor-ram-{trial}.tar'
with tarfile.open(path) as tar:
    data={m.name.removeprefix('./'):tar.extractfile(m).read() for m in tar if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
with tarfile.open(out/f'reboot-audio-clean-{number}.tar') as tar:
    assert data['boot-id-private.txt']==tar.extractfile('./boot-id-private.txt').read()
assert data['firmware-selected.txt'].strip()==selection.encode()
assert data['firmware-final.txt']==data['firmware-before.txt']
assert data['slpi-final-state.txt'].strip()==b'offline' and data['power-final.txt'].strip()==b'vdd=0 vddio=0'
assert data['kernel-state-after.txt'].splitlines()[-1]==b'0'
results={}
for kind in ('accelerometer','proximity','light','magnetometer','gyroscope','compass'):
    log=data.get(kind+'.txt',b'').decode(errors='replace')
    key='query-exit.txt' if kind=='accelerometer' else kind+'-exit.txt'
    code=int(data[key]) if key in data else None
    assert key in data and kind+'.txt' in data, 'query not completed: '+kind
    results[kind]=dict(query_exit=code,
        sample_count=len(re.findall(r'^'+kind.capitalize()+r' sensor measurement:',log,re.M)),
        names=sorted(set(re.findall(r'^.*  name: ([^\r\n]+)',log,re.M))),
        vendors=sorted(set(re.findall(r'^.*  vendor: ([^\r\n]+)',log,re.M))),
        disable_confirmed='Sensor disable request sent successfully' in log,
        initialized=code==0)
report=dict(archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    firmware_reference=('rmx1931-global-c35-00098' if trial=='v16' else 'original-rmx1931-00121'),boot_checkpoint=f'reboot-audio-clean-{number}',
    sensors=results,original_firmware_selector_restored=True,slpi_offline_and_sensor_power_off=True,
    taint=0,all_sensors_accepted=False,goal_complete=False)
if trial in ('v17','census14','attributes15'):
    candidate=json.loads((ref/'magnetometer-config-encoding-candidate.json').read_text())
    for key in ('config-candidate-check.txt','config-original-check.txt','config-patched-check.txt'):
        assert data[key].strip().endswith(b': OK')
    def manifest(payload):
        return {name.removeprefix('./'):digest for digest,name in
            (line.split('  ',1) for line in payload.decode().splitlines())}
    for key in ('ram-tree-before.sha256','ram-tree-after.sha256'):
        assert manifest(data[key])['sensors/config/msmnile_mmc5603nj.json']==candidate['candidate_sha256']
    assert data['source-after.txt'].count(b': OK')==4 and data['nv-after.txt'].count(b': OK')==6
    report.update(one_literal_tab_escaped_in_ram_copy=True,decoded_configuration_values_unchanged=True,
        original_source_and_nv_unchanged=True,all_sensor_queries_completed=True,
        syntax_escape_alone_did_not_enable_magnetometer=results['magnetometer']['query_exit']==254)
(ref/f'sensors-{trial}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
