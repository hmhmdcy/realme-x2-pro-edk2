proof=json.loads((root/'proof.json').read_text());dev=Path('/sys/bus/platform/devices/ac10000.icp')
consumers={};new_services={};stopped=False;packages_sent=False;driver_changed=False;verified=False;rollback=False;failure=None;client=None;collector=None;collector_log=None;user_probe=None
before=subprocess.check_output(['dmesg']);kernel_anchor=before.decode(errors='replace').splitlines()[-1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def versions():
 result={}
 for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
  f=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
  if f.get('P') in proof['packages']:result[f['P']]=f['V']
 return result
def m2m():return json.loads((dev/'m2m_status').read_text())
def core():return json.loads((dev/'state').read_text())
def released(s):return not any(s[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes'])
def idle():
 wait_idle();deadline=time.monotonic()+5
 while not released(core()) or m2m()['users'] or m2m()['running']:
  assert time.monotonic()<deadline,'IPE still owns active work';time.sleep(.02)
def owner_zero():
 deadline=time.monotonic()+5
 while m2m()['owner_refs']:
  assert time.monotonic()<deadline,'CAMSS still has an external camera consumer';time.sleep(.02)
def defaults_unchanged():return {n:sha('/etc/libcamera/ipa/camss-vfe/'+n) for n in proof['private_defaults']}==proof['private_defaults']
"""Runtime helpers appended to the proven package installation worker."""
def driver_notes(kind):
 for item in proof['driver_pair']:
  assert sha('/sys/module/'+item['module']+'/notes/.note.gnu.build-id')==item[kind+'_note_sha256']
  if kind=='new':assert sha(item['target'])==item['new_sha256']
 assert sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')==proof['camss_note_sha256']
 assert not Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack').exists()
 for n in ['test_cc_mode','test_gamma_mode','test_ltm_mode','test_chain_mode']:
  assert not Path('/sys/module/camss_icp_a5_m2m/parameters',n).exists()

def unload_pair():
 if (dev/'m2m_status').exists():idle();owner_zero()
 for name in ['qcom_camss','camss_icp_a5_m2m','qcom_camss_icp_a5_core']:
  if Path('/sys/module',name).exists():run(['rmmod',name],'unload-'+name,timeout=20)
 assert not (dev/'driver').exists() and not (dev/'m2m_status').exists()

def replace_pair(kind):
 for i,item in enumerate(proof['driver_pair']):
  source=root/item['payload'] if kind=='new' else root/'backup'/('module-'+str(i)+'.ko')
  assert sha(source)==item[kind+'_sha256']
  target=Path(item['target']);temporary=target.with_name(target.name+'.k420-tmp')
  assert not temporary.exists()
  with temporary.open('xb') as f:f.write(source.read_bytes());f.flush();os.fsync(f.fileno())
  temporary.chmod(0o644);os.replace(temporary,target)
  fd=os.open(target.parent,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(fd)
  finally:os.close(fd)
 run(['depmod','-a',os.uname().release],'depmod-'+kind,timeout=30)

def load_pair(kind):
 run(['modprobe','qcom_camss'],'load-pair-'+kind,timeout=30)
 assert (dev/'driver').resolve().name=='qcom-sm8150-icp'
 driver_notes(kind);idle();owner_zero()


try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(proof['boot_guard']).read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512' and versions()==proof['old_packages']
 assert sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')==proof['camss_note_sha256'] and (dev/'driver').resolve().name=='qcom-sm8150-icp'
 assert defaults_unchanged() and released(core())
 driver_notes('old')
 assert all(sha(i['target'])==i['old_sha256'] for i in proof['driver_pair'])
 consumers=services();backup=root/'backup';backup.mkdir(mode=0o700)
 for name in ['etc/apk/world','etc/apk/repositories.d/60-samurai-camera.list']:
  p=backup/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(Path('/')/name,p)
 for i,item in enumerate(proof['driver_pair']):shutil.copyfile(item['target'],backup/('module-'+str(i)+'.ko'))
 (root/'services-private.json').write_text(json.dumps(consumers,indent=2)+'\n')
 for kind in ['forward','rollback']:(root/(kind+'.list')).write_text('ndx file://'+str(root/'repository'/kind/'packages.adb')+'\n')
 run(['apk','--no-network','--repositories-file',str(root/'forward.list'),'add','--simulate','samurai-camera-stack=0.1.0-r26'],'simulate',timeout=40)
 save('stopping-camera-consumers');stopped=True;stop_services(consumers);idle();owner_zero();state['ipe_before']=m2m()
 save('installing-production419-pair');driver_changed=True;unload_pair();replace_pair('new');load_pair('new');state['ipe_before']=m2m()
 save('installing-r31-r26');packages_sent=True
 run(['apk','--no-network','--repositories-file',str(root/'forward.list'),'add','samurai-camera-stack=0.1.0-r26'],'packages',timeout=90)
 assert versions()==proof['packages'] and defaults_unchanged()
 for name,digest in proof['installed_files'].items():assert sha('/'+name)==digest,name
 assert sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')==proof['camss_note_sha256']
 collector_log=(root/'collector.log').open('xb');collector=subprocess.Popen([sys.executable,str(root/'dump-collector.py'),str(root)],stdin=subprocess.DEVNULL,stdout=collector_log,stderr=subprocess.STDOUT,start_new_session=True)
 save('arming-collector',collector_pid=collector.pid);deadline=time.monotonic()+3
 while not (root/'collector-ready.json').exists():assert collector.poll() is None and time.monotonic()<deadline;time.sleep(.01)
 q=run(['cam','-l'],'enumeration');assert (q.stdout+q.stderr).decode(errors='replace').count('for pipeline handler camss-vfe')==4
 if 'reuse_suite' in proof:
  previous=proof['reuse_suite'];assert sha(previous['path'])==previous['sha256']
  shutil.copyfile(previous['path'],root/'suite.json');state['camera_suite_reused_from']=previous['path']
 else:
  with (root/'suite.json').open('xb') as output,(root/'suite.log').open('xb') as errors:
   client=subprocess.Popen([sys.executable,str(root/'camera-client.py'),str(root)],stdin=subprocess.DEVNULL,stdout=output,stderr=errors,start_new_session=True)
   save('installed-camera-suite-running',client_pid=client.pid);code=client.wait(timeout=400)
  assert code==0
 suite=json.loads((root/'suite.json').read_text());assert suite['passed'] and len(suite['captures'])==7
 idle();owner_zero();state['camera_suite']=suite;state['ipe_after_suite']=m2m()
 assert state['ipe_after_suite']['completed']-state['ipe_before']['completed']==(0 if 'reuse_suite' in proof else sum(r['ipe_completed'] for r in suite['captures'].values()))
 save('restarting-desktop-consumers');restart(consumers,'new',new_services);wait_idle()
 item=new_services['pipewire'];env=item['env'].copy();user_probe=Path(env['XDG_RUNTIME_DIR'])/(root.name+'-pw-probe')
 with user_probe.open('xb') as f:f.write((root/'pw-hardware-probe').read_bytes())
 user_probe.chmod(0o755);u=pwd.getpwuid(item['uid']);os.chown(user_probe,u.pw_uid,u.pw_gid)
 nodes=[];deadline=time.monotonic()+10
 while time.monotonic()<deadline:
  q=run([str(user_probe),'--list'],'pw-enumeration',env=env,preexec_fn=demote(item));nodes=re.findall(rb'PW_NODE id=(\d+) name=(\S+) serial=(\S+) path=(\S+)',q.stdout)
  if len(nodes)==4:break
  time.sleep(.2)
 assert len(nodes)==4
 maps=Path('/proc',str(new_services['wireplumber']['pid']),'maps').read_text();(root/'wireplumber-maps-private.txt').write_text(maps)
 assert any('/usr/lib/libcamera.so.0.7.2' in line and '(deleted)' not in line for line in maps.splitlines()),'WirePlumber camera SPA did not load the installed core'
 model='imx319';device=next(p for p in Path('/sys/bus/i2c/drivers',model).iterdir() if (p/'of_node').exists());camera_id='/base'+str((device/'of_node').resolve()).split('/base',1)[1]
 node_name='libcamera_input.'+re.sub(r'[^A-Za-z0-9_.-]','_',camera_id);selected=next(n for n in nodes if n[3].decode()==camera_id or n[1].decode()==node_name)
 prior=m2m();q=run([str(user_probe),selected[2].decode()],'installed-pipewire',env=env,preexec_fn=demote(item),timeout=35);idle();after=m2m()
 match=re.search(rb'PW_RESULT frames=(\d+) format-accepted=(\d+) errors=(\d+) result=(\d+)',q.stdout)
 assert match and int(match[1])>0 and int(match[2]) and int(match[3])==int(match[4])==0
 assert after['completed']-prior['completed']>=int(match[1]) and not after['failed'] and after['direct_completed']==after['completed']
 state['pipewire']=dict(nodes=4,frames=int(match[1]),ipe_completed=after['completed']-prior['completed'],ipe_cancelled=after['cancelled']-prior['cancelled'],installed_core_mapping_verified=True,core_mapping_process='wireplumber',passed=True)
 assert released(core()) and defaults_unchanged() and versions()==proof['packages'] and collector.poll() is None
 Path('/etc/apk/repositories.d/60-samurai-camera.list').write_text('ndx file://'+str(root/'repository/forward/packages.adb')+'\n')
 driver_notes('new')
 state['ipe_after']=after;state['core_after']=core();verified=True
 save('installed-default-paths-verified')
except BaseException:
 failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
 try:
  child_live=client is not None and client.poll() is None;state['client_live']=child_live
  assert not child_live,'Camera suite still live: retain package state and inspect its owned child'
  if (dev/'m2m_status').exists():idle()
  if not verified and stopped:
   save('rollback')
   if new_services:stop_services(new_services)
   if (dev/'m2m_status').exists():idle();owner_zero()
   if driver_changed:unload_pair();replace_pair('old');load_pair('old')
   if packages_sent:run(['apk','--no-network','--repositories-file',str(root/'rollback.list'),'add',*[n+'='+v for n,v in proof['old_packages'].items()]],'rollback-packages',timeout=90)
   for n in ['etc/apk/world','etc/apk/repositories.d/60-samurai-camera.list']:shutil.copyfile(root/'backup'/n,Path('/')/n)
   assert versions()==proof['old_packages'] and defaults_unchanged();new_services={};restart(consumers,'rollback',new_services);wait_idle();rollback=True
  if collector is not None:
   (root/'collector-stop').touch();state['collector_exit']=collector.wait(timeout=5);state['collector_result']=json.loads((root/'collector-result.json').read_text())
   assert not state['collector_result'].get('error') and not state['collector_result']['timeout'] and (not state['collector_result']['captured'] or state['collector_result']['acknowledged'])
 except BaseException:state['cleanup_failure']=traceback.format_exc();verified=False
 if user_probe and user_probe.exists():user_probe.unlink()
 if collector_log:collector_log.close()
 logs=subprocess.check_output(['dmesg']).decode(errors='replace');lines=logs.splitlines()
 assert lines.count(kernel_anchor)==1,'Kernel log anchor unavailable: retain evidence and inspect'
 new=lines[lines.index(kernel_anchor)+1:]
 (root/'kernel-log-private.txt').write_text('\n'.join(new)+'\n');pattern=r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|crash detected in modem|CCI error|Stream stop failed:|A5 IPE frame failed|IPE m2m job failed'
 faults=[l for l in new if re.search(pattern,l)];taint=int(Path('/proc/sys/kernel/tainted').read_text())
 state.update(driver_pair_installed=verified,installed=verified,rollback=rollback,failure=failure,packages=versions(),private_defaults_unchanged=defaults_unchanged(),new_faults=faults,taint_after=taint,services={n:[int(p.name) for p in processes(n)] for n in ['pipewire','wireplumber']})
 passed=verified and failure is None and not faults and taint==512 and all(len(p)==1 for p in state['services'].values()) and released(core())
 save('finished',terminal=True,passed=bool(passed))
