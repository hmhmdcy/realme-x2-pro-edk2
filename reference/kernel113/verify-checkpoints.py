from pathlib import Path
import hashlib,json,re,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
reports={}
def read(name):
    path=out/name
    with tarfile.open(path) as t:
        data={}
        for m in t:
            assert not m.issym() and not m.islnk()
            if not m.isfile(): continue
            key=m.name.removeprefix('./')
            assert not Path(key).is_absolute() and '..' not in Path(key).parts and key not in data
            data[key]=t.extractfile(m).read()
    count=0
    for line in data['SHA256SUMS'].decode().splitlines():
        digest,file=line.split('  ',1)
        assert hashlib.sha256(data[file.removeprefix('./')]).hexdigest()==digest
        count+=1
    reports[name]=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),nested_files_verified=count)
    return data

first=read('first-before-slpi.tar')
assert first['state.txt'].splitlines()[-1]==b'0' and b'#113 SMP PREEMPT' in first['uname.txt']
for name in ['desktop-before-slpi.tar']+[f'desktop-after-ram-v{i}.tar' for i in range(5,18)]+['desktop-after-ram-census14.tar']:
    if not (out/name).exists(): continue
    data=read(name)
    assert data['tainted.txt'].strip()==b'0' and b'#113 SMP PREEMPT' in data['uname.txt']
    assert data['pcm-idle.txt'].strip()==b'closed\nclosed'
    assert data['amps.txt'].count(b'powered=0 muted=1')==2
    assert b'starts=0' in data['haptics.txt']
    assert b'Leap status' in data['clock.txt'] and b'Normal' in data['clock.txt']
    assert b'alsa_output.platform-sound.HiFi__Speaker__sink' in data['sinks.txt']
    assert b'alsa_input.platform-sound.HiFi__Mic__source' in data['sources.txt']
    assert data['power-state.txt'].strip()==b'vdd=0 vddio=0'
    reports[name].update(desktop_wifi_https_ntp_audio_idle_haptics_pass=True,taint=0,
                         dpu_timeouts=data['dmesg.txt'].count(b'frame done timeout'),
                         gpu_faults=data['dmesg.txt'].count(b'*** gpu fault'))

for name in [f'sensor-ram-v{i}.tar' for i in range(5,18)]+['sensor-ram-census14.tar','sensor-ram-attributes15.tar']:
    if not (out/name).exists(): continue
    data=read(name)
    assert data['power-before.txt'].strip()==data['power-final.txt'].strip()==b'vdd=0 vddio=0'
    assert data['power-enabled.txt'].strip()==b'vdd=1 vddio=1'
    assert data['slpi-final-state.txt'].strip()==b'offline' and data['power-off-exit.txt'].strip()==b'0'
    assert data['kernel-state-after.txt'].splitlines()[-1]==b'0'
    assert data['nv-after.txt'].count(b': OK')==6 and data['source-after.txt'].count(b': OK')==4
    log=data['dmesg-final.txt']; rpc=data.get('rpcd.txt',b'').decode(errors='replace')
    report=reports[name]
    report.update(manual_supply_enable_disable_pass=True,taint=0,nv6_sources4_unchanged=True,
                  slpi_final='offline',query_exit=(int(data.get('query-exit.txt',b'')) if data.get('query-exit.txt',b'').strip().lstrip(b'-').isdigit() else None),daemon_exit=(int(data['daemon-exit.txt']) if 'daemon-exit.txt' in data else None),
                  sensor_i2c_fatal=b'I2C_ERROR_TRANSFER_TIMEOUT' in log,dpu_timeouts=log.count(b'frame done timeout'),
                  gpu_faults=log.count(b'*** gpu fault'),large_input_completed=rpc.count('large-input('),
                  ram_writes=rpc.count('ram-write('),sensor_function_accepted=False)
    report['ram_renames']=rpc.count('ram-rename(')
    report['extended_mids']=sorted(set(int(x) for x in re.findall(r'listener-mid=(\d+)',rpc)))
    if 'firmware-final.txt' in data:
        assert data['firmware-final.txt']==data['firmware-before.txt']
        assert data['firmware-final.txt'].strip()==b'qcom/sm8150/realme/samurai/slpi.mdt'
        report['original_firmware_selector_restored']=True
        report['trial_firmware_selector']=data['firmware-selected.txt'].decode().strip()
    if 'query-late-exit.txt' in data: report['query_late_exit']=int(data['query-late-exit.txt'])
    report['trial_exit']=int(data.get('trial-exit.txt',b'0'))
    report['slpi_coredump_captured']='slpi-coredump.elf' in data
    if 'slpi-coredump.elf' in data:
        assert data['coredump-read-exit.txt'].strip()==b'0'
        assert data['slpi-coredump.elf'].startswith(b'\x7fELF')
        report['slpi_coredump_bytes']=len(data['slpi-coredump.elf'])
        report['slpi_coredump_sha256']=hashlib.sha256(data['slpi-coredump.elf']).hexdigest()
        report['explicit_slpi_debug_crash']=True
        report['recovery_exit']=int(data['recover-exit.txt'])
        report['slpi_state_after_coredump']=data['slpi-state-after-coredump.txt'].decode().strip()
        report['slpi_now_up_count']=log.count(b'remote processor slpi is now up')
        report['slpi_power_up_timeout_count']=log.count(b'failed to power up')
    for kind in ('light','proximity','magnetometer','gyroscope','compass'):
        if kind+'-exit.txt' in data: report[kind+'_query_exit']=int(data[kind+'-exit.txt'])
    if 'daemon-uptime-start.txt' in data:
        report['daemon_seconds']=round(float(data['daemon-uptime-end.txt'].split()[0])-float(data['daemon-uptime-start.txt'].split()[0]),2)
        report['listener_exit_codes']=re.findall(r'listener-exit ret=(-?\d+) errno=(-?\d+)',rpc)
        report['last_listener_dispatch']=re.findall(r'listener-dispatch ret=(-?\d+) result=(\d+) handle=(\d+) method=(\d+)',rpc)[-1:]

