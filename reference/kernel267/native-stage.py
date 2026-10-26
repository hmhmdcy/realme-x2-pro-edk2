"""Stage common drivers for the matched DTB; retain old loaded modules until reboot."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import struct
import subprocess
import traceback

os.umask(0o077)
r=Path('/var/lib/samurai');o=r/'k267-module-transaction';o.mkdir(mode=0o700)
source=r/'k267-input';manifest=json.loads((source/'manifest.json').read_text())
state=dict(stage=267,state='preflight',terminal=False,pid=os.getpid())
def save():
    p=o/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(o/'state-private.json')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(tree):
    return {str(p.relative_to(tree)):sha(p) for p in tree.rglob('*') if p.is_file() and not p.is_symlink()}
def note(p):
    data=p.read_bytes();offset=struct.unpack_from('<Q',data,40)[0];size,count,index=struct.unpack_from('<HHH',data,58)
    sections=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*size) for i in range(count)]
    strings=data[sections[index][4]:sections[index][4]+sections[index][5]]
    items=[data[s[4]:s[4]+s[5]] for s in sections if strings[s[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id']
    assert len(items)==1;return items[0]
save();saved={};changed=False
try:
    assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k260-work/boot-id-private.txt').read_bytes()
    assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
    release=os.uname().release;tree=Path('/usr/lib/modules')/release
    before=inventory(tree);(o/'module-inventory-before-private.json').write_text(json.dumps(before,indent=2)+'\n')
    package_db=sha(Path('/lib/apk/db/installed'))
    for row in manifest['modules']:
        dest=tree/row['relative_path'];assert sha(dest)==row['before_sha256']
        assert note(dest)==Path('/sys/module',row['name'],'notes/.note.gnu.build-id').read_bytes()
        assert sha(source/row['file'])==row['sha256']
        assert subprocess.check_output(['modinfo','-F','intree',str(source/row['file'])],text=True).strip()=='Y'
        assert subprocess.check_output(['modinfo','-F','vermagic',str(source/row['file'])],text=True).strip()==row['vermagic']
    for row in manifest['remove_modules']:
        assert sha(tree/row['relative_path'])==row['before_sha256']
    config=Path('/etc/modprobe.d/samurai-pmic-bringup.conf')
    assert config.read_text()=='options qcom_pm8008 experimental_p_imx319_power=1\nsoftdep qcom_pm8008 pre: reset_realme_rmx1931_pm8008\n'
    targets={tree/row['relative_path'] for row in manifest['modules']+manifest['remove_modules']}
    targets|={p for p in tree.glob('modules.*') if p.is_file()};targets.add(config)
    backup=o/'before';backup.mkdir(mode=0o700)
    for p in targets:
        name=str(p).lstrip('/');dest=backup/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,dest);saved[str(p)]=dict(sha256=sha(p),mode=p.stat().st_mode&0o777)
    (o/'before-files-private.json').write_text(json.dumps(saved,indent=2)+'\n')
    (o/'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
    state.update(state='writing_backed_up_driver_files');save();changed=True
    for row in manifest['modules']:
        dest=tree/row['relative_path'];temp=dest.with_name(dest.name+'.k267-next')
        assert not temp.exists();temp.write_bytes((source/row['file']).read_bytes());temp.chmod(0o644);temp.replace(dest)
    for row in manifest['remove_modules']:(tree/row['relative_path']).unlink()
    config.unlink()
    q=subprocess.run(['depmod','-a',release],capture_output=True,timeout=40)
    (o/'depmod-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
    assert not q.stderr,q.stderr
    after=inventory(tree);(o/'module-inventory-after-private.json').write_text(json.dumps(after,indent=2)+'\n')
    replaced={row['relative_path'] for row in manifest['modules']}
    removed={row['relative_path'] for row in manifest['remove_modules']}
    assert set(before)-set(after)==removed
    for name,digest in before.items():
        if name not in replaced|removed and not name.startswith('modules.'):assert after[name]==digest
    assert not any('experimental_p_' in line or 'reset_realme_rmx1931_pm8008' in line
                   for line in subprocess.check_output(['modprobe','-c'],text=True).splitlines())
    for row in manifest['modules']:
        assert sha(tree/row['relative_path'])==row['sha256']
        # No hot replacement: memory still contains the exact original module.
        assert Path('/sys/module',row['name'],'notes/.note.gnu.build-id').read_bytes()==note(backup/str(tree/row['relative_path']).lstrip('/'))
    assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
    assert sha(Path('/lib/apk/db/installed'))==package_db
    summary=dict(stage=267,three_common_modules_staged=True,two_experimental_module_files_removed=True,
                 old_lab_loader_configuration_removed=True,other_modules_preserved=True,
                 all_loaded_modules_still_original=True,no_hot_unload_or_pmic_reset=True,
                 before_ko=sum(n.endswith('.ko') for n in before),after_ko=sum(n.endswith('.ko') for n in after),
                 taint=0,package_database_unchanged=True,matched_new_boot_required=True)
    (o/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    os.sync();state.update(state='terminal',terminal=True,exit_code=0);save()
except BaseException:
    error=traceback.format_exc();(o/'failure-private.txt').write_text(error)
    if changed:
        for name,row in saved.items():
            p=Path(name);p.write_bytes((o/'before'/name.lstrip('/')).read_bytes());p.chmod(row['mode'])
        for p in tree.glob('modules.*'):
            if p.is_file() and str(p) not in saved:p.unlink()
        for row in manifest['modules']:
            p=(tree/row['relative_path']).with_name(row['file']+'.k267-next')
            if p.exists():p.unlink()
        assert all(sha(Path(n))==row['sha256'] for n,row in saved.items())
        state['disk_rollback_passed']=True
    os.sync();state.update(state='failed',terminal=True,exit_code=1);save()
    raise SystemExit(1)
