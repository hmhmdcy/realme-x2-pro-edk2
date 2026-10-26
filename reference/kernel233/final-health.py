"""Verify deployed233 manifests and accepted native cycles after front capture."""
from pathlib import Path
import ast,json
import host
R=Path(__file__).resolve().parent
tree=ast.parse((R.parent/'kernel230/final-health.py').read_text())
code=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='code' for v in n.targets)))
code=code.replace("out=root/'k230-final-health'","out=root/'k233-final-health'")
code=code.replace('k230-runtime','k233-runtime').replace('k230-baseline','k233-baseline').replace('stage=230','stage=233')
code=code.replace("root/'k233-baseline/partition-check.sha256'","root/'k233-tools/partition-after.sha256'")
code=code.replace("root/'k233-baseline/module-tree.sha256'","root/'k233-module-stage/module-tree-after.sha256'")
old="check(['sha256sum','-c',str(root/'k228-intree-stage/module-tree-after.sha256')],'prior-accepted-module-tree',Path('/usr/lib/modules')/os.uname().release)"
assert old in code;code=code.replace(old,"check(['sha256sum','-c',str(root/'k233-module-stage/loader-config-after.sha256')],'loader-config')")
code=code.replace('boot219_logdump183_persist_nv_exact=True','boot232_logdump183_persist_nv_exact=True').replace('module_tree786_and_unrelated785_exact=True','module_tree787_and_unrelated771_ko_exact=True')
needle="(out/'summary.json').write_text"
extra=r'''
assert not Path('/sys/kernel/tracing/instances/pmic233').exists()
assert json.loads((root/'k233-pmic-cycles/state-private.json').read_text())['exit_code']==0
cycles=json.loads((root/'k233-pmic-cycles/summary.json').read_text())
assert cycles['q_warm_cycle']['all_seven_q_rail_states_and_voltages_preserved'] and cycles['provider_cold_cycle']['one_cold_address_assignment']
assert Path('/sys/module/qcom_pm8008/parameters/experimental_p_address_only').read_text().strip()=='Y'
qname=json.loads((root/'k233-baseline/pmic-q-before-private.json').read_text())['device'];pname=qname.rsplit('-',1)[0]+'-0008'
q=Path('/sys/bus/i2c/devices')/qname;p=Path('/sys/bus/i2c/devices')/pname
assert all((n/'driver').is_symlink() for n in [p,q,Path('/sys/bus/platform/devices/camera-pmic-resets')])
assert not any(p.resolve() in n.resolve().parents for n in Path('/sys/bus/platform/devices').iterdir())
assert not any(p.resolve() in n.resolve().parents for n in Path('/sys/class/regulator').glob('regulator.*'))
qregs=[{k:(n/k).read_text().strip() for k in ['name','state','num_users']} for n in Path('/sys/class/regulator').glob('regulator.*') if q.resolve() in n.resolve().parents]
assert len(qregs)==7 and all(n['state']=='disabled' and n['num_users']=='0' for n in qregs)
for rel in ['2304x1728-raw-pattern0-system','2296x1728-rgb-pattern0-system']:
 capture=json.loads((root/('k233-front-regression-'+rel)/'summary.json').read_text())
 assert capture['program_exit']==0 and len(capture['frames'])==6 and all(not f['all_zero'] for f in capture['frames'])
 assert all(capture[k] for k in ['all_formats_restored','media_graph_restored','sensor_controls_restored','camera_devices_suspended','no_scene_images_saved'])
 assert capture['taint']==0 and not any(capture['fault_delta'].values())
report.update(p_q_provider_bound=True,p_no_mfd_or_regulator_children=True,q_all_seven_rails_disabled_zero_users=True,
 warm_and_cold_native_cycles_passed=True,reset_gpio_trace_stopped_and_instance_removed=True,
 front_raw_and_rgb_six_frames_each_passed=True,front_known_colour_test_deferred=True,no_scene_images_saved=True)
'''
assert code.count(needle)==1;code=code.replace(needle,extra+'\n'+needle)
r=host.ssh('python3 -',input=code.encode(),timeout=110);(host.PRIVATE/'final-health-host-private.log').write_bytes(r.stdout+r.stderr)
report=json.loads(r.stdout);(R/'final-health-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
