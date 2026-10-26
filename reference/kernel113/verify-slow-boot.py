from pathlib import Path
import hashlib, json, re, tarfile
from inspect_live_fdt import fdt

out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
def read(name):
    path=out/(name+'.tar')
    with tarfile.open(path) as t:
        data={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
    for line in data['SHA256SUMS'].decode().splitlines():
        digest,file=line.split('  ',1)
        assert hashlib.sha256(data[file.removeprefix('./')]).hexdigest()==digest
    return data, hashlib.sha256(path.read_bytes()).hexdigest()

slow,sha=read('slow-boot-radio-clean-5')
assert sha=='6144b3bc82c4dff445c1842dc84bc640670596e5f1886943ad96f0a6dc59103c'
assert slow['state.txt'].splitlines()[-1]==b'512'
log=slow['dmesg.txt'].decode()
assert log.count('WARNING:')==1 and 'WARNING: sound/soc/codecs/wcd934x.c:1457' in log
assert 'Efuse sense is not complete val=0, ret=-22' in log
assert b'/dev/sda16 / f2fs rw' in slow['mounts.txt']
assert slow['nv-check.txt'].count(b': OK')==6 and slow['source-check.txt'].count(b': OK')==4
parts=dict(line.split('  ')[::-1] for line in slow['partition-check.sha256'].decode().splitlines())
for dev,file in [('/dev/sde11','boot-partition-k113.img'),('/dev/sde32','logdump-k113-sensor-power.img')]:
    assert parts[dev]==hashlib.sha256((out/file).read_bytes()).hexdigest()
assert parts['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
expected=fdt((out/'dtb-sensor-power').read_bytes())
live=fdt(slow['live-fdt-private.dtb'])
assert expected.keys()==live.keys()
for name,props in expected.items(): assert all(live[name].get(k)==v for k,v in props.items())
clean,qsha=read('audio-radio-quiesce-5')
assert clean['boot-id-private.txt']==slow['boot-id-private.txt']
assert clean['adsp-final-state.txt'].strip()==b'offline'
assert clean['pcm-idle.txt'].strip()==b'closed\nclosed'
assert clean['amps.txt'].count(b'powered=0 muted=1')==2
assert clean['nv-check.txt'].count(b': OK')==6 and clean['source-check.txt'].count(b': OK')==4
report=dict(kernel_build=113,slow_boot_archive_sha256=sha,quiesce_archive_sha256=qsha,
            warning_source='WCD934x efuse sensing after SLIMbus DMA preparation failed',
            taint=512,warning_count=1,codec_enospc_errors=log.count('ASoC error (-28)'),
            slim_dma_prepare_failures=log.count('unable to prepare channel'),
            dpu_timeouts=log.count('frame done timeout'),gpu_faults=log.count('*** gpu fault'),
            boot_logdump_live_dtb_and_nv6_sources4_persist_preserved=True,
            user_reports_phosh_visible=True,full_reboot_hardware_gate_pass=False,
            audio_radio_quiesce_completed=True,adsp_final_state='offline',
            next_reboot_accepted=False,raw_logs_private=True,goal_complete=False)
(ref/'slow-boot-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
