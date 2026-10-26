"""Add native PMIC acceptance to the accepted automatic-service observer."""
from pathlib import Path
import json
R=Path(__file__).resolve().parent
text=(R.parent/'kernel230/collect-newboot.py').read_text().replace('k230','k233').replace('stage=230','stage=233')
text=text.replace("str(before / 'partition-check.sha256')","str(root / 'k233-tools/partition-after.sha256')")
text=text.replace("str(before / 'module-tree.sha256')","str(root / 'k233-module-stage/module-tree-after.sha256')")
text=text.replace('boot219_logdump183_persist_nv_exact=True, module_tree786_exact=True','boot232_logdump183_persist_nv_exact=True, staged_module_tree787_exact=True')
text=text.replace('partitions_flashed=[]','partitions_flashed=[\'boot\']')
anchor="    (out / 'summary.json').write_text"
extra=r'''
    checked(['sha256sum','-c',str(root/'k233-module-stage/loader-config-after.sha256')],'loader-config')
    tree=Path('/usr/lib/modules')/os.uname().release
    pmic_modules={}
    for name,rel in [('qcom_pm8008','kernel/drivers/mfd/qcom-pm8008.ko'),
                     ('reset_realme_rmx1931_pm8008','kernel/drivers/reset/reset-realme-rmx1931-pm8008.ko')]:
        data=(tree/rel).read_bytes()
        assert Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes()==note(data)
        assert subprocess.check_output(['modinfo','-F','intree',str(tree/rel)],text=True).strip()=='Y'
        pmic_modules[name]=hashlib.sha256(data).hexdigest()
    assert Path('/sys/module/qcom_pm8008/parameters/experimental_p_address_only').read_text().strip()=='Y'
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
    assert not Path('/sys/bus/i2c/devices',qname.rsplit('-',1)[0]+'-0009').exists()
    descendants=[n.name for n in Path('/sys/bus/platform/devices').iterdir() if p.resolve() in n.resolve().parents]
    regulators=[n.name for n in Path('/sys/class/regulator').glob('regulator.*') if p.resolve() in n.resolve().parents]
    assert descendants==[] and regulators==[]
    assert any(n.name.startswith('pm8008-regulator') for n in q.iterdir())
    assert any((pname+' ' in l or ' '+pname+':' in l) and 'dependent PMIC identity verified; address-only bring-up, no children' in l for l in log.decode(errors='replace').splitlines())
    (out/'pmic-topology-private.json').write_text(json.dumps(dict(p=pname,q=qname,provider=provider.name,p_platform_children=descendants,p_regulators=regulators),indent=2)+'\n')
    for name,path in [('gpio','/sys/kernel/debug/gpio'),('regulators','/sys/kernel/debug/regulator/regulator_summary')]:
        (out/(name+'-after-private.txt')).write_text(Path(path).read_text())
    report.update(new_pmic_modules_loaded_notes_match=True,pmic_modules=pmic_modules,
                  experimental_option_active=True,provider_q_p_bound=True,p_identity_read_verified=True,
                  p_no_secondary_dummy_or_mfd_or_regulators=True,exact_reset_handles_and_q_dependency_verified=True,
                  q_existing_regulator_child_present=True,native_unbind_and_front_capture_not_yet_tested=True)
'''
assert text.count(anchor)==1;text=text.replace(anchor,extra+'\n'+anchor)
compile(text,'collect-newboot233','exec');(R/'collect-newboot.py').write_text(text)
old=(R.parent/'kernel219/flash-boot.py').read_text()
old=old.replace("build=json.loads((ref/'build-package-validation.json').read_text())","build=json.loads((out/'build-package-validation.json').read_text())")
old=old.replace("image=out/'boot-partition-k219-front-modes.img';rollback=out.parent/'kernel211/boot-partition-k211-sensor-domain.img'", "lock=json.loads((out/'deployment-lock-private.json').read_text());image=Path(lock['files']['boot_candidate']['path']);rollback=Path(lock['files']['boot219_rollback']['path'])")
old=old.replace('stage=219,','stage=233,');compile(old,'flash-boot233','exec');(R/'flash-boot.py').write_text(old)
print(json.dumps(dict(stage=233,newboot_observer_pmic_acceptance_prepared=True,flash_only_locked_boot=True)))
