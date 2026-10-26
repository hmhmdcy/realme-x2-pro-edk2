from pathlib import Path
import json,re,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k199-baseline/boot-id-private.txt').read_bytes();out=root/'k199-front-capture-r1';r=json.loads((out/'summary.json').read_text());print(json.dumps({k:r.get(k) for k in ['attempts','normal_driver_bound','physical_media_graph_present','capture_cycles','idle_performance_dropped','physical_image_capture','camss_original_module_restored','camss_original_graph_restored','fault_delta','taint']}));print('temporary_modules',[n for n in ['samurai_camera_perf','samurai_front_overlay','imx471','qcom_pm8008','samurai_vio_phandle','i2c_qcom_cci'] if Path('/sys/module/'+n).exists()]);print('camss_bound',Path('/sys/bus/platform/devices/acb3000.camss/driver').exists())
for name in ['first-capture-private.log','second-capture-private.log']:
 p=out/name
 if p.exists():print(name,re.sub(r'hash=[0-9a-f]+','hash=<private>',p.read_text())[-2500:])
before=(out/'dmesg-before-private.txt').read_bytes();after=subprocess.check_output(['dmesg']);(out/'dmesg-current-private.txt').write_bytes(after);print(after[len(before):].decode(errors='replace')[-9000:]);pd=Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_text();rows=pd.splitlines()
for i,l in enumerate(rows):
 if re.match(r'^mmcx\s',l):print('\n'.join(rows[i:i+9]))
