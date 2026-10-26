"""Two finite physical captures through drivers that bound at boot210."""
from pathlib import Path
import hashlib,json,os,re,signal,subprocess,threading,time
os.umask(0o077)
root=Path('/var/lib/samurai');out=root/'k210-static-front-capture';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k210-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
sensor=Path('/sys/bus/i2c/devices/7-0010');camss=Path('/sys/bus/platform/devices/acb3000.camss');cci=Path('/sys/bus/platform/devices/ac4b000.cci')
assert (sensor/'driver').resolve().name=='imx471' and (camss/'driver').exists()
assert (sensor/'of_node').resolve().as_posix().endswith('/soc@0/cci@ac4b000/i2c-bus@1/camera@10')
assert all(not Path('/sys/module'/Path(n)).exists() for n in ['samurai_front_overlay','samurai_vio_phandle','samurai_cci_bringup','samurai_camera_perf'])
tool=root/'k197-offline-tools/front-capture-aarch64-private';manifest=json.loads((tool.parent/'manifest.json').read_text())
assert hashlib.sha256(tool.read_bytes()).hexdigest()==next(x['sha256'] for x in manifest if x['file']==tool.name)
report=dict(stage=210,static_boot_bound_drivers=True,no_temporary_overlay_or_performance_helper=True,cycles=[],pm_samples=[])
before_log=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before_log)
def save():(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
def video_fds():
    result=[]
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():continue
        try:
            for p in (process/'fd').iterdir():
                try:
                    target=os.readlink(p)
                    if target.startswith(('/dev/video','/dev/media','/dev/v4l-subdev')):result.append(dict(pid=process.name,fd=p.name,target=target))
                except OSError:pass
        except OSError:pass
    return result
def pm_sample(label):
    rails={}
    for p in Path('/sys/class/regulator').glob('regulator.*'):
        name=(p/'name').read_text().strip()
        if name not in ['cam-front-vdig','cam-front-vana','ldo1']:continue
        if name=='ldo1' and (not (p/'of_node').exists() or not str((p/'of_node').resolve()).endswith('/regulators-1/ldo1')):continue
        rails[name]={n:(p/n).read_text().strip() for n in ['state','num_users','microvolts']}
    clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text()
    clock=[l.split() for l in clocks.splitlines() if re.search(r'\bcam_cc_mclk2_clk\s',l)];assert len(clock)==1
    sample=dict(label=label,sensor=(sensor/'power/runtime_status').read_text().strip(),camss=(camss/'power/runtime_status').read_text().strip(),cci=(cci/'power/runtime_status').read_text().strip(),regulators=rails,mclk_enable_count=int(clock[0][1]),mclk_rate_hz=int(clock[0][4]))
    report['pm_samples'].append(sample);save();return sample
def idle(label):
    time.sleep(1);sample=pm_sample(label)
    assert sample['sensor']=='suspended' and sample['camss']=='suspended' and sample['cci']=='suspended'
    assert sample['mclk_enable_count']==0 and sample['mclk_rate_hz']==19200000
    assert all(sample['regulators'][n]['state']=='disabled' and sample['regulators'][n]['num_users']=='0' for n in ['cam-front-vdig','cam-front-vana','ldo1'])
    pd=Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_text();(out/(label+'-genpd-private.txt')).write_text(pd)
    assert re.search(r'genpd:3:acb3000.camss\s+suspended\s+0\s',pd)
    assert not video_fds()
def topology(label):
    p=subprocess.run(['media-ctl','-d','/dev/media0','-p'],capture_output=True,timeout=10);assert p.returncode==0
    (out/(label+'-graph-private.txt')).write_bytes(p.stdout+p.stderr);return p.stdout
assert not video_fds();original_graph=topology('before');assert b'imx471 7-0010' in original_graph
idle('before');save()
try:
    for label in ['first','second']:
        process=subprocess.Popen([str(tool),'--capture',str(out/(label+'-first-frame-private.raw'))],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        active=[]
        def observe():
            for _ in range(400):
                if process.poll() is not None:break
                pd=Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_text()
                if re.search(r'genpd:3:acb3000.camss\s+active\s+384\s',pd):
                    clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text();rows=[l.split() for l in clocks.splitlines() if re.search(r'\bcam_cc_ife_0_clk\s',l)]
                    if rows and int(rows[0][1])>0:
                        (out/(label+'-active-genpd-private.txt')).write_text(pd);(out/(label+'-active-clocks-private.txt')).write_text(clocks)
                        rates={name:int(next(l.split()[4] for l in clocks.splitlines() if re.search(r'\b'+name+r'\s',l))) for name in ['cam_cc_ife_0_clk','cam_cc_ife_0_csid_clk','cam_cc_mclk2_clk']}
                        active.append(dict(mmcx_performance_state=384,clock_rates_hz=rates));break
                time.sleep(.002)
        thread=threading.Thread(target=observe);thread.start()
        try:stdout,stderr=process.communicate(timeout=30)
        finally:
            if process.poll() is None:process.terminate();stdout,stderr=process.communicate(timeout=10)
            thread.join(timeout=5);assert not thread.is_alive()
        (out/(label+'-capture-private.log')).write_bytes(stdout+stderr)
        row=dict(label=label,exit=process.returncode,active_performance_snapshot=active)
        frames=[]
        for match in re.finditer(rb'FRAME number=(\d+) index=(\d+) sequence=(\d+) bytes=(\d+) changed=(\d+) active_bytes=(\d+) hash=[0-9a-f]+ timestamp_us=(\d+)',stdout):
            frames.append(dict(zip(['number','buffer','sequence','bytes','active_bytes_changed','active_bytes','timestamp_us'],map(int,match.groups()))))
        row['frames']=frames;report['cycles'].append(row);save()
        assert process.returncode==0 and len(frames)==3
        assert b'PATTERNS sensor=0 csid=0 physical_link=enabled' in stdout and b'CAPTURE_RESULT success=1 cleanup_complete=1' in stdout
        assert len(active)==1
        rates=active[0]['clock_rates_hz']
        assert abs(rates['cam_cc_ife_0_clk']-847000000)<=100
        assert rates['cam_cc_ife_0_csid_clk']==600000000 and rates['cam_cc_mclk2_clk']==19200000
        idle(label+'-idle');assert topology(label+'-after')==original_graph
    assert report['cycles'][1]['frames'][0]['timestamp_us']>report['cycles'][0]['frames'][-1]['timestamp_us']
    report['six_physical_raw10_frames_captured']=True
finally:
    after_log=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after_log)
    report['fault_delta']={k:after_log.count(v)-before_log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
    report['taint']=int(Path('/proc/sys/kernel/tainted').read_text());report['video_fds_after']=len(video_fds());save()
assert not any(report['fault_delta'].values()) and report['taint']==0 and report['video_fds_after']==0
report['graph_restored_after_each_cycle']=True;report['all_idle_rails_clocks_and_own_mmcx_votes_released']=True;save()
print(json.dumps(report))
