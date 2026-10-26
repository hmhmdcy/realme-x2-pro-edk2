from pathlib import Path
ref=Path(__file__).resolve().parent;s=(ref.parent/'kernel196/final-health.py').read_text().replace('k196','k197').replace('stage=196','stage=197').replace('k197-front-probe-r6','k197-front-capture-r5').replace(" and front['driver_probe_and_runtime_cycle_complete']",'')
s=s.replace('physical_image_capture_proven=False,normal_imx471_probe_proven=True,runtime_power_cycle_count=1,','physical_image_capture_proven=False,normal_imx471_probe_proven=True,camss_physical_graph_proven=True,csid_reset_timeout_unresolved=True,')
s=s.replace("log=subprocess.check_output(['dmesg']);", "assert (Path('/sys/bus/platform/devices/acb3000.camss')/'driver').resolve()==Path('/sys/bus/platform/drivers/qcom-camss')\nmodule=Path(subprocess.check_output(['modinfo','-n','qcom-camss'],text=True).strip());assert hashlib.sha256(module.read_bytes()).hexdigest()=='e9b73f4c6bad90fbd6ff89ba45894c88b32b51bc9836ddd741ff56876eb13b0d'\nassert not Path('/lib/firmware/samurai/k196-front.dtbo').exists()\nlog=subprocess.check_output(['dmesg']);")
s=s.replace("r=dict(stage=197,", "r=dict(stage=197,original_camss_module_restored=True,original_camss_module_sha256=hashlib.sha256(module.read_bytes()).hexdigest(),")
(ref/'final-health.py').write_text(s)
s=(ref.parent/'kernel196/export-native.py').read_text().replace('k196','k197').replace('stage=196','stage=197');(ref/'export-native.py').write_text(s)
print('Final health and private export scripts prepared')
