from pathlib import Path
ref=Path(__file__).resolve().parent;previous=ref.parent/'kernel195'
s=(previous/'final-health.py').read_text().replace('k195-','k196-').replace('stage=195','stage=196').replace("names=['samurai_vio_phandle'","names=['samurai_front_overlay','samurai_vio_phandle'")
a=s.index("vio=json.loads(");b=s.index("assert Path('/sys/firmware",a)
s=s[:a]+"front=json.loads((root/'k196-front-probe-r6/summary.json').read_text());assert front['normal_driver_bound'] and front['physical_id_accepted_by_normal_driver'] and front['driver_probe_and_runtime_cycle_complete'] and front['pins_restored_exact'] and front['pmic_after_restore']==front['before']['pmic']\nassert not Path('/sys/firmware/devicetree/base/samurai-front-restore').exists() and not Path('/sys/firmware/devicetree/base/soc@0/camss@acb3000/ports/port@2').exists()\n"+s[b:]
s=s.replace("physical_image_capture_proven=False,", "physical_image_capture_proven=False,normal_imx471_probe_proven=True,runtime_power_cycle_count=1,")
(ref/'final-health.py').write_text(s);(ref/'export-native.py').write_text((previous/'export-native.py').read_text().replace('k195-','k196-').replace('stage=195','stage=196'))
print('Final health and all-attempt native evidence export prepared')
