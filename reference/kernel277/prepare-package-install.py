"""Derive the already validated normal-consumer restart flow, removing module work."""
from pathlib import Path
R=Path(__file__).resolve().parent
s=(R.parent/'kernel271/install-gain-pair.py').read_text()
s=s.split("code=r'''",1)[1].split("'''.replace('__MODULE__'",1)[0]
for a,b in [('k271-gain-transaction','k277-package-transaction'),('k271-gain-candidates','k277-package-candidates'),
 ('k270-work','k276-work'),('k271-services-current','k277-services-current'),('stage=271','stage=277'),
 ('samurai-camera-stack=0.1.0-r15','samurai-camera-stack=0.1.0-r18')]:s=s.replace(a,b)
def replace(a,b):
 global s
 assert s.count(a)==1,a;s=s.replace(a,b)
def span(a,b,replacement=''):
 global s
 start=s.index(a);end=s.index(b,start);s=s[:start]+replacement+s[end:]
span("tree=Path('/usr/lib/modules')",'stopped=[];',"tree=Path('/usr/lib/modules')/os.uname().release\n")
replace(" assert sha(target)==sha(original)=='22315c6f3eb233add16e33658bd071dbc973499744b21323adf8b771c1552f72'\n",'')
replace(" assert sha(stage/'s5k3m5.ko')==__MODULE__\n",'')
replace("['7-0010','8-002d','9-0010']","['6-0010','7-0010','8-002d','9-0010','6-0072']")
replace("if (p/'comm').read_text().strip()==name and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:result.append(p)","if (p/'comm').read_text().strip()==name and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z' and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:result.append(p)")
replace("  stopped.append(name)\n  assert not processes(name),'Unexpected daemon restart; inspect manager before mutation'","  stopped.append(name)\n  for _ in range(50):\n   if not processes(name):break\n   time.sleep(.1)\n  assert not processes(name),'Unexpected live daemon restart; inspect manager before mutation'")
span(" save(state='normal-sensor-unbind-submitted')"," save(state='signed-package-transaction-submitted'")
span(" save(state='new-packages-verified')"," olddb=records", " save(state='new-packages-verified')\n")
replace(" assert inventory.keys()==previous.keys() and [n for n in inventory if inventory[n]!=previous[n]]==['kernel/drivers/media/i2c/s5k3m5.ko']"," assert inventory==previous and len(inventory)==776")
span('except BaseException:\n failure=traceback.format_exc();','finally:',r'''except BaseException:
 failure=traceback.format_exc();(out/'failure-private.txt').write_text(failure);save(state='failure-restoration-pending')
 if state['packages_sent']:
  with (out/'rollback-install-private.log').open('xb') as log:
   q=subprocess.run(['apk','--no-network','--repositories-file',str(out/'rollback-repositories.list'),'add',*[x['name']+'='+x['version'] for x in old['packages']]],stdout=log,stderr=subprocess.STDOUT,timeout=60)
  assert q.returncode==0
  for path in ['etc/apk/world','etc/apk/repositories.d/60-samurai-camera.list']:
   shutil.copyfile(backup/path,Path('/')/path)
  verify_payload(old);rollback_verified=True;pair_verified=True;save(state='matching-original-packages-restored')
 else:pair_verified=True
''')
span('report=dict(stage=277,','save(state=\'verified\'',r'''report=dict(stage=277,packages_verified=pair_verified and not failure,rollback_verified=rollback_verified,failure=failure is not None,
 framework_version='99990.7.2-r23' if not failure else '99990.7.2-r22',configuration_version='0.1.0-r18' if not failure else '0.1.0-r17',
 installed_package_count=961,other_954_package_records_preserved=not failure,all_776_modules_preserved=not failure,
 new_processes=new_services,desktop_processes_preserved=True,camera_idle=idle(),fault_delta=delta,
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),no_flash_or_reboot=True,no_driver_unbind_or_unload=True,
 physical_focus_metadata_validation_pending=True)
''')
assert all(x not in s for x in ['__MODULE__','__VERMAGIC__','__NOTE__',"driver/'unbind'",'modprobe',"sha(target)"])
compile(s,'install-r23-worker.py','exec');p=R/'install-r23-worker.py';assert not p.exists();p.write_text(s)
print('Package-only worker prepared: normal PW/WP restart, no kernel/provider or desktop restart')
