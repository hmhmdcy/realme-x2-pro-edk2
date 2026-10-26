"""Read-only verification of the archived native-display evidence."""
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
    assert len(raw) == record['raw_bytes'] and sha(raw) == record['raw_sha256'], name
    assert len(compressed) == record['gzip_bytes'] and sha(compressed) == record['gzip_sha256'], name

tests = {}
for name, expected_sha in (
    ('display-cycle-tests.txt','7f7b9f9d402e3b4734624e2728b31ef16ae214d1102bad2ae45ec04462240143'),
    ('reboot-display-tests.txt','04990f4ee18874a173611b760cd6cafe0e159ad6e292fc5ee49055a139b33b62'),
):
    raw = (root/name).read_bytes()
    assert sha(raw) == expected_sha, name
    text = raw.decode()
    samples = re.findall(r'pattern=(\d) scanout CRC (0x\w+) (0x\w+) (0x\w+)',text)
    assert [s[0] for s in samples] == ['0']*8+['1']*8+['0']*8
    pairs = [(s[2],s[3]) for s in samples]
    assert all(p == ('0x69961448','0x60af15f5') for p in pairs[:8]+pairs[16:])
    assert all(p == ('0x25e11871','0x25e11871') for p in pairs[8:16])
    sequences = [int(s) for s in re.findall(r'^vblank sequence=(\d+)$',text,re.M)]
    assert len(sequences)==6 and all(sequences[i+1]-sequences[i]==59 for i in (0,2,4))
    elapsed = [float(t) for t in re.findall(r'60 vblank waits elapsed=([\d.]+)',text)]
    assert len(elapsed)==3 and all(.95<t<1.05 for t in elapsed)
    assert text.count('Native panel disable/unprepare and prepare/enable cycle passed')==3
    assert text.count('Native KMS mode setting, scanout/vblank and console restoration passed')==3
    assert text.endswith('120\n256\n400\nconnected\n0\n')
    tests[name] = dict(sha256=expected_sha,crc_aba_pass=True,crc_samples=len(samples),
        cycles_passed=3,vblank_waits=60,vblank_elapsed_seconds=elapsed)

facts = (root/'final-facts.txt').read_text()
assert facts.splitlines()[1:3] == ['fc4fe164-1e90-402a-b841-ce870ba9ddfb','0']
assert 'PARTNAME=logdump' in facts and 'logdump_partition=/dev/sde32' in facts
assert 'c7778d45c336b35cf75c2842c083b513343f59a0a1864fe52ad2105d3d55e6c7  /dev/sde32' in facts
assert '57508887131ae55cf9465fa1a44280fa45b507a3439345ffe635dc7544eaa999  -' in facts
assert 'syna,s3706a' in facts or 'Synaptics' in facts
assert all(str(freq) in facts for freq in (1785600,2419200,2956800))
assert all(re.search(r'^\s*\d+\s+\d+\s+\d+\s+'+lun+'$',facts,re.M) for lun in ('sda','sdb','sdc','sdd','sde','sdf'))
assert 'configured\nhigh-speed\na600000.usb' in facts
log = (root/'final-dmesg.txt').read_text()
assert '#64 SMP' in log and 'msmdrmfb frame buffer device' in log
assert log.count('power mode 0x9c (stock 0x9c)')==4
assert not re.search(r'Kernel panic|\bOops:|\bBUG:|WARNING:|\bunderflow\b|Call trace:',log)
fault_times = [float(t) for t in re.findall(r'\[\s*([\d.]+)\] .*Unhandled context fault:',log)]
assert len(fault_times)==10 and max(fault_times)-min(fault_times)<.01
assert min(fault_times)>30 and max(fault_times)<40
assert '\nK73_EUD_NATIVE_OK\n' in (root/'native-eud.txt').read_text()
assert '\nK73_REBOOT_EUD_OK\n' in (root/'reboot-eud.txt').read_text()
for prefix in ('display','deps','native'):
    assert 'F1' in (root/(prefix+'-f1-wsl.txt')).read_text()
assert '62bc28a1' in (root/'same-image-ready-devices.out').read_text()
assert json.loads((root/'same-image-ready-reboot.json').read_text())['no_flash']

result = dict(captures_verified=len(captures),tests=tests,final_boot_id=facts.splitlines()[1],
    taint=0,partition_hashes_pass=True,native_panel_power_readback=156,
    eud_echo_and_f1_pass=True,preserved_cpu_touch_ufs_usb=True,
    unresolved_boot_handoff_smmu=dict(fault_count=len(fault_times),first_seconds=min(fault_times),
        last_seconds=max(fault_times),no_later_fault_in_captured_tests=True),
    gpu_rendering_verified=False,refresh90_verified=False,optical_output_verified=False,
    brightness_hardware_readback_verified=False,suspend_resume_verified=False)
print(json.dumps(result,indent=2))
