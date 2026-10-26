"""Validate preserved observations; decode settings without recommending writes."""
from pathlib import Path
import gzip
import hashlib
import json
import re
import shutil

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel79')
expected = {
    'before': '8902de40fa2c8abb8b91f3dae694f00278c079f8f7fa5838615193890b3f2902',
    'first': '06a4d24bb439709ba6a7859612cec7406cf62757df45413b4fff44e2c0826ab3',
    'mounted': '889bd01c065c204a14be39bb6c208dd6d87b1e4a602b39aa321ac8a7bfab1591',
    'complete': '7afcfdca5fad14ff89c80f326e3a7f66cdc38a5794a7879ab866464a525f0a1f',
}
logs = []
for prefix,digest in expected.items():
    p = out/(prefix+'-dmesg.txt.gz')
    raw = gzip.decompress(p.read_bytes())
    assert hashlib.sha256(raw).hexdigest() == digest
    text = raw.decode()
    faults = re.findall(r'(?mi)^.*(?:\bBUG:|\bOops:|\bKernel panic|\bUnhandled fault|SMMU.*context fault|geni_i2c.*(?:error|timeout)).*$',text)
    assert not faults
    assert 'dsi_err_worker' not in text
    (ref/(prefix+'-dmesg.txt')).write_bytes(raw)
    shutil.copyfile(p,ref/p.name)
    logs.append({'prefix':prefix,'raw_bytes':len(raw),'sha256':digest,
                 'dsi_error_lines':0,'matched_faults':faults,
                 'panel_enable_messages':text.count('DSC 1080x2400@60')})
raws = [(out/p).read_text() for p in ('mp-observation.txt','mp-followup.txt')]
samples = []
for raw in raws:
    for body in re.split(r'SNAPSHOT_\d+\n',raw)[1:]:
        assert 'MP_READER_EXIT=0' in body and 'GAUGE_READER_EXIT=0' in body
        rows = re.findall(r'reg=(0x[0-9a-f]+) value=(0x[0-9a-f]+)',body)
        regs = {int(a,16):int(b,16) for a,b in rows}
        assert len(rows) == len(regs) == 12 and 0x14 not in regs
        samples.append({'uptime_seconds':float(body.split()[0]),'registers':{f'{a:02x}':f'{b:02x}' for a,b in regs.items()}})
assert len(samples) == 3
assert all(s['registers'] == samples[0]['registers'] for s in samples)
r = {int(a,16):int(b,16) for a,b in samples[0]['registers'].items()}
cells = (2,3,4,4)[r[7]>>6]
decoded = {
    'series_cells':cells,'chg_enable':bool(r[8]&0x10),'otg_enable':bool(r[8]&0x20),
    'suspend_enable':bool(r[8]&8),'battfet_enable':bool(r[8]&2),
    'pin_function_is_ntc_otg':bool(r[8]&4),
    'watchdog_seconds':(0,40,80,160)[(r[9]>>4)&3],
    'termination_enabled':bool(r[9]&0x40),'safety_timer_enabled':bool(r[9]&8),
    'safety_timer_hours':(5,8,12,20)[(r[9]>>1)&3],
    'ntc_mode':('JEITA','standard','standard','disabled')[(r[0x0a]>>4)&3],
    'charge_current_setting_ma':(r[2]&0x7f)*50,
    'termination_current_setting_ma':(r[3]&15)*100,
    'input_limit1_nominal_ma_assuming_rs_10mohm':(r[0]&0x7f)*50,
    'input_limit2_nominal_ma_assuming_rs_10mohm':(r[0x0f]&0x7f)*50,
    'input_voltage_limit_mv':r[1]*100,
    'full_voltage_setting_mv_per_cell':3712.5+((r[4]>>1)&63)*12.5,
    'full_voltage_setting_mv_pack':cells*(3712.5+((r[4]>>1)&63)*12.5),
    'status_charge_state':('not_charging','precharge','fast_charge','termination')[(r[0x13]>>2)&3],
    'status_input_power_good':bool(r[0x13]&2),
}
assert decoded['series_cells'] == 2 and decoded['ntc_mode'] == 'disabled'
assert decoded['watchdog_seconds'] == 0 and decoded['safety_timer_enabled']
report = {'successful_snapshots':3,'combined_transactions':36,'charger_register_data_writes':0,
          'fault_register_reads':0,'samples':samples,'decoded_current_settings':decoded,
          'decode_source':'MPS MP2650 Rev1.0 2022-04-22 pp29-44, and stock header cross-check',
          'not_a_charging_acceptance':True,'otp_defaults_not_identified':True,
          'thermistor_wiring_and_input_sense_resistor_not_verified':True,
          'negative_current_sysfs_seen_but_no_calibrated_discharge_test':True,
          'logs':logs}
(out/'observation-validation.json').write_text(json.dumps(report,indent=2)+'\n')
s = (ref.parent/'kernel78/validate-pageflip.py').read_text().replace('kernel78','kernel79')
(ref/'validate-pageflip.py').write_text(s)
exec(compile(s,str(ref/'validate-pageflip.py'),'exec'))
fw = json.loads((out/'firmware-validation.json').read_text())
state = (out/'final-state.txt').read_text(encoding='utf-8-sig')
assert fw['boot_after_sha256'] in state
assert '607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0' in state
assert state.splitlines()[0] == '87753933-4992-45d2-aaf5-d9db9c11d1a3' and state.splitlines()[1] == '0'
print(json.dumps({'decoded_current_settings':decoded,'successful_snapshots':3,'logs':logs},indent=2))