normal=False
if (out/'reboot-radio-clean-1.tar').exists():
    data=read('reboot-radio-clean-1.tar')
    assert data['boot-id-private.txt']!=first['boot-id-private.txt']
    assert b'#113 SMP PREEMPT' in data['uname.txt'] and data['state.txt'].splitlines()[-1]==b'0'
    assert b'/dev/sda16 / f2fs rw' in data['mounts.txt']
    assert data['nv-check.txt'].count(b': OK')==6 and data['source-check.txt'].count(b': OK')==4
    normal=True
normal_count=int(normal)
if (out/'reboot-radio-clean-2.tar').exists():
    assert normal_count==1
    second=read('reboot-radio-clean-2.tar')
    assert second['boot-id-private.txt']!=data['boot-id-private.txt']
    assert b'#113 SMP PREEMPT' in second['uname.txt'] and second['state.txt'].splitlines()[-1]==b'0'
    assert second['nv-check.txt'].count(b': OK')==6 and second['source-check.txt'].count(b': OK')==4
    normal_count+=1
if (out/'reboot-radio-clean-3.tar').exists():
    assert normal_count==2
    third=read('reboot-radio-clean-3.tar')
    assert third['boot-id-private.txt']!=second['boot-id-private.txt']
    assert b'#113 SMP PREEMPT' in third['uname.txt'] and third['state.txt'].splitlines()[-1]==b'0'
    assert third['nv-check.txt'].count(b': OK')==6 and third['source-check.txt'].count(b': OK')==4
    normal_count+=1
if (out/'reboot-radio-clean-4.tar').exists():
    assert normal_count==3
    fourth=read('reboot-radio-clean-4.tar')
    assert fourth['boot-id-private.txt']!=third['boot-id-private.txt']
    assert b'#113 SMP PREEMPT' in fourth['uname.txt'] and fourth['state.txt'].splitlines()[-1]==b'0'
    assert fourth['nv-check.txt'].count(b': OK')==6 and fourth['source-check.txt'].count(b': OK')==4
    normal_count+=1
if (out/'reboot-audio-clean-6.tar').exists():
    assert normal_count==4
    sixth=read('reboot-audio-clean-6.tar')
    with tarfile.open(out/'slow-boot-radio-clean-5.tar') as t:
        assert sixth['boot-id-private.txt']!=t.extractfile('./boot-id-private.txt').read()
    assert b'#113 SMP PREEMPT' in sixth['uname.txt'] and sixth['state.txt'].splitlines()[-1]==b'0'
    assert sixth['nv-check.txt'].count(b': OK')==6 and sixth['source-check.txt'].count(b': OK')==4
    normal_count+=1
