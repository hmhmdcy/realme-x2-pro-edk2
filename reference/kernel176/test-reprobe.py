from pathlib import Path
import errno, json, os, re, shlex, subprocess, time, wave

os.umask(0o077)
out=Path('/var/lib/samurai/k176-reprobe');out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==Path('/var/lib/samurai/k176-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#176 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
(out/'boot-id-private.txt').write_bytes(boot)
def cmd(args):
    p=subprocess.run(args,capture_output=True);assert p.returncode==0,(args,p.stderr.decode(errors='replace'))
    return p.stdout.decode(errors='replace')
def pulse(args):return cmd(['su','-s','/bin/sh','cy122','-c','XDG_RUNTIME_DIR=/run/user/10000 '+shlex.join(['pactl']+args)])
def pcm_closed():return all(p.read_text().strip()=='closed' for p in Path('/proc/asound').glob('card*/pcm*/sub*/status'))
def amps_off():
    data={a:Path('/sys/bus/i2c/devices/'+a+'/status').read_text().strip() for a in ['1-0039','1-003a']}
    assert all('powered=0 muted=1' in s and 'failed=0' in s for s in data.values());return data
def supply_counts():
    rows={}
    for line in Path('/sys/kernel/debug/regulator/regulator_summary').read_text().splitlines():
        fields=line.split()
        if fields and re.fullmatch(r'217:250:1:0-vdd-(?:io|rx|tx|buck-sido|buck)',fields[0]):
            rows[fields[0]]=int(fields[1])
    return rows
def map_paths():
    return {kind:Path('/sys/kernel/debug/regmap')/name/'name' for kind,name in [('main','217:250:1:0'),('interface','217:250:0:0')]}
def map_read():
    rows={n:p.read_text().strip() for n,p in map_paths().items()};assert rows=={'main':'wcd934x-slim','interface':'nodev'}
    return rows
def clock_count():
    text=Path('/sys/kernel/debug/clk/clk_summary').read_text()
    return sum(bool(re.match(r'^\s+mclk\s',line)) for line in text.splitlines())
def wait_card():
    for _ in range(60):
        if 'Realme X2 Pro' in Path('/proc/asound/cards').read_text():return
        time.sleep(.5)
    raise AssertionError('Card did not recover without machine rebind')
def wait_pulse():
    for _ in range(40):
        cards=json.loads(pulse(['-f','json','list','cards']))
        if len(cards)==1 and cards[0]['active_profile']=='HiFi (Mic, Speaker)':return cards[0]
        time.sleep(.5)
    raise AssertionError('Pulse card/profile did not recover')
def suspend():
    pulse(['suspend-sink','alsa_output.platform-sound.HiFi__Speaker__sink','1'])
    pulse(['suspend-source','alsa_input.platform-sound.HiFi__Mic__source','1'])
    time.sleep(.5);assert pcm_closed();amps_off()
def unsuspend():
    pulse(['suspend-sink','alsa_output.platform-sound.HiFi__Speaker__sink','0'])
    pulse(['suspend-source','alsa_input.platform-sound.HiFi__Mic__source','0'])
before=cmd(['dmesg']);(out/'dmesg-before-private.txt').write_text(before)
assert 'ASoC error' not in before
assert len(json.loads(pulse(['-f','json','list','sink-inputs'])))==0
assert len(json.loads(pulse(['-f','json','list','source-outputs'])))==0
map_read();assert clock_count()==1
supplies_before=supply_counts();assert len(supplies_before)==5 and all(v==1 for v in supplies_before.values())
cases=[]
for index,kind in enumerate(['codec','codec'] + ['mfd'] * 8):
    assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes()
    assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
    suspend();old_names=map_read()
    driver=Path('/sys/bus/'+('platform' if kind=='codec' else 'slimbus')+'/drivers/'+('wcd934x-codec' if kind=='codec' else 'wcd934x-slim'))
    nodes=[p for p in driver.iterdir() if p.is_symlink() and p.name!='module']
    assert len(nodes)==1
    name=nodes[0].name;device=nodes[0].resolve();assert (device/'driver').resolve()==driver
    targets=['interface'] if kind=='codec' else ['main','interface']
    fds={n:os.open(map_paths()[n],os.O_RDONLY|os.O_CLOEXEC) for n in targets}
    stale={};unbound=False
    phase=out/('case-%d-phase-private.json'%index)
    phase.write_text(json.dumps(dict(kind=kind,device=name,phase='before-unbind'))+'\n')
    try:
        (driver/'unbind').write_text(name+'\n')
        assert not (device/'driver').exists();unbound=True
        phase.write_text(json.dumps(dict(kind=kind,device=name,phase='unbound'))+'\n')
        assert 'no soundcards' in Path('/proc/asound/cards').read_text()
        present={n:p.exists() for n,p in map_paths().items()}
        assert present==({'main':True,'interface':False} if kind=='codec' else {'main':False,'interface':False}),present
        assert clock_count()==0
        supplies_unbound=supply_counts()
        if kind=='mfd':assert all(v==0 for v in supplies_unbound.values())
        else:assert supplies_unbound==supplies_before
        for n,fd in fds.items():
            try:data=os.pread(fd,128,0)
            except OSError as e:
                assert e.errno in [errno.EIO,errno.ENODEV,errno.ENOENT],e
                stale[n]=e.errno
            else:raise AssertionError(('Removed debugfs handle still readable',n,data))
        (driver/'bind').write_text(name+'\n');unbound=False
        phase.write_text(json.dumps(dict(kind=kind,device=name,phase='bound'))+'\n')
        wait_card();card=wait_pulse();new_names=map_read();assert clock_count()==1
        supplies_after=supply_counts();assert supplies_after==supplies_before
        maps=[p.name for p in Path('/sys/kernel/debug/regmap').iterdir() if p.name.startswith('217:250:')]
        assert sorted(maps)==['217:250:0:0','217:250:1:0']
        assert sum('\tmodule-alsa-card\t' in l for l in pulse(['list','short','modules']).splitlines())==1
        unsuspend();suspend()
        target=out/('case-%d-capture-private.wav'%index)
        with (out/('case-%d-capture-private.log'%index)).open('wb') as log:
            rec=subprocess.Popen(['arecord','-q','-D','hw:0,1','-r','48000','-c','1','-f','S16_LE','-d','1',str(target)],stdout=log,stderr=log)
            try:
                time.sleep(.25);assert 'RUNNING' in Path('/proc/asound/card0/pcm1c/sub0/status').read_text()
                assert rec.wait(timeout=4)==0
            finally:
                if rec.poll() is None:rec.terminate();rec.wait(timeout=3)
        with wave.open(str(target),'rb') as w:assert w.getnframes()==48000
        unsuspend()
        # PulseAudio suspend-on-idle normally waits five seconds after resume.
        for idle_sample in range(24):
            if pcm_closed():break
            time.sleep(.5)
        assert pcm_closed();amps_off()
        assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
        row=dict(case=index,target=kind,driver_unbind_bind_once=True,card_recovered_without_machine_rebind=True,
                 removed_regmap_names_absent=True,old_debugfs_handle_errno=stale,mclk_removed_and_recreated=True,
                 new_regmap_names=new_names,exactly_two_regmaps_and_single_pulse_card=True,
                 active_profile=card['active_profile'],capture_frames_after_rebind=48000,running_seen=True,pcm_closed=True,
                 supplies_unbound=supplies_unbound,supplies_after=supplies_after)
        cases.append(row);(out/('case-%d-validation.json'%index)).write_text(json.dumps(row,indent=2)+'\n')
    finally:
        for fd in fds.values():os.close(fd)
        if unbound and boot==Path('/proc/sys/kernel/random/boot_id').read_bytes() and not (device/'driver').exists():
            (driver/'bind').write_text(name+'\n')
            phase.write_text(json.dumps(dict(kind=kind,device=name,phase='restoration-bind-after-failure'))+'\n')
            wait_card();wait_pulse()
            unsuspend()
after=cmd(['dmesg']);(out/'dmesg-after-private.txt').write_text(after)
patterns={'warnings':'WARNING:','oops':'Oops:','asoc_error':'ASoC error','jack_disconnect':'jack disconnect:',
          'dma_prepare':'unable to prepare channel','tx_timeout':'TX timed out','underflow':'underflow error','overflow':'overflow error','port_closed':'Port Closed',
          'mclk_error':'Failed to register MCLK output','irq_chip_error':'Failed to add IRQ chip','ngd_error_interrupt':'Error Interrupt received','transfer_timeout':'failed:-110','bringup_error':'Failed to bring up WCD934X:'}
delta={n:after.count(p)-before.count(p) for n,p in patterns.items()};assert not any(delta.values()),delta
report=dict(stage=176,kernel_build=176,cases=cases,fault_delta=delta,taint=0,same_boot=boot==Path('/proc/sys/kernel/random/boot_id').read_bytes(),
 no_machine_card_driver_rebind_used=True,old_debugfs_handles_total=len([v for r in cases for v in r['old_debugfs_handle_errno'].values()]),
 pcm_closed=pcm_closed(),amps=amps_off(),port_policy_owner='callaudiod',no_gain_or_classh_changes=True,supplies_before=supplies_before,all_supply_consumer_counts_balanced=True)
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
