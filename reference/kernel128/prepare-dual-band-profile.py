from pathlib import Path
import configparser,hashlib,json,re,runpy
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel128';out=Path('/mnt/e/edk2-samurai-out/kernel128')
key=json.loads((ref/'key-delete-postflash-validation.json').read_text());network=json.loads((ref/'5ghz-postflash-validation.json').read_text())
assert key['current_boot_delete_wait_resolved'] and network['test_network_pass'] and not any(network['new_faults'].values())
runpy.run_path(str(r/'reference/kernel126/ensure-build-volume.py'))
template=Path('/home/cy122/pmos-samurai-build126/rootfs128/etc/NetworkManager/system-connections/samurai-wifi.nmconnection')
original=(out/'live-wifi-profile-before-private.nmconnection').read_bytes();assert template.read_bytes()==original
text=original.decode();assert len(re.findall(r'^band=bg$',text,re.M))==1
assert len(re.findall(r'^id=Samurai 2\.4GHz$',text,re.M))==1
candidate=re.sub(r'^band=bg\n','',text,flags=re.M)
candidate=re.sub(r'^id=Samurai 2\.4GHz$','id=Samurai Wi-Fi',candidate,flags=re.M)
old=configparser.ConfigParser(interpolation=None);old.read_string(text)
new=configparser.ConfigParser(interpolation=None);new.read_string(candidate)
assert old.sections()==new.sections() and old['wifi']['band']=='bg' and 'band' not in new['wifi']
for section in old.sections():
 for name,value in old[section].items():
  if (section,name) in [('wifi','band'),('connection','id')]:continue
  assert new[section][name]==value
assert old['wifi-security']['psk'] and new['connection']['autoconnect']=='true' and old['connection']['uuid']==new['connection']['uuid']
path=out/'wifi-dual-band-candidate-private.nmconnection';assert not path.exists();path.write_text(candidate);path.chmod(0o600)
private=dict(before_sha256=hashlib.sha256(original).hexdigest(),candidate_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),uuid=old['connection']['uuid'])
(out/'wifi-profile-deployment-private.json').write_text(json.dumps(private,indent=2)+'\n')
report=dict(kernel128_real_delete_fix_and_5ghz_data_pass_required=True,
 original_live_and_template_profile_bytes_match=True,changed_only_band_lock_and_generic_ui_name=True,
 original_uuid_ssid_psk_security_ipv4_ipv6_autoconnect_mac_policy_preserved=True,
 explicit_2ghz_lock_removed_both_2_and5_eligible=True,new_profile_private_mode600=True,
 live_deployment_pending=True,template_unchanged_until_live_pass=True)
(ref/'wifi-profile-candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