if (out/'reboot-audio-clean-7.tar').exists():
    assert normal_count==5
    seventh=read('reboot-audio-clean-7.tar')
    assert seventh['boot-id-private.txt']!=sixth['boot-id-private.txt']
    assert b'#113 SMP PREEMPT' in seventh['uname.txt'] and seventh['state.txt'].splitlines()[-1]==b'0'
    assert seventh['nv-check.txt'].count(b': OK')==6 and seventh['source-check.txt'].count(b': OK')==4
    normal_count+=1
if (out/'reboot-audio-clean-8.tar').exists():
    assert normal_count==6
    eighth=read('reboot-audio-clean-8.tar')
    assert eighth['boot-id-private.txt']!=seventh['boot-id-private.txt']
    assert b'#113 SMP PREEMPT' in eighth['uname.txt'] and eighth['state.txt'].splitlines()[-1]==b'0'
    assert eighth['nv-check.txt'].count(b': OK')==6 and eighth['source-check.txt'].count(b': OK')==4
    normal_count+=1
if (out/'reboot-audio-clean-9.tar').exists():
    assert normal_count==7
    ninth=read('reboot-audio-clean-9.tar')
    assert ninth['boot-id-private.txt']!=eighth['boot-id-private.txt']
    assert b'#113 SMP PREEMPT' in ninth['uname.txt'] and ninth['state.txt'].splitlines()[-1]==b'0'
    assert ninth['nv-check.txt'].count(b': OK')==6 and ninth['source-check.txt'].count(b': OK')==4
    normal_count+=1
previous=ninth if normal_count==8 else None
for number in (10,11,12,13,14,15):
    name=f'reboot-audio-clean-{number}.tar'
    if not (out/name).exists(): continue
    assert normal_count==number-2 and previous is not None
    current=read(name)
    assert current['boot-id-private.txt']!=previous['boot-id-private.txt']
    assert b'#113 SMP PREEMPT' in current['uname.txt'] and current['state.txt'].splitlines()[-1]==b'0'
    assert b'/dev/sda16 / f2fs rw' in current['mounts.txt']
    assert current['nv-check.txt'].count(b': OK')==6 and current['source-check.txt'].count(b': OK')==4
    normal_count+=1
    previous=current
