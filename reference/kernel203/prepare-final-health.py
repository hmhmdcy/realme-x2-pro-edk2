from pathlib import Path
import ast

here=Path(__file__).resolve().parent
source=(here.parent/'kernel202/reboot-r2/final-health.py').read_text().replace("root/'k202r2-final-health'","root/'k203-final-health'")
source=source.replace("root/'k202r2-runtime/boot-id-private.txt'","root/'k203-baseline/boot-id-private.txt'").replace('k202r2-geoclue-first-session','k203-geoclue-package-test').replace('k202r2-runtime/desktop-env-private.json','k203-baseline/desktop-env-private.json')
source=source.replace('stage=202,reboot_cycle=2','stage=203,same_boot202r2=True').replace('openrc_autostart_and_idle_utc_preparation_verified=True','packaged_helper_restart_and_idle_utc_preparation_verified=True').replace('first_session_nmea_time_advances','packaged_session_nmea_time_advances').replace('first_session_nonzero_distinct_gga_times','packaged_session_nonzero_distinct_gga_times').replace('first_session_real_fix_obtained','packaged_session_real_fix_obtained')
source=source.replace("assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes()",r'''
manifest=json.loads((root/'packages/gnss-203/package-manifest.json').read_text())
versions={}
for entry in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 fields={line[:1]:line[2:] for line in entry.splitlines() if len(line)>1 and line[1]==':' and line[:1] in ['P','V']}
 if fields.get('P') in {'modemmanager','modemmanager-openrc','modemmanager-udev','libmm-glib','samurai-gnss-assist','samurai-gnss-stack'}:versions[fields['P']]=fields['V']
for item in manifest['packages']:
 assert versions[item['name']]==item['version']
 for relative,expected in item['files'].items():
  path=Path('/')/relative
  if expected['kind']=='symlink':assert path.is_symlink() and str(path.readlink())==expected['target']
  else:assert hashlib.sha256(path.read_bytes()).hexdigest()==expected['sha256'] and path.stat().st_mode & 0o7777==expected['mode']
proc=json.loads((root/'k203-package-preflight/processes-private.json').read_text());assert hashlib.sha256(Path('/proc/%d/exe'%proc['mm_pid']).read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
usb={}
for item in Path('/sys/class/udc').iterdir():usb[item.name]=(item/'state').read_text().strip()
(out/'usb-udc-state-private.json').write_text(json.dumps(usb,indent=2)+'\n')
report.update(installed_package_versions=versions,all_signed_package_payloads_still_exact=True,mm_loaded_executable_still191=True,mm_loaded_executable_inode_retired=os.readlink('/proc/%d/exe'%proc['mm_pid']).endswith(' (deleted)'),global_verification_public_key_present=Path('/etc/apk/keys/samurai-linux-203.rsa.pub').is_file(),local_repository_configuration_exact=Path('/etc/apk/repositories.d/50-samurai-gnss.list').read_text()=='ndx file:///var/lib/samurai/packages/gnss-203/packages.adb\n',offline_rootfs132_image_not_updated=True,new_reboot_not_performed=True)
assert report['global_verification_public_key_present'] and report['local_repository_configuration_exact']
assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes()
''')
# The inserted raw source must contain ordinary newline escape literals.
source=source.replace("split('\\\\n\\\\n')", "split('\\n\\n')").replace("+'\\\\n'", "+'\\n'").replace("packages.adb\\\\n'", "packages.adb\\n'")
ast.parse(source);(here/'final-health.py').write_text(source)
probe=(here/'probe-transports.py').read_text().replace('transport-probes-private.json','transport-probes-final-private.json').replace("name+'-probe-failed-private.log'","name+'-probe-final-failed-private.log'")
ast.parse(probe);(here/'probe-transports-final.py').write_text(probe)
print('Prepared final current-state checks; no transition or package transaction requested.')
