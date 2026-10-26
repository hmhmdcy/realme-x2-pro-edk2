from pathlib import Path
import hashlib,json,re,sys,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
trial=sys.argv[1]
assert trial in ('15','15b')
path=out/f'display-clock{trial}.tar'
with tarfile.open(path) as archive:
    data={}
    for entry in archive:
        assert not entry.issym() and not entry.islnk()
        if not entry.isfile():continue
        name=entry.name.removeprefix('./')
        assert not Path(name).is_absolute() and '..' not in Path(name).parts and name not in data
        data[name]=archive.extractfile(entry).read()
count=0
for line in data['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
    count+=1
assert data['slpi-after.txt'].strip()==b'offline' and data['power-after.txt'].strip()==b'vdd=0 vddio=0'
assert data['fbcon-after.txt'].strip()==b'0'
assert data['nv-check.txt'].count(b': OK')==6 and data['source-check.txt'].count(b': OK')==4
assert b': OK' in data['greetd-unchanged.txt'] and data['phoc-after.txt'].strip() and data['phosh-after.txt'].strip()
before=data['dmesg-before.txt'];after=data['dmesg-after.txt']
probe=data['probe.txt'].decode();trace=data['trace-private.txt'].decode()
report=dict(archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),nested_files_verified=count,
    boot_checkpoint='reboot-audio-clean-15',probe_exit=int(data['probe-exit.txt']),
    taint_before=int(data['state-before.txt'].splitlines()[-1]),taint_after=int(data['state-after.txt'].splitlines()[-1]),
    new_dpu_frame_done_timeouts=after.count(b'frame done timeout')-before.count(b'frame done timeout'),
    new_pingpong_done_timeouts=after.count(b'kickoff timeout')-before.count(b'kickoff timeout'),
    new_kernel_warning_lines=after.count(b'WARNING:')-before.count(b'WARNING:'),
    new_gpu_faults=after.count(b'*** gpu fault')-before.count(b'*** gpu fault'),
    total_dpu_timeouts=after.count(b'frame done timeout'),phosh_restored=True,
    slpi_offline_sensor_power_off=True,nv6_sources4_unchanged=True,greetd_configuration_unchanged=True,
    existing_snapshot_preserved=True,partition_writes=False,
    physical_clock_comparison_verified=False,permanent_display_fix_accepted=False,goal_complete=False)
if trial=='15':
    assert report['probe_exit']==1 and 'CRTC must be inactive after GUI stop' in probe
    assert 'PHASE_BEGIN' not in probe
    report.update(retained_crtc_guard_refused=True,test_modes_submitted=False)
else:
    assert report['probe_exit']==0
    begin=re.findall(r'PHASE_BEGIN name=(\S+) clock_khz=(\d+) htotal=(\d+) vtotal=(\d+) refresh=60',probe)
    end=re.findall(r'PHASE_END name=(\S+) flips=(\d+) elapsed=([\d.]+) interrupted=0',probe)
    assert [row[0] for row in begin]==[row[0] for row in end]==['baseline','stock-rate','return-baseline']
    phases=[]
    for first,last in zip(begin,end):
        name,clock,htotal,vtotal=first
        assert int(last[1])>=100 and 20<=float(last[2])<=23
        rates={}
        for line in data[f'{name}-state-0.txt'].decode().splitlines():
            fields=line.split()
            if fields and fields[0] in ('disp_cc_mdss_pclk0_clk','disp_cc_mdss_byte0_clk','disp_cc_mdss_byte0_intf_clk','disp_cc_mdss_mdp_clk'):
                assert len(fields)>4
                rates[fields[0]]=int(fields[4])
        assert set(rates)=={'disp_cc_mdss_pclk0_clk','disp_cc_mdss_byte0_clk','disp_cc_mdss_byte0_intf_clk','disp_cc_mdss_mdp_clk'}
        mode_rows=re.findall(r'^\s*mode: "[^"]+": (.*)$',data[f'{name}-state-2.txt'].decode(),re.M)
        assert len(mode_rows)==1
        fields=mode_rows[0].split()
        assert list(map(int,fields[:3]))==[60,int(clock),1080]
        assert int(fields[5])==int(htotal) and int(fields[6])==2400 and int(fields[9])==int(vtotal)
        byte=rates['disp_cc_mdss_byte0_clk']
        assert (138_000_000<byte<139_000_000) if name=='stock-rate' else (46_000_000<byte<47_000_000)
        phases.append(dict(name=name,clock_khz=int(clock),htotal=int(htotal),vtotal=int(vtotal),refresh_hz=60,
            page_flips=int(last[1]),seconds=float(last[2]),clock_rates_hz=rates,dsi_bit_rate_hz=8*byte))
    events=re.findall(r'\s(\d+\.\d+): (\w+): (.*)',trace)
    report.update(test_modes_submitted=True,phases=phases,total_page_flips=sum(p['page_flips'] for p in phases),
        trace_frame_done_timeouts=sum(name=='dpu_enc_frame_done_timeout' for _,name,_ in events),
        trace_pingpong_timeouts=sum(name=='dpu_enc_phys_cmd_pdone_timeout' for _,name,_ in events),
        trace_frame_done_callbacks=sum(name=='dpu_enc_frame_done_cb' for _,name,_ in events),
        watchdog_arm_count=sum(name=='dpu_enc_frame_watchdog' and 'action=arm ' in body for _,name,body in events),
        trace_records=len(events))
    (out/'display-clock15b-events-private.json').write_text(json.dumps(events,indent=2)+'\n')
(ref/f'display-clock{trial}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
