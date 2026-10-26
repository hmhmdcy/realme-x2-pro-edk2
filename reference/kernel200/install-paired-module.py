from pathlib import Path
import hashlib, json, os, subprocess

os.umask(0o077)
root=Path('/var/lib/samurai')
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==(root/'k200-baseline/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
proof=json.loads((root/'k200-preliminary/summary-private.json').read_text())
assert proof['preliminary_quiesce_pass'] and proof['boot_id']==boot.decode().strip()
assert not Path('/sys/module/qcom_camss').exists()
out=root/'k200-deploy';assert not out.exists();out.mkdir(mode=0o700)
module=Path(subprocess.check_output(['modinfo','-n','qcom-camss'],text=True).strip())
old=module.read_bytes();candidate=root/'k200-reboot-tools/qcom-camss-mmcx.ko';new=candidate.read_bytes()
digest=lambda b:hashlib.sha256(b).hexdigest()
assert digest(old)=='e9b73f4c6bad90fbd6ff89ba45894c88b32b51bc9836ddd741ff56876eb13b0d'
assert digest(new)=='82cbc0528a76858ac57e149bdb540d14630112d74213384303960eead684fe58'
for field in ['depends','vermagic','intree']:
    assert subprocess.check_output(['modinfo','-F',field,str(module)])==subprocess.check_output(['modinfo','-F',field,str(candidate)]),field
(out/'qcom-camss-original-private.ko').write_bytes(old)
lines=(root/'k200-baseline/old132-module-tree.sha256').read_text().splitlines();target='kernel/drivers/media/platform/qcom/camss/qcom-camss.ko';found=0;newlines=[]
for line in lines:
    value,name=line.split(maxsplit=1);name=name.lstrip('*')
    if name==target:
        assert value==digest(old);value=digest(new);found+=1
    newlines.append(value+'  '+name)
assert found==1
temporary=module.with_name(module.name+'.k200-new')
assert not temporary.exists();temporary.write_bytes(new);os.chmod(temporary,module.stat().st_mode & 0o777);os.replace(temporary,module)
assert digest(module.read_bytes())==digest(new)
(out/'paired-module-tree.sha256').write_text('\n'.join(newlines)+'\n')
subprocess.run(['sha256sum','-c',str(out/'paired-module-tree.sha256')],cwd=Path('/usr/lib/modules')/os.uname().release,check=True,stdout=(out/'module-tree-check-private.txt').open('wb'))
r=dict(stage=200,module_replaced_for_paired_static_dt_boot=True,old_sha256=digest(old),candidate_sha256=digest(new),backup_verified=True,module_not_loaded_with_old_three_domain_dt=True,module_tree_files=784,full_remoteproc_shutdown_pending=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');os.sync();print(json.dumps(r))
