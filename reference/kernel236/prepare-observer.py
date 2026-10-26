"""Keep the automatic-service observer and add real235 power/sensor acceptance."""
from pathlib import Path
import ast
import json

R = Path(__file__).resolve().parent
text = (R.parent / 'kernel233/collect-newboot.py').read_text().replace('k233', 'k236').replace('stage=233', 'stage=236')
text = text.replace('k236-module-stage', 'k235-module-stage')
text = text.replace('boot232_logdump183_persist_nv_exact=True, staged_module_tree787_exact=True',
                    'boot235_logdump183_persist_nv_exact=True, staged_module_tree789_exact=True')
start = text.index("    checked(['sha256sum','-c',str(root/'k235-module-stage/loader-config-after.sha256')]")
end = text.index("    (out / 'summary.json').write_text", start)
extra = r'''
    checked(['sha256sum','-c',str(root/'k235-module-stage/loader-config-after.sha256')],'loader-config')
    tree=Path('/usr/lib/modules')/os.uname().release
    actual_tree={str(n.relative_to(tree)):hashlib.sha256(n.read_bytes()).hexdigest() for n in tree.rglob('*') if n.is_file()}
    assert actual_tree==json.loads((before/'module-inventory-private.json').read_text())
    assert len(actual_tree)==789 and sum(name.endswith('.ko') for name in actual_tree)==775
    lock=json.loads((root/'k236-tools/deployment-lock-private.json').read_text())
    pmic_modules={}
    for name,rel,key in [('qcom_pm8008','kernel/drivers/mfd/qcom-pm8008.ko','mfd_module'),
                         ('qcom_pm8008_imx319_lab','kernel/drivers/regulator/qcom-pm8008-imx319-lab.ko','lab_module'),
                         ('imx319','kernel/drivers/media/i2c/imx319.ko','sensor_module'),
                         ('reset_realme_rmx1931_pm8008','kernel/drivers/reset/reset-realme-rmx1931-pm8008.ko','provider_module')]:
        data=(tree/rel).read_bytes()
        assert hashlib.sha256(data).hexdigest()==lock['files'][key]['sha256']
        assert Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes()==note(data),name
        assert subprocess.check_output(['modinfo','-F','intree',str(tree/rel)],text=True).strip()=='Y'
        pmic_modules[name]=hashlib.sha256(data).hexdigest()
    assert Path('/sys/module/qcom_pm8008/parameters/experimental_p_address_only').read_text().strip()=='N'
    assert Path('/sys/module/qcom_pm8008/parameters/experimental_p_imx319_power').read_text().strip()=='Y'
    qname=json.loads((before/'pmic-q-before-private.json').read_text())['device']
    pname=qname.rsplit('-',1)[0]+'-0008'
    q=Path('/sys/bus/i2c/devices')/qname;p=Path('/sys/bus/i2c/devices')/pname
    provider=Path('/sys/bus/platform/devices/camera-pmic-resets')
    assert provider.joinpath('driver').resolve().name=='rmx1931-pm8008-resets'
    for node in [p,q]:assert node.joinpath('driver').is_symlink() and node.joinpath('driver').resolve().name=='pm8008'
    cells=lambda data:[int.from_bytes(data[i:i+4],'big') for i in range(0,len(data),4)]
    handle=cells(provider.joinpath('of_node/phandle').read_bytes())[0]
    assert cells(p.joinpath('of_node/resets').read_bytes())==[handle,0]
    assert cells(q.joinpath('of_node/resets').read_bytes())==[handle,1]
    assert cells(p.joinpath('of_node/qcom,address-setup-supplier').read_bytes())==cells(q.joinpath('of_node/phandle').read_bytes())
    assert not q.joinpath('of_node/reset-gpios').exists()
    assert Path('/sys/bus/i2c/devices',qname.rsplit('-',1)[0]+'-0009').exists()
    descendants=[n for n in Path('/sys/bus/platform/devices').iterdir() if p.resolve() in n.resolve().parents]
    assert len(descendants)==1 and descendants[0].name.startswith('pm8008-reg-lab14.')
    assert descendants[0].joinpath('driver').resolve().name=='pm8008-imx319-lab'
    rails={}
    for node in Path('/sys/class/regulator').glob('regulator.*'):
        if p.resolve() not in node.resolve().parents:continue
        name=(node/'name').read_text().strip()
        rails[name]={field:(node/field).read_text().strip() for field in ['state','num_users','microvolts']}
    topology=dict(p=pname,q=qname,p_platform_children=[n.name for n in descendants],p_rails=rails)
    sensors={}
    for node in Path('/sys/bus/i2c/devices').iterdir():
        compatible=node/'of_node/compatible'
        if not compatible.exists():continue
        raw=compatible.read_bytes()
        kind='rear' if raw==b'realme,rmx1931-imx319\0' else 'front' if raw==b'sony,imx471\0' else None
        if kind:
            assert kind not in sensors
            sensors[kind]=dict(device=node.name,of_node=str((node/'of_node').resolve()),
                               driver=(node/'driver').resolve().name if (node/'driver').is_symlink() else None,
                               runtime=(node/'power/runtime_status').read_text().strip())
    topology['sensors']=sensors
    (out/'pmic-sensor-topology-private.json').write_text(json.dumps(topology,indent=2)+'\n')
    for name,path in [('gpio','/sys/kernel/debug/gpio'),('regulators','/sys/kernel/debug/regulator/regulator_summary'),
                      ('clocks','/sys/kernel/debug/clk/clk_summary'),('domains','/sys/kernel/debug/pm_genpd/pm_genpd_summary')]:
        (out/(name+'-after-private.txt')).write_text(Path(path).read_text())
    assert set(rails)=={'cam-rear-vana','cam-rear-vdig'}
    assert rails['cam-rear-vana']==dict(state='disabled',num_users='0',microvolts='2800000')
    assert rails['cam-rear-vdig']==dict(state='disabled',num_users='0',microvolts='1104000')
    assert set(sensors)=={'front','rear'}
    assert sensors['rear']['driver']=='imx319' and sensors['rear']['runtime']=='suspended'
    assert '/cci@ac4a000/i2c-bus@1/camera@10' in sensors['rear']['of_node']
    assert sensors['front']['driver']=='imx471' and sensors['front']['runtime']=='suspended'
    assert '/cci@ac4b000/i2c-bus@1/camera@10' in sensors['front']['of_node']
    for cci in ['ac4a000.cci','ac4b000.cci']:
        assert Path('/sys/bus/platform/devices',cci,'power/runtime_status').read_text().strip()=='suspended'
    assert Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip()=='suspended'
    clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text()
    for name in ['cam_cc_mclk1_clk','cam_cc_mclk2_clk']:
        rows=[line.split() for line in clocks.splitlines() if line.split() and line.split()[0]==name]
        assert len(rows)==1 and int(rows[0][1])==0
    assert any(n.name.startswith('pm8008-regulator') for n in q.iterdir())
    # Driver probe returns success only after the real 0x0016 read equals0x0319.
    report.update(new_pmic_sensor_loaded_notes_match=True,pmic_sensor_modules=pmic_modules,
                  p_l1_l4_only_bound_and_off=True,provider_q_p_bound=True,
                  imx319_chip_identity_passed_in_probe=True,rear_sensor_runtime_suspended=True,
                  existing_front_runtime_suspended=True,exact_reset_handles_and_q_dependency_verified=True,
                  no_native_capture_or_power_cycle_yet=True)

'''
text = text[:start] + extra + text[end:]
ast.parse(text)
assert not (R / 'collect-newboot.py').exists()
(R / 'collect-newboot.py').write_text(text)
print(json.dumps(dict(stage=236, newboot_observer_prepared=True, native_sensor_power_id_and_pm_checked=True, no_phone_operation=True)))
