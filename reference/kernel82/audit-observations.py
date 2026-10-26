"""Validate the fixed observations and source metadata; preserve original bytes."""
from pathlib import Path
import hashlib,json,re,tarfile
OUT=Path('/mnt/e/edk2-samurai-out/kernel82')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected={0x08:0x16,0x09:0x4c,0x0a:0x36,0x07:0x14,0x00:0x12,0x01:0x2d,
          0x02:0x06,0x03:0xa2,0x04:0x68,0x0f:0x12,0x0b:0x00,0x13:0x0f}
observations={}
for phase in ('before','after'):
    allowed={f'tmp/k82-{phase}-{kind}.txt' for kind in ('state','registers','temperatures','dmesg','hashes')}
    with tarfile.open(OUT/(phase+'.tar')) as tar:
        assert {m.name for m in tar}==allowed
        for name in sorted(allowed):
            data=tar.extractfile(name).read();assert len(data)<1500000
            target=OUT/Path(name).name.removeprefix('k82-')
            if target.exists():assert target.read_bytes()==data
            else:target.write_bytes(data)
    for line in (OUT/(phase+'-hashes.txt')).read_text().splitlines():
        digest,remote=line.split('  ',1)
        assert sha(OUT/Path(remote).name.removeprefix('k82-'))==digest
    state=(OUT/(phase+'-state.txt')).read_text()
    assert state.startswith('87753933-4992-45d2-aaf5-d9db9c11d1a3\n')
    assert '7.3.0-rc6-rmx1931-samurai+ #76' in state
    assert re.search(r'^0$',state,re.M)
    assert int(re.search(r'underrun:\s*(\d+)',state)[1])==0
    assert int(re.search(r'frame_done_cnt:(\d+)',state)[1])==2
    registers=(OUT/(phase+'-registers.txt')).read_text()
    actual={int(a,16):int(b,16) for a,b in re.findall(r'reg=0x([0-9a-f]+) value=0x([0-9a-f]+)',registers)}
    assert actual==expected
    temp=(OUT/(phase+'-temperatures.txt')).read_text()
    assert 'MAC_requests=0 register_data_writes=0 retries=0' in temp
    words={name:int(word) for name,word in re.findall(r'^(\w+) selector=.*unsigned_word=(\d+)',temp,re.M)}
    assert set(words)=={'Temperature','InternalTemperature','PackVoltage','InstantCurrent','AverageCurrent'}
    log=(OUT/(phase+'-dmesg.txt')).read_text()
    timeouts=[float(x) for x in re.findall(r'^\[\s*([0-9.]+)\].*enc35 frame done timeout',log,re.M)]
    assert len(timeouts)==2 and timeouts==[1545.683499,1775.069790]
    assert not re.search(r'\bOops:|\bBUG:|Kernel panic|SMMU.*fault|dsi.*(error|fail)|geni.*(error|timeout)',log,re.I)
    observations[phase]={'pack_uV':int(re.search(r'POWER_SUPPLY_VOLTAGE_NOW=(\d+)',state)[1]),
                         'capacity_percent':int(re.search(r'POWER_SUPPLY_CAPACITY=(\d+)',state)[1]),
                         'sysfs_temperature_decidegrees_C':int(re.search(r'POWER_SUPPLY_TEMP=(\d+)',state)[1]),
                         'standard_words':words,'MP2650_registers_hex':{f'{k:02x}':f'{v:02x}' for k,v in actual.items()},
                         'known_frame_done_timeouts':timeouts,'encoder_timeout_count':2,'underrun':0}
before=(OUT/'before-dmesg.txt').read_bytes();after=(OUT/'after-dmesg.txt').read_bytes()
assert after.startswith(before)
for line in (OUT/'usb-budget-hashes.txt').read_text().splitlines():
    digest,remote=line.split('  ',1);assert sha(OUT/Path(remote).name.removeprefix('k82-'))==digest
usb=(OUT/'usb-budget.txt').read_text()
assert 'gadget_MaxPower_mA=100\n' in usb and 'udc_state=configured\n' in usb
assert 'gadget_bmAttributes=0x80\n' in usb
config=json.loads((OUT/'stock-config-observation.json').read_text())
version=json.loads((OUT/'stock-kernel-version.json').read_text())
assert config['sha256']==version['stock_boot_sha256']=='dfe18875661164e7cb64eba7942b856e80ffe20abb537aec815da4bf43995cdd'
assert config['OEM_factory_image_verified'] is False and 'droidspaces' in version['embedded_version']
assert config['selected']['CONFIG_OPLUS_SHORT_IC_CHECK']=='CONFIG_OPLUS_SHORT_IC_CHECK=y'
result={'scope':'Fixed standard gauge and MP2650 reads, plus read-only USB declaration; no charge acceptance.',
        'observations':observations,'new_dmesg_bytes':len(after)-len(before),
        'new_frame_done_timeouts':0,'no_reboot':True,'gauge_MAC_requests':0,
        'gauge_register_data_writes':0,'MP2650_register_data_writes':0,
        'short_IC_registers_read':False,'partition_writes':False,
        'gadget_MaxPower_mA':100,'USB_available_current_verified':False,
        'Android_backup_OEM_factory_provenance_verified':False,
        'Android_backup_kernel_version':version['embedded_version']}
(OUT/'observation-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
