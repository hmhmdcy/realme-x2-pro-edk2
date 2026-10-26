"""Read-only verification of device captures, failed candidates and final handoff."""
from pathlib import Path
import gzip
import hashlib
import json
import re

root = Path(__file__).resolve().parent
sha = lambda data: hashlib.sha256(data).hexdigest()
captures = json.loads((root/'capture-validation.json').read_text())
for name, record in captures.items():
    compressed = (root/(name+'.gz')).read_bytes()
    raw = gzip.decompress(compressed)
    assert raw == (root/(name+'.txt')).read_bytes(), name
    assert len(raw)==record['raw_bytes'] and sha(raw)==record['raw_sha256'], name
    assert len(compressed)==record['gzip_bytes'] and sha(compressed)==record['gzip_sha256'], name

def display_test(name, strict_timing=True):
    text = (root/(name+'.txt')).read_text()
    samples = re.findall(r'pattern=(\d) scanout CRC (0x\w+) (0x\w+) (0x\w+)',text)
    assert [s[0] for s in samples] == (['0']*8+['1']*8+['0']*8)*3, name
    for i, sample in enumerate(samples):
        expected = ('0x25e11871','0x25e11871') if (i//8)%3==1 else ('0x69961448','0x60af15f5')
        assert sample[2:]==expected, (name,i,sample)
    sequences = [int(s) for s in re.findall(r'^vblank sequence=(\d+)$',text,re.M)]
    assert len(sequences)==18 and all(sequences[i+1]-sequences[i]==59 for i in range(0,18,2)), name
    elapsed = [float(t) for t in re.findall(r'60 vblank waits elapsed=([\d.]+)',text)]
    assert len(elapsed)==9
    if strict_timing:
        assert all(.95<t<1.05 for t in elapsed), (name,elapsed)
    assert text.count('Native panel disable/unprepare and prepare/enable cycle passed')==9
    assert text.count('Native KMS mode setting, scanout/vblank and console restoration passed')==9
    assert text.endswith('120\n256\n400\nconnected\n0\n')
    return dict(boot_id=text.splitlines()[1],crc_aba_repetitions=3,crc_samples=72,
        display_off_on_cycles=9,vblank_elapsed_seconds=elapsed)

before = (root/'before-dmesg.txt').read_text()
assert len(re.findall('Unhandled context fault:',before))==10
failed_reboot = (root/'reboot-boot-dmesg.txt').read_text()
assert 'WARNING:' in failed_reboot and 'dsi_err_worker: status=c' in failed_reboot
assert 'Unhandled context fault:' not in failed_reboot
assert 'wait vblank: Device or resource busy' in (root/'reboot-kms-first.txt').read_text()
no_start = (root/'no-start-boot-dmesg.txt').read_text()
assert 'iova=0x00000000' in no_start and 'WARNING:' in no_start
assert 'wait vblank: Device or resource busy' in (root/'no-start-display-tests.txt').read_text()
detached = (root/'detach-boot-dmesg.txt').read_text()
assert 'Unhandled context fault:' not in detached and 'dsi_err_worker: status=c' in detached
assert '60 vblank waits elapsed=0.994044' in (root/'reprepare-tests.txt').read_text()
assert 'enable scanout CRC: No such file or directory' in (root/'reprepare-tests.txt').read_text()

tests = {name:display_test(name) for name in ('drain-display-tests','drain-reboot-display-tests')}
boot_ids = [record['boot_id'] for record in tests.values()]
assert len(set(boot_ids))==2
logs = {}
for name in ('drain-boot-dmesg','drain-tested-dmesg','drain-reboot-boot-dmesg','final-dmesg'):
    log = (root/(name+'.txt')).read_text()
    assert '#68 SMP' in log and 'msmdrmfb frame buffer device' in log, name
    assert 'boot INTF1: tearcheck=0x1 autorefresh=0x80000001 trigger=0x0' in log, name
    assert 'boot INTF1 stopped: tearcheck=0x0 autorefresh=0x1 trigger=0x0' in log, name
    assert 'boot CTL0 cleared: layer0=0x0 layer1=0x0 fetch=0x0' in log, name
    assert 'power mode 0x9c (stock 0x9c)' in log, name
    assert not re.search(r'Unhandled context fault:|Kernel panic|\bOops:|\bBUG:|WARNING:|Call trace:|dsi_err_worker:|kickoff timeout|wait for commit done returned',log), name
    logs[name] = dict(smmu_faults=0,dsi_errors=0,warnings=0,panel_power_reads=log.count('power mode 0x9c (stock 0x9c)'))

facts = (root/'final-facts.txt').read_text()
assert facts.splitlines()[1:3]==[boot_ids[-1],'0']
assert 'PARTNAME=logdump' in facts and 'logdump_partition=/dev/sde32' in facts
assert '8e43d13658a1d332c441f68a6008e7ebb855177b59fbeb447a196195239f1ee5  /dev/sde32' in facts
assert '57508887131ae55cf9465fa1a44280fa45b507a3439345ffe635dc7544eaa999  -' in facts
assert 'Synaptics' in facts and 'configured\nhigh-speed\na600000.usb' in facts
assert all(str(freq) in facts for freq in (1785600,2419200,2956800))
assert all(re.search(r'^\s*\d+\s+\d+\s+\d+\s+'+lun+'$',facts,re.M) for lun in ('sda','sdb','sdc','sdd','sde','sdf'))
assert '\nK74_NATIVE_EUD_OK\n' in (root/'native-eud.txt').read_text()
native_events = (root/'native-eud.events.txt').read_text()
assert len(re.findall(r'TX native .*sync=False',native_events))==2
assert native_events.count('TX native')==native_events.count('ACK native')==3
assert 'SYNC fresh Ctrl-U receipt; begin native input' in native_events
assert all('attempt=1' in line for line in native_events.splitlines() if 'TX native' in line)
for prefix in ('handoff','same-image','no-start','detach','drain','drain-reboot'):
    events = [json.loads(line) for line in (root/(prefix+'-f1-wsl.events.jsonl')).read_text().splitlines()]
    assert len([event for event in events if event['event']=='out_submit'])==1
    assert any(event['event']=='receipt' and event['text']=='F1' for event in events)
for prefix in ('handoff','no-start-ready','detach','drain'):
    report = json.loads((root/(prefix+'-flash-validation.json')).read_text(encoding='utf-8-sig'))
    assert report['flashed_partitions']==['logdump'] and report['flash_success'] and report['reboot_success']
    assert not report['boot_written'] and not report['userdata_written'] and not report['gpt_written']
assert json.loads((root/'drain-reboot-reboot.json').read_text(encoding='utf-8-sig'))['no_flash']
host = json.loads((root/'host-final.json').read_text(encoding='utf-8-sig'))
assert host['pnp_ok'] and host['eud_windows_shared'] and not host['eud_attached'] and not host['owners']
preserved = json.loads((root/'core-preservation.json').read_text())
assert preserved['config_unchanged'] and preserved['dtb_unchanged']
assert len(preserved['unchanged'])==8
assert json.loads((root/'patch-validation.json').read_text())['applied_files_match_actual_source']

result = dict(captures_verified=len(captures),baseline_smmu_faults=10,
    failed_candidates_preserved=['#65 warm reboot DSI/vblank','#66 no-start SMMU/DSI','#67 DSI until first full reprepare'],
    tests=tests,logs=logs,final_boot_id=boot_ids[-1],taint=0,
    final_partition_hashes_pass=True,only_logdump_written=True,
    eud_echo_and_six_f1_pass=True,preserved_cpu_touch_ufs_usb=True,
    native_boot_handoff_verified=True,gpu_rendering_verified=False,refresh90_verified=False,
    optical_output_verified=False,brightness_hardware_readback_verified=False,suspend_resume_verified=False)
print(json.dumps(result,indent=2))
