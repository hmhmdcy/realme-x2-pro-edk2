# Appended to the existing service save/stop/restart helpers.
proof=json.loads((root/'proof.json').read_text());manifest=json.loads((root/'manifest.json').read_text())
items={};started={};stopped=False;backed_up=False;changed=False;verified=False;records=[]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def replace_file(source,target,mode):
 target.parent.mkdir(parents=True,exist_ok=True)
 tmp=target.with_name(target.name+'.k390-tmp');assert not tmp.exists()
 with tmp.open('xb') as f:f.write(source.read_bytes());f.flush();os.fsync(f.fileno())
 tmp.chmod(mode);tmp.replace(target)
 d=os.open(target.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(d)
 finally:os.close(d)
def rollback_files():
 for r in records:
  target=Path(r['target']);present=target.exists();digest=sha(target) if present else None
  assert digest in [None,r.get('old_sha256'),r['new_sha256']],r['name']+' changed outside this transaction'
  if r['existed']:
   original=root/'backup'/r['name'];assert sha(original)==r['old_sha256'];replace_file(original,target,r['old_mode'])
  elif present:target.unlink()
 run(['depmod','-a',manifest['release']],'rollback-depmod')
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(proof['guard']).read_bytes()
 assert Path('/proc/sys/kernel/osrelease').read_text().strip()==manifest['release']
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 for name,digest in manifest['files_sha256'].items():assert sha(root/name)==digest
 assert sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')==proof['camss_note_sha256']
 assert sha('/sys/module/videobuf2_dma_sg/notes/.note.gnu.build-id')==proof['sg_note_sha256']
 modroot=Path(proof['module_root']);assert modroot.resolve()==modroot and modroot.is_dir()
 backup=root/'backup';backup.mkdir(mode=0o700)
 for row in manifest['modules']:
  target=modroot/row['target_relative'];baseline=proof['modules'][row['name']]
  assert str(target.resolve())==baseline['path'] and target.exists()==baseline['exists']
  assert not target.exists() or sha(target)==baseline['sha256']
  records.append(dict(name=row['name']+'.ko',target=str(target),payload='modules/'+row['target_relative'],existed=target.exists(),old_sha256=baseline['sha256'],old_mode=target.stat().st_mode&0o777 if target.exists() else None,new_sha256=row['sha256']))
 firmware=Path(manifest['firmware']['target']).resolve();assert not firmware.exists()
 records.append(dict(name='camera-icp.elf',target=str(firmware),payload='firmware/camera-icp.elf',existed=False,old_sha256=None,old_mode=None,new_sha256=manifest['firmware']['sha256']))
 for r in records:
  if r['existed']:shutil.copy2(r['target'],backup/r['name']);assert sha(backup/r['name'])==r['old_sha256']
 (root/'rollback-files-private.json').write_text(json.dumps(records,indent=2)+'\n');backed_up=True
 items=services();(root/'services-private.json').write_text(json.dumps(items,indent=2)+'\n')
 save('stopping-camera-consumers');stopped=True;stop_services(items);wait_idle()
 assert not any(processes(n) for n in ['pipewire','wireplumber'])
 save('installing-module-files',original_files_saved=True);changed=True
 for r in records:
  replace_file(root/r['payload'],Path(r['target']),0o600 if r['name'].endswith('.elf') else 0o644)
  assert sha(r['target'])==r['new_sha256']
 run(['depmod','-a',manifest['release']],'new-depmod')
 for row in manifest['modules']:
  path=subprocess.check_output(['modinfo','-n',row['name']],text=True).strip()
  assert Path(path).resolve()==(modroot/row['target_relative']).resolve() and sha(path)==row['sha256']
 deps=subprocess.check_output(['modinfo','-F','depends','qcom_camss'],text=True)
 assert 'camss-icp-a5-m2m' in deps and 'qcom-camss-icp-a5-core' in deps
 assert 'qcom,sm8150-camss-icp' in subprocess.check_output(['modinfo','-F','alias','qcom_camss'],text=True)
 assert sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')==proof['camss_note_sha256']
 assert sha('/sys/module/videobuf2_dma_sg/notes/.note.gnu.build-id')==proof['sg_note_sha256']
 assert not any(Path('/sys/module',n).exists() for n in ['qcom_camss_icp_a5_core','camss_icp_a5_m2m','v4l2_mem2mem'])
 os.sync();verified=True
 save('files-installed-pending-reboot',candidate_files_verified=True,old_loaded_code_preserved=True,services_stopped=True)
except BaseException:
 (root/'failure.txt').write_text(traceback.format_exc());state['failure']=traceback.format_exc()
 if changed and backed_up:
  try:rollback_files();state['files_rolled_back']=True
  except BaseException:state['rollback_error']=traceback.format_exc()
 if stopped and (not changed or state.get('files_rolled_back')):
  try:restart(items,'rollback',started);wait_idle();state['services_restored']=True
  except BaseException:state['service_restore_error']=traceback.format_exc()
finally:
 save('finished',terminal=True,passed=verified,candidate_files_installed=verified,old_loaded_code_preserved=verified)
