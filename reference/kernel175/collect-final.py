from pathlib import Path
import hashlib, json, os, re, subprocess, tarfile

os.umask(0o077)
out=Path('/var/lib/samurai/k175-final');out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==Path('/var/lib/samurai/k175-runtime/boot-id-private.txt').read_bytes()
(out/'boot-id-private.txt').write_bytes(boot)
assert os.uname().version.startswith('#175 ')
def cmd(args):
    p=subprocess.run(args,capture_output=True);assert p.returncode==0,(args,p.stderr.decode(errors='replace'))
    return p.stdout.decode(errors='replace')
log=cmd(['dmesg']);(out/'dmesg-private.txt').write_text(log)
patterns={'warnings':'WARNING:','kernel_oops':'Oops:','asoc_error':'ASoC error','jack_disconnect_error':'jack disconnect:',
          'dma_prepare':'unable to prepare channel','tx_timeout':'TX timed out','resume_failed':'NGD resume failed','gpu_fault':'gpu fault:',
          'wcd_underflow':'underflow error','wcd_overflow':'overflow error','port_closed':'Port Closed','mclk_error':'Failed to register MCLK output'}
faults={n:log.count(p) for n,p in patterns.items()};assert not any(faults.values()),faults
known={'ngd_error_interrupt_82000000':log.count('Error Interrupt received 0x82000000'),
       'ngd_request_value_timeout':log.count('Tx:MT:0x0, MC:0x60, LA:0xcf failed:-110'),
       'mfd_bringup_timeout':log.count('Failed to bring up WCD934X: err = -110')}
assert all(v==1 for v in known.values()),known
cmd(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'])
cmd(['sh','-c','cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+ && sha256sum -c /var/lib/samurai/k175-preflash/old132-module-tree.sha256'])
assert cmd(['sha256sum','/dev/sda2']).split()[0]=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
expected={'/usr/libexec/samurai-audio-route':'818f63a18cc24b2fd5fd23b950f05db0f386b6e0e19075fd943faa3eedb98e2b',
 '/usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/HiFi.conf':'a3a9916090364434dbbc4e4aa607973ecc587b2894a094dece9f51a48ffb9c2e',
 '/usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/Realme_X2_Pro.conf':'2712a658e7989b290b9d26eddd3a27588a679fe3b38ae01a6f180fb266b13387'}
for p,h in expected.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
saved=json.loads(Path('/var/lib/samurai/k175-dmic0-ucm175-low24/mixer-before-private.json').read_text())
restored={n:re.search(': values=(.*)',cmd(['amixer','-c','0','cget',"name='"+n+"'"]))[1].strip()==v for n,v in saved.items()}
assert all(restored.values())
pulse=lambda arg:cmd(['su','-s','/bin/sh','cy122','-c','XDG_RUNTIME_DIR=/run/user/10000 '+arg])
cards=json.loads(pulse('pactl -f json list cards'));assert len(cards)==1 and cards[0]['active_profile']=='HiFi (Mic, Speaker)'
modules=pulse('pactl list short modules');(out/'pulse-modules-private.txt').write_text(modules)
assert sum('\tmodule-alsa-card\t' in l for l in modules.splitlines())==1
assert '\tmodule-switch-on-port-available\t' not in modules
assert subprocess.run(['pgrep','-x','callaudiod'],stdout=subprocess.DEVNULL).returncode==0
names={kind:(Path('/sys/kernel/debug/regmap')/addr/'name').read_text().strip() for kind,addr in [('main','217:250:1:0'),('interface','217:250:0:0')]}
assert names=={'main':'wcd934x-slim','interface':'nodev'}
mapdirs=[p.name for p in Path('/sys/kernel/debug/regmap').iterdir() if p.name.startswith('217:250:')]
assert sorted(mapdirs)==['217:250:0:0','217:250:1:0']
assert sum(bool(re.match(r'^\s+mclk\s',l)) for l in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines())==1
jack={n:re.search(': values=(.*)',cmd(['amixer','-c','0','cget',"iface=CARD,name='"+n+"'"]))[1].strip() for n in ['Headphone Jack','Mic Jack']}
assert all(v=='off' for v in jack.values())
pcm={p:Path('/proc/asound/card0/'+p+'/sub0/status').read_text().strip() for p in ['pcm0p','pcm1c']}
amps={a:Path('/sys/bus/i2c/devices/'+a+'/status').read_text().strip() for a in ['1-0039','1-003a']}
counts={a:{n:int(re.search(n+r'=(\d+)',s)[1]) for n in ['starts','stops','failed']} for a,s in amps.items()}
assert all('global=00' in s and 'powered=0 muted=1' in s for s in amps.values())
assert all(c['starts']==c['stops'] and c['failed']==0 for c in counts.values())
completed=[json.loads((Path('/var/lib/samurai/k175-reprobe-v2')/('case-%d-validation.json'%i)).read_text()) for i in range(3)]
assert [r['target'] for r in completed]==['codec','codec','mfd']
phase=json.loads(Path('/var/lib/samurai/k175-reprobe-v2/case-3-phase-private.json').read_text())
assert phase['phase']=='unbound'
assert Path('/sys/bus/slimbus/devices/217:250:1:0/driver').resolve()==Path('/sys/bus/slimbus/drivers/wcd934x-slim')
report=dict(stage=175,kernel_build=175,same_boot=boot==Path('/proc/sys/kernel/random/boot_id').read_bytes(),
 uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 fault_counts=faults,known_parent_rebind_fault_counts=known,parent_rebind_reliability_not_fixed=True,
 first_boot_card_recovered_without_machine_rebind=True,current_card_present_after_failed_bind_and_later_probe=True,
 no_test_restoration_bind_receipt_in_failed_case=True,completed_reprobe_cases=completed,
 initial_reprobe_test_three_second_idle_check_failed_before_pulse_five_second_timeout=True,
 current_regmap_names=names,exactly_two_regmap_dirs=True,single_mclk=True,
 old_debugfs_dead_handles_verified_in_completed_cases=4,current_debugfs_name_reads_without_oops=True,
 mbhc_starts_total=log.count('samurai MBHC started: micbias=2700 mV'),jack_binds_total=log.count('WCD934x headset detection connected'),
 single_pulse_card_and_alsa_module=True,active_profile=cards[0]['active_profile'],port_policy_owner='callaudiod',
 jack=jack,pcm=pcm,amps=amps,amp_counts=counts,mixer_restored=restored,nv_and_persist_verified=True,modules132_verified=True,
 ucm173_unchanged=True,ngd_pm=Path('/sys/bus/platform/devices/qcom,slim-ngd.1/power/runtime_status').read_text().strip(),
 physical_headset_not_available_or_tested=True)
assert report['taint']==0 and report['same_boot'] and all(v=='closed' for v in pcm.values())
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
with tarfile.open('/tmp/k175-all-private.tar.gz','w:gz') as ar:
    for p in Path('/var/lib/samurai').glob('k175*'):ar.add(p,arcname=p.name)
print(json.dumps(report),flush=True)
