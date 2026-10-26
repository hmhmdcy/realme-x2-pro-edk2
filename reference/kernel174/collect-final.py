from pathlib import Path
import hashlib, json, os, re, subprocess, tarfile

os.umask(0o077)
out=Path('/var/lib/samurai/k174-final');out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==Path('/var/lib/samurai/k174-runtime-v2/boot-id-private.txt').read_bytes()
(out/'boot-id-private.txt').write_bytes(boot)
assert os.uname().version.startswith('#174 ')
def cmd(args):
    p=subprocess.run(args,capture_output=True);assert p.returncode==0,(args,p.stderr.decode(errors='replace'))
    return p.stdout.decode(errors='replace')
log=cmd(['dmesg']);(out/'dmesg-private.txt').write_text(log)
patterns={'warnings':'WARNING:','kernel_oops':'Oops:','dma_prepare':'unable to prepare channel','tx_timeout':'TX timed out','resume_failed':'NGD resume failed','gpu_fault':'gpu fault:',
          'wcd_underflow':'underflow error','wcd_overflow':'overflow error','port_closed':'Port Closed'}
faults={n:log.count(p) for n,p in patterns.items()};assert not any(faults.values()),faults
assert log.count('SLIMBUS_0_RX: ASoC error (-22)')==1
cmd(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'])
modules=cmd(['sh','-c','cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+ && sha256sum -c /var/lib/samurai/k174-preflash/old132-module-tree.sha256'])
(out/'module-check-private.txt').write_text(modules)
expected={'/usr/libexec/samurai-audio-route':'818f63a18cc24b2fd5fd23b950f05db0f386b6e0e19075fd943faa3eedb98e2b',
 '/usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/HiFi.conf':'a3a9916090364434dbbc4e4aa607973ecc587b2894a094dece9f51a48ffb9c2e',
 '/usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/Realme_X2_Pro.conf':'2712a658e7989b290b9d26eddd3a27588a679fe3b38ae01a6f180fb266b13387'}
for p,h in expected.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
saved=json.loads(Path('/var/lib/samurai/k174-dmic0-ucm174-low24/mixer-before-private.json').read_text())
restored={}
for n,v in saved.items():
    current=re.search(': values=(.*)',cmd(['amixer','-c','0','cget',"name='"+n+"'"]))[1].strip()
    restored[n]=current==v
assert all(restored.values())
pulse=lambda arg:cmd(['su','-s','/bin/sh','cy122','-c','XDG_RUNTIME_DIR=/run/user/10000 '+arg])
cards=json.loads(pulse('pactl -f json list cards'));assert len(cards)==1 and cards[0]['active_profile']=='HiFi (Mic, Speaker)'
module_lines=pulse('pactl list short modules');(out/'pulse-modules-private.txt').write_text(module_lines)
assert sum('\tmodule-alsa-card\t' in l for l in module_lines.splitlines())==1
assert '\tmodule-switch-on-port-available\t' not in module_lines
assert subprocess.run(['pgrep','-x','callaudiod'],stdout=subprocess.DEVNULL).returncode==0
jack={}
for n in ['Headphone Jack','Mic Jack']:
    jack[n]=re.search(': values=(.*)',cmd(['amixer','-c','0','cget',"iface=CARD,name='"+n+"'"]))[1].strip()
assert all(v=='off' for v in jack.values())
pcm={p:Path('/proc/asound/card0/'+p+'/sub0/status').read_text().strip() for p in ['pcm0p','pcm1c']}
amps={a:Path('/sys/bus/i2c/devices/'+a+'/status').read_text().strip() for a in ['1-0039','1-003a']}
amp_counts={}
for a,v in amps.items():
    assert 'powered=0 muted=1' in v and 'failed=0' in v and 'global=00' in v
    counts={n:int(re.search(n+r'=(\d+)',v)[1]) for n in ['starts','stops','failed']}
    assert counts['starts']==counts['stops'];amp_counts[a]=counts
report=dict(stage=174,kernel_build=174,firmware172_retained=True,dtb172_and_ucm173_retained=True,
 same_boot=boot==Path('/proc/sys/kernel/random/boot_id').read_bytes(),uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_counts=faults,
 initial_boot_card_registration_failures=1,machine_card_rebind_used=True,automatic_codec_reprobe_not_fixed=True,
 previous_kernel172_debugfs_name_oops_not_fixed=True,port_routing_policy_owner='running callaudiod',
 module_switch_on_port_available_intentionally_absent=True,single_pulse_card_and_alsa_module=True,active_profile=cards[0]['active_profile'],
 mbhc_starts_total=log.count('samurai MBHC started: micbias=2700 mV'),jack_bind_total=log.count('WCD934x headset detection connected'),
 jack=jack,pcm=pcm,amps=amps,amp_counts=amp_counts,mixer_restored=restored,
 nv_verified=True,modules132_verified=True,ngd_pm=Path('/sys/bus/platform/devices/qcom,slim-ngd.1/power/runtime_status').read_text().strip(),
 physical_headset_unavailable_and_not_tested=True)
assert report['taint']==0 and report['same_boot'] and all(v=='closed' for v in pcm.values())
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
with tarfile.open('/tmp/k174-all-private.tar.gz','w:gz') as ar:
    for p in Path('/var/lib/samurai').glob('k174*'):ar.add(p,arcname=p.name)
print(json.dumps(report),flush=True)
