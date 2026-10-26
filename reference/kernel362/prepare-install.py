"""Prepare an offline transaction for the tested framework/driver/private profiles."""
from pathlib import Path
import io,json,shutil,tarfile,textwrap
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=storage.SDK
assert json.loads((HERE/'package-artifact-validation.json').read_text())['passed']
assert json.loads((HERE/'runtime-validation.json').read_text())['full_candidate_validation_passed']
proof=json.loads((P.parent/'kernel348/proof.json').read_text());adopted=json.loads((P.parent/'kernel360/recovered-boot-adoption-private.json').read_text())
new={r['name']:r['version'] for r in json.loads((P/'runtime-records.json').read_text())}
proof=dict(stage=362,packages=new,old_packages={k:('99990.7.2-r27' if k.startswith('libcamera') else '0.1.0-r22') for k in new},
    boot_guard=adopted['guard_path'],module_note_sha256='0227d29bb5129e2fc69866529147b21b902d441c855f848fd5eaa3093c590297',
    candidate_note_sha256=proof['module_note_sha256'])
(P/'install-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
cases=json.loads((P/'cases-private.json').read_text());default={k:cases[k] for k in ['s5kgw1-2-preview','s5kgw1-4-preview','imx471-1-preview','imx319-2-preview','s5k3m5-3-preview']}
(P/'default-cases.json').write_text(json.dumps(default,indent=2)+'\n')
profiles=P/'install-profiles';profiles.mkdir(exist_ok=True)
for item in default.values():shutil.copyfile(P.parent/'kernel360/profiles'/item['profile'],profiles/(item['model']+'.yaml'))
s=(HERE.parent/'kernel342/native-install.py').read_text().replace("'stage':342","'stage':362").replace('stage=342','stage=362').replace('0.1.0-r22','0.1.0-r24')
s=s.replace("Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt')","Path(proof['boot_guard'])")
s=s.replace('user_probe=None','user_probe=None;module_changed=False;profiles_changed=False;default_results={}')
needle=" consumers=services();wait_idle()"
extra=''' consumers=services();wait_idle()
 target=Path(subprocess.check_output(['modinfo','-n','qcom_camss'],text=True).strip())
 if target.suffix!='.ko':raise RuntimeError('Expected existing uncompressed module')
 if subprocess.check_output(['modinfo','-F','vermagic',str(target)])!=subprocess.check_output(['modinfo','-F','vermagic',str(root/'qcom-camss.ko')]):raise RuntimeError('Module ABI mismatch')
 profile_names=['etc/libcamera/ipa/camss-vfe/'+m+'.yaml' for m in ['s5kgw1','imx471','imx319','s5k3m5']]
 if not all((Path('/')/name).is_file() for name in profile_names):raise RuntimeError('Expected344 defaults')'''
assert s.count(needle)==1;s=s.replace(needle,extra)
s=s.replace("for name in ['etc/apk/world','etc/apk/repositories.d/60-samurai-camera.list']:","for name in ['etc/apk/world','etc/apk/repositories.d/60-samurai-camera.list',str(target.relative_to('/')),*profile_names]:",1)
needle=" if sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')!=proof['module_note_sha256']:raise RuntimeError('Loaded module differs')"
replacement=''' module_changed=True
 run(['rmmod','qcom_camss'],'unload-old-module')
 temp=target.with_name(target.name+'.k362-tmp');shutil.copyfile(root/'qcom-camss.ko',temp);temp.chmod(0o644);os.replace(temp,target)
 run(['modprobe','qcom_camss'],'load-tested-module')
 if sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')!=proof['candidate_note_sha256']:raise RuntimeError('Loaded candidate differs')
 profiles_changed=True
 for name in profile_names:
  dest=Path('/')/name;temp=dest.with_name(dest.name+'.k362-tmp');shutil.copyfile(root/'profiles'/dest.name,temp);temp.chmod(0o644);os.replace(temp,dest)
'''+textwrap.indent((HERE/'install-default-check.py').read_text(),' ')
assert s.count(needle)==1;s=s.replace(needle,replacement)
needle="   if packages_sent:\n"
replacement='''   if profiles_changed:
    for name in profile_names:
     dest=Path('/')/name;temp=dest.with_name(dest.name+'.k362-tmp');shutil.copyfile(root/'backup'/name,temp);os.replace(temp,dest)
   if module_changed:
    if Path('/sys/module/qcom_camss').exists():run(['rmmod','qcom_camss'],'rollback-unload')
    temp=target.with_name(target.name+'.k362-tmp');shutil.copyfile(root/'backup'/str(target.relative_to('/')),temp);os.replace(temp,target)
    run(['modprobe','qcom_camss'],'rollback-module')
   if packages_sent:
'''
assert s.count(needle)==1;s=s.replace(needle,replacement)
s=s.replace('module_unchanged=True,kernel_image_unchanged=True','module_unchanged=False,module_stage=348,private_defaults_updated=verified,default_checks=default_results,kernel_image_unchanged=True')
(HERE/'native-install.py').write_text(s);compile(s,str(HERE/'native-install.py'),'exec')
for name in ['launch-install.py','inspect-install.py']:
    s=(HERE.parent/'kernel342'/name).read_text().replace('k342-install-','k362-install-').replace('stage=342','stage=362')
    if name=='inspect-install.py':s=s.replace("proof['module_note_sha256']","proof['candidate_note_sha256']")
    (HERE/name).write_text(s)
build=json.loads((HERE.parent/'kernel348/kernel-build-validation.json').read_text())
files={'worker.py':HERE/'native-install.py','proof.json':P/'install-proof.json','default-cases.json':P/'default-cases.json','profiles':profiles,
 'qcom-camss.ko':Path(build['module']),'pipeline-fixture':P.parent/'kernel313/pipeline-fixture',
 'bin/adaptation-smoke':storage.candidate().parent/'camss362-runtime/adaptation-smoke',
 'bin/gst-hardware-probe':SDK/'private/camss316-runtime/gst-hardware-probe','bin/pw-hardware-probe':SDK/'private/camss316-runtime/pw-hardware-probe'}
with tarfile.open(P/'install.tar.gz.tmp','w:gz') as tar:
    for name,path in files.items():tar.add(path,arcname=name)
    for path in (P/'runtime-repository').rglob('*'):tar.add(path,arcname='repository/'+path.relative_to(P/'runtime-repository').as_posix(),recursive=False)
(P/'install.tar.gz.tmp').replace(P/'install.tar.gz')
print('Prepared r29/r24 +348 + four default Preview profiles; offline r27/r22 rollback, old module/profile backups before mutation.')
