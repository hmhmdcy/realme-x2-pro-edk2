from pathlib import Path
import hashlib, json, os, re, subprocess, tarfile

os.umask(0o077)
out=Path('/var/lib/samurai/k174-recovery-runtime');out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot != Path('/var/lib/samurai/k174-recovery-preflash/boot-id-private.txt').read_bytes()
(out/'boot-id-private.txt').write_bytes(boot)
assert os.uname().version.startswith('#172 ')
def cmd(args):
    p=subprocess.run(args,capture_output=True);assert p.returncode==0,(args,p.stderr.decode(errors='replace'))
    return p.stdout.decode(errors='replace')
log=cmd(['dmesg']);(out/'dmesg-private.txt').write_text(log)
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
patterns={'warnings':'WARNING:','kernel_oops':'Oops:','dma_prepare':'unable to prepare channel','tx_timeout':'TX timed out','resume_failed':'NGD resume failed','gpu_fault':'gpu fault:'}
faults={n:log.count(p) for n,p in patterns.items()};assert not any(faults.values()),faults
hashes=dict((l.split()[1],l.split()[0]) for l in cmd(['sha256sum','/dev/sde11','/dev/sde32','/dev/sda2']).splitlines())
assert hashes['/dev/sde11']=='77e1a272741aeb09f780a1cff1224098bc78126f1a9154ed5d0c00d91f587a28'
assert hashes['/dev/sde32']=='0562112b37e7b6b62d764d75836ca169eb006ae446e89ca9c4a20f29fd7420c2'
assert hashes['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
cmd(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'])
expected={'/usr/libexec/samurai-audio-route':'818f63a18cc24b2fd5fd23b950f05db0f386b6e0e19075fd943faa3eedb98e2b',
 '/usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/HiFi.conf':'a3a9916090364434dbbc4e4aa607973ecc587b2894a094dece9f51a48ffb9c2e',
 '/usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/Realme_X2_Pro.conf':'2712a658e7989b290b9d26eddd3a27588a679fe3b38ae01a6f180fb266b13387'}
for p,h in expected.items(): assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
pulse=lambda args:cmd(['su','-s','/bin/sh','cy122','-c','XDG_RUNTIME_DIR=/run/user/10000 '+' '.join(args)])
modules=pulse(['pactl','list','short','modules']);(out/'pulse-modules-private.txt').write_text(modules)
cards=json.loads(pulse(['pactl','-f','json','list','cards']));(out/'pulse-cards-private.json').write_text(json.dumps(cards,indent=2)+'\n')
assert len(cards)==1 and cards[0]['active_profile']=='HiFi (Mic, Speaker)'
jack={}
for n in ['Headphone Jack','Mic Jack']:
    jack[n]=re.search(': values=(.*)',cmd(['amixer','-c','0','cget',"iface=CARD,name='"+n+"'"]))[1].strip()
assert all(v=='off' for v in jack.values())
amps={a:Path('/sys/bus/i2c/devices/'+a+'/status').read_text().strip() for a in ['1-0039','1-003a']}
assert all('powered=0 muted=1' in v and 'failed=0' in v for v in amps.values())
pcm={p:Path('/proc/asound/card0/'+p+'/sub0/status').read_text().strip() for p in ['pcm0p','pcm1c']}
assert all(v=='closed' for v in pcm.values())
report=dict(stage=174,operation='recover-kernel172-after-debugfs-name-oops',new_boot=True,no_partition_flash=True,
 kernel_build=172,taint=0,faults=faults,boot172_logdump172_and_nv_verified=True,ucm173_files_unchanged=True,
 ucm173_profile_restored_after_reboot=True,active_profile=cards[0]['active_profile'],single_pulse_card=True,
 port_switch_module_present='\tmodule-switch-on-port-available\t' in modules,
 callaudiod_present=subprocess.run(['pgrep','-x','callaudiod'],stdout=subprocess.DEVNULL).returncode==0,
 jack=jack,pcm=pcm,amps=amps,fbdev_emulation_reset=Path('/sys/module/drm_kms_helper/parameters/fbdev_emulation').read_text().strip()=='Y',
 prior_debugfs_oops_root_cause_not_yet_fixed=True,prior_fb_blank_ebusy_and_lastclose_restore_recovered=True)
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
with tarfile.open('/tmp/k174-recovery-runtime-private.tar.gz','w:gz') as ar: ar.add(out,arcname=out.name)
print(json.dumps(report),flush=True)
