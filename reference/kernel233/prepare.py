"""Prepare a fresh transaction; semantic edits never replace page-size constants."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel233');P.mkdir(mode=0o700)
old=R.parent/'kernel230'
host=(R.parent/'kernel232/host.py').read_text(encoding='utf-8-sig').replace('kernel232','kernel233').replace('Authenticated232','Authenticated233')
(R/'host.py').write_text(host)
(P/'usb-ipv6-candidates-private.json').write_bytes((P.parent/'kernel232/usb-ipv6-candidates-private.json').read_bytes())
lock=json.loads((P.parent/'kernel232/deployment-lock-private.json').read_text())
for info in lock['files'].values():assert hashlib.sha256(Path(info['path']).read_bytes()).hexdigest()==info['sha256']
(P/'deployment-lock-private.json').write_text(json.dumps(lock,indent=2)+'\n')
text=(old/'collect-baseline.py').read_text().replace('k230-baseline','k233-baseline').replace('k228-runtime/boot-id-private.txt','k230-runtime/boot-id-private.txt')
text=text.replace("read_text().strip() == '4096'","read_text().strip() == '0'")
text=text.replace("=={'fastrpc':'O'}","=={}")
text=text.replace("assert loaded==(root/'k228-intree-stage/loaded-note-before-private.bin').read_bytes()\nassert loaded!=note(original)","assert loaded==note(original)")
text=text.replace('stage=230,','stage=233,').replace('same228_boot=True','same230_boot=True').replace('running_external7ca5_note_verified=True','running_intree2abde_note_verified=True').replace('taint=4096','taint=0')
needle="(out / 'summary.json').write_text"
extra=r'''
mfd=module_root/'kernel/drivers/mfd/qcom-pm8008.ko'
assert sha(mfd)=='d1ff82c022577e65b8d5cf8d98e56ea4170eb5bf4138516be843736db25a9dea'
assert not (module_root/'kernel/drivers/reset/reset-realme-rmx1931-pm8008.ko').exists()
assert not Path('/sys/module/reset_realme_rmx1931_pm8008').exists()
loaded_mfd=Path('/sys/module/qcom_pm8008/notes/.note.gnu.build-id').read_bytes()
assert loaded_mfd==note(mfd.read_bytes())
(out/'mfd-original-private.ko').write_bytes(mfd.read_bytes())
(out/'mfd-loaded-note-private.bin').write_bytes(loaded_mfd)
metadata={}
for n in modules:
 if n.endswith('.ko'):continue
 src=module_root/n;dest=out/'module-metadata-before'/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(src.read_bytes())
 st=src.stat();metadata[n]=dict(mode=st.st_mode & 0o777,uid=st.st_uid,gid=st.st_gid)
(out/'module-metadata-meta-private.json').write_text(json.dumps(metadata,indent=2)+'\n')
config=Path('/etc/modprobe.d/samurai-pmic-bringup.conf');assert not config.exists()
configs={}
for directory in ['/etc/modprobe.d','/run/modprobe.d','/usr/lib/modprobe.d','/lib/modprobe.d']:
 for f in Path(directory).glob('*.conf'):
  if f.is_file():
   data=f.read_bytes();configs[str(f)]=hashlib.sha256(data).hexdigest()
   assert not any('qcom_pm8008' in l.replace('-','_') or 'reset_realme_rmx1931_pm8008' in l.replace('-','_') for l in data.decode(errors='replace').splitlines() if not l.lstrip().startswith('#'))
(out/'loader-config-before-private.json').write_text(json.dumps(configs,indent=2)+'\n')
q=[n for n in Path('/sys/bus/i2c/devices').glob('*-0004') if (n/'driver').exists() and (n/'driver').resolve().name=='pm8008'];assert len(q)==1
(out/'pmic-q-before-private.json').write_text(json.dumps(dict(device=q[0].name,children=sorted(n.name for n in q[0].iterdir() if n.name.startswith('pm8008-'))),indent=2)+'\n')
report.update(old_mfd_default_and_loaded_note_match=True,old_mfd_backed_up=True,module_metadata_backed_up=len(metadata),loader_config_target_absent=True,old_q_bound=True)
'''
assert text.count(needle)==1;text=text.replace(needle,extra+'\n'+needle)
assert "'4096'" not in text and "'O'" not in text
(R/'collect-baseline.py').write_text(text)
state=dict(stage=233,state='prepared tools only; phone untouched; candidate232 locked',guard='/var/lib/samurai/k230-runtime/boot-id-private.txt',transition_pending=False,active_native_session=None,active_build_session=None,full_peripheral_goal_active=True,front_known_colour_test_deferred_by_user=True,next='Fresh233 native baseline then atomic two-module+options/softdep staging; no live MFD reload')
(P/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(stage=233,locked_inputs=len(lock['files']),baseline_script_prepared=True,phone_untouched=True)))
