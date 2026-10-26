"""Quiesce static camera drivers only after desktop camera clients exit."""
from pathlib import Path
import json,os,re,subprocess
root=Path('/var/lib/samurai');out=root/'k236-quiesce';assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k236-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert {p.parent.name:p.read_text().strip() for p in Path('/sys/module').glob('*/taint') if p.read_text().strip()}=={}
for process in Path('/proc').iterdir():
    if not process.name.isdigit():continue
    try:
        for fd in (process/'fd').iterdir():
            try:assert not os.readlink(fd).startswith(('/dev/video','/dev/media','/dev/v4l-subdev'))
            except OSError:pass
    except OSError:pass
for p in ['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci']:
    assert Path(p,'power/runtime_status').read_text().strip()=='suspended'
for p in Path('/sys/class/regulator').glob('regulator.*'):
    if (p/'name').read_text().strip() in ['cam-front-vdig','cam-front-vana']:
        assert (p/'state').read_text().strip()=='disabled' and (p/'num_users').read_text().strip()=='0'
clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text();mclk=next(l.split() for l in clocks.splitlines() if re.search(r'\bcam_cc_mclk2_clk\s',l));assert int(mclk[1])==0
pd=Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_text();assert re.search(r'genpd:3:acb3000.camss\s+suspended\s+0\s',pd)
before=subprocess.check_output(['dmesg']);report=dict(stage=236,all_camera_clients_closed=True,all_camera_devices_and_resources_idle=True,unload_results=[])
for i,name in enumerate(['qcom_camss','imx471','v4l2_cci','i2c_qcom_cci']):
    assert Path('/sys/module'/Path(name)).exists()
    if name=='imx471':
        Path('/sys/bus/i2c/drivers/imx471/unbind').write_text('7-0010')
        assert not Path('/sys/bus/i2c/devices/7-0010/driver').is_symlink()
    p=subprocess.run(['rmmod',name],capture_output=True,timeout=15);(out/('camera-unload-'+str(i)+'-private.log')).write_bytes(p.stdout+p.stderr)
    report['unload_results'].append(dict(module=name,exit=p.returncode));(out/'camera-quiesce-validation.json').write_text(json.dumps(report,indent=2)+'\n');assert p.returncode==0
assert not Path('/dev/media0').exists()
after=subprocess.check_output(['dmesg']);(out/'camera-unload-dmesg-private.txt').write_bytes(after)
faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(faults.values())
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/sys/module/qcom_pm8008').exists() and Path('/sys/module/qcom_pm8008_regulator').exists()
assert Path('/sys/module/qcom_pm8008/notes/.note.gnu.build-id').read_bytes()==(root/'k236-baseline/mfd-loaded-note-private.bin').read_bytes()
q=json.loads((root/'k236-baseline/pmic-q-before-private.json').read_text())['device']
assert Path('/sys/bus/i2c/devices',q,'driver').resolve().name=='pm8008'
assert Path('/sys/module/reset_realme_rmx1931_pm8008').exists()
assert Path('/sys/bus/i2c/devices/1-0008/driver').resolve().name=='pm8008'
assert not Path('/sys/bus/i2c/devices/1-0009').exists()
report.update(p_q_provider_retained=True,all_four_endpoint_modules_unloaded=True,old_q_mfd_and_regulator_retained=True,taint=0,fault_delta=faults)
(out/'camera-quiesce-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('K211_STATIC_CAMERA_CLIENTS_CLOSED_AND_DRIVERS_QUIESCED')
