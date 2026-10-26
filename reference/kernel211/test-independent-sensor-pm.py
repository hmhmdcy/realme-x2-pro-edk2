from pathlib import Path
import json,os,re,signal,subprocess,time
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k211-independent-sensor-pm';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
sensor=Path('/sys/bus/i2c/devices/7-0010');camss=Path('/sys/bus/platform/devices/acb3000.camss');cci=Path('/sys/bus/platform/devices/ac4b000.cci');control=sensor/'power/control';original=control.read_text().strip();assert original=='auto'
assert (sensor/'driver').resolve().name=='imx471'
assert all((p/'power/runtime_status').read_text().strip()=='suspended' for p in [sensor,camss,cci])
holders={}
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():continue
    try:
        for fd in (proc/'fd').iterdir():
            try:
                if os.readlink(fd).startswith(('/dev/video','/dev/media','/dev/v4l-subdev')):holders[int(proc.name)]=proc
            except OSError:pass
    except OSError:pass
assert len(holders)<=1
monitor=next(iter(holders.values())) if holders else None;start=None
if monitor:
    assert (monitor/'comm').read_text().strip()=='wireplumber' and int((monitor/'status').read_text().split('Uid:',1)[1].split()[0])==10000
    assert 'State:\tT' not in (monitor/'status').read_text();start=(monitor/'stat').read_text().split()[21]
before=subprocess.check_output(['dmesg']);assert not any(x in before for x in [b'WARNING:',b'Oops:',b'gpu fault:',b'fatal error received',b'Frame reassembly failed'])
report=dict(stage=211,original_sensor_control=original,samples=[],sensor_policy_restored=False,monitor_resumed=not bool(monitor))
def save():(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
def sample(label):
    clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text();mclk=next(l.split() for l in clocks.splitlines() if re.search(r'\bcam_cc_mclk2_clk\s',l));rails={}
    for p in Path('/sys/class/regulator').glob('regulator.*'):
        name=(p/'name').read_text().strip()
        if name in ['cam-front-vdig','cam-front-vana']:rails[name]={n:(p/n).read_text().strip() for n in ['state','num_users','microvolts']}
    row=dict(label=label,sensor=(sensor/'power/runtime_status').read_text().strip(),camss=(camss/'power/runtime_status').read_text().strip(),cci=(cci/'power/runtime_status').read_text().strip(),mclk_enable_count=int(mclk[1]),mclk_hz=int(mclk[4]),rails=rails)
    report['samples'].append(row);(out/(label+'-genpd-private.txt')).write_bytes(Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_bytes());save();return row
def interrupt(signum,frame):raise RuntimeError('Interrupted independent sensor PM test; restore policy/monitor')
for sig in [signal.SIGTERM,signal.SIGINT,signal.SIGHUP]:signal.signal(sig,interrupt)
save()
try:
    if monitor:
        os.kill(int(monitor.name),signal.SIGSTOP)
        for _ in range(50):
            if 'State:\tT' in (monitor/'status').read_text():break
            time.sleep(.01)
        assert 'State:\tT' in (monitor/'status').read_text()
    initial=sample('before');assert initial['mclk_enable_count']==0
    control.write_text('on\n');active=sample('sensor-only-active')
    assert active['sensor']=='active' and active['camss']==active['cci']=='suspended'
    assert active['mclk_enable_count']==1 and active['mclk_hz']==19200000
    assert len(active['rails'])==2 and all(x['state']=='enabled' and x['num_users']=='1' for x in active['rails'].values())
    report['independent_sensor_resume_passed']=True;save()
finally:
    control.write_text(original+'\n')
    for _ in range(50):
        if (sensor/'power/runtime_status').read_text().strip()=='suspended':break
        time.sleep(.05)
    report['sensor_policy_restored']=control.read_text().strip()==original
    if monitor:
        assert (monitor/'stat').read_text().split()[21]==start;os.kill(int(monitor.name),signal.SIGCONT);time.sleep(.1);report['monitor_resumed']='State:\tT' not in (monitor/'status').read_text()
    save()
idle=sample('restored-idle');assert idle['sensor']==idle['camss']==idle['cci']=='suspended' and idle['mclk_enable_count']==0
assert all(x['state']=='disabled' and x['num_users']=='0' for x in idle['rails'].values())
after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after)
report['fault_delta']={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(report['fault_delta'].values())
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0';report.update(taint=0,independent_resume_and_suspend_verified=True);save();print(json.dumps(report))