if (out/'layout-after.tar').exists():
    layout=read('layout-after.tar'); prior=read('preflash.tar')
    for dev in ('sda','sdb','sdc','sdd','sde','sdf'):
        for suffix in ('geometry','head','tail'):
            name=f'{dev}.{suffix}'; assert layout[name]==prior[name],name
    parts=dict(line.split('  ')[::-1] for line in layout['partition-check.sha256'].decode().splitlines())
    for dev,name in [('/dev/sde11','boot-partition-k113.img'),('/dev/sde32','logdump-k113-sensor-power.img')]:
        assert parts[dev]==hashlib.sha256((out/name).read_bytes()).hexdigest()
    assert parts['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
    assert layout['nv-check.txt'].count(b': OK')==6 and layout['source-check.txt'].count(b': OK')==4
    assert layout['state.txt'].splitlines()[-1]==b'0'
    reports['layout-after.tar'].update(gpt_18_unchanged=True,boot_logdump_match=True,nv6_sources4_persist_unchanged=True,taint=0)
report=dict(checkpoints=reports,kernel_build=113,physical_first_113_after_ram_v5_unlock_apps_confirmed=True,
            normal_reboot_113_verified=normal,sensor_function_accepted=False,
            normal_reboot_113_count=normal_count,
            rolling_corruption_permanently_fixed=False,goal_complete=False)
report['physical_after_ram_v11']={'normal_reboot_attempt':7,'display_after_unlock_normal_confirmed':True,
                                'applications_reconfirmed':False,'user_requests_fewer_repeated_display_questions':True}
if (ref/'proximity-v9-validation.json').exists():
    report['proximity']=json.loads((ref/'proximity-v9-validation.json').read_text())
if (ref/'slow-boot-validation.json').exists():
    report['slow_boot_regression']=json.loads((ref/'slow-boot-validation.json').read_text())
    report['slow_boot_regression']['next_reboot_accepted']='reboot-audio-clean-6.tar' in reports
if (ref/'ulog-v11-validation.json').exists():
    report['slpi_ulog_v11']=json.loads((ref/'ulog-v11-validation.json').read_text())
if (ref/'ulog-v12-validation.json').exists():
    report['slpi_ulog_v12']=json.loads((ref/'ulog-v12-validation.json').read_text())
if (ref/'ulog-v13-validation.json').exists():
    report['slpi_ulog_v13']=json.loads((ref/'ulog-v13-validation.json').read_text())
if (ref/'magnetometer-v13-validation.json').exists():
    report['magnetometer_v13']=json.loads((ref/'magnetometer-v13-validation.json').read_text())
for trial in ('v14','v15','v16','v17','census14','attributes15'):
    path=ref/f'ulog-{trial}-validation.json'
    if path.exists(): report[f'slpi_ulog_{trial}']=json.loads(path.read_text())
for trial in ('v14','v15'):
    path=ref/f'magnetometer-{trial}-validation.json'
    if path.exists(): report[f'magnetometer_{trial}']=json.loads(path.read_text())
for name in ('magnetometer-v16-validation','sensors-v16-validation','sensors-v17-validation','sensors-census14-validation','sensors-attributes15-validation'):
    path=ref/(name+'.json')
    if path.exists(): report[name.replace('-','_')]=json.loads(path.read_text())
if (out/'passive-after-v17-long-host-fetch.tar').exists():
    passive=read('passive-after-v17-long-host-fetch.tar')
    with tarfile.open(out/'reboot-audio-clean-13.tar') as archive:
        assert passive['boot-id-private.txt']==archive.extractfile('./boot-id-private.txt').read()
    assert passive['state.txt'].splitlines()[-1]==b'0'
    assert passive['sensor-power.txt'].strip()==b'vdd=0 vddio=0'
    report['passive_after_v17']=json.loads((ref/'passive-after-v17-validation.json').read_text())
if (ref/'a11-reference-attempt.json').exists():
    report['a11_reference_attempt']=json.loads((ref/'a11-reference-attempt.json').read_text())
if (ref/'npa-own-firmware-validation.json').exists():
    npa=json.loads((ref/'npa-own-firmware-validation.json').read_text())
    assert npa['coredump_sha256']==report['slpi_ulog_v17']['coredump_sha256']
    assert npa['npa_client_value_bytes']==16 and npa['master_slave_pairs']==2
    assert npa['runtime_route_tree_nodes']==68 and npa['runtime_master_nodes']==12 and npa['runtime_slave_nodes']==33
    assert npa['spi_npa_failure_uses_normal_function_epilogue']
    assert not npa['npa_error_as_sensor_root_cause_proven'] and not npa['phone_changed']
    report['npa_own_firmware']=npa
if (ref/'ssc-census14-validation.json').exists():
    census=json.loads((ref/'ssc-census14-validation.json').read_text())
    assert census['archive_sha256']==reports['sensor-ram-census14.tar']['sha256']
    assert census['boot_checkpoint']=='reboot-audio-clean-14'
    report['ssc_census14']=census
if (ref/'ssc-attributes15-validation.json').exists():
    attributes=json.loads((ref/'ssc-attributes15-validation.json').read_text())
    assert attributes['archive_sha256']==reports['sensor-ram-attributes15.tar']['sha256']
    assert attributes['attribute_control_complete'] and attributes['attribute_responses']==15
    assert not attributes['sensor_function_accepted']
    report['ssc_attributes15']=attributes
for name in ('display-regression-boot15','display-session-reset-boot15','display-no-fbcon-boot15','display-wake15','display-trace15','display-visible15','display-clock15','display-clock15b','display-linear15-failed','display-idle-restored15'):
    if (out/(name+'.tar')).exists(): read(name+'.tar')
if (out/'wrap-up15.tar.gz').exists(): read('wrap-up15.tar.gz')
if (out/'wrap-up15-trace-final.tar.gz').exists(): read('wrap-up15-trace-final.tar.gz')
for name in ('display-regression15','display-reset15','display-actions15','display-trace15','display-visible15','display-clock15','display-clock15b','display-linear15-failed','display-idle-restored15','wrap-up15'):
    path=ref/(name+'-validation.json')
    if path.exists(): report[name.replace('-','_')]=json.loads(path.read_text())
if (ref/'display-physical-reply15.json').exists():
    report['display_physical_reply15']=json.loads((ref/'display-physical-reply15.json').read_text())
    report['latest_boot_display_regression_preserved']=True
if (ref/'user-scope-20261012.json').exists():
    report['current_user_scope']=json.loads((ref/'user-scope-20261012.json').read_text())
(ref/'checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(archives_verified=len(reports),nested_files_verified=sum(r['nested_files_verified'] for r in reports.values()),
                     normal_reboot_113_verified=normal,normal_reboot_113_count=normal_count,
                     sensor_trial_archives=sum(k.startswith('sensor-ram') for k in reports),
                     own_firmware_npa_forensics_included='npa_own_firmware' in report,goal_complete=False)))
