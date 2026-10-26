from pathlib import Path
import tarfile,hashlib,json,re
out=Path('/mnt/e/edk2-samurai-out/kernel81');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel81')
p=out/'display-raw.tar';assert hashlib.sha256(p.read_bytes()).hexdigest()=='a7466dc32ac4e57683dae4f768501d9ec03dcb4e1267698f2308bafc9b4c4a01'
with tarfile.open(p) as t:
    for m in t:
        assert m.isfile() and m.name.startswith('k81-') and '/' not in m.name
        name=m.name.removeprefix('k81-');target=out/name;data=t.extractfile(m).read()
        if target.exists():assert target.read_bytes()==data
        else:target.write_bytes(data)
hashes={}
for line in (out/'display-device-hashes.txt').read_text().splitlines():
    digest,path=line.split('  ',1);name=Path(path).name.removeprefix('k81-');assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest;hashes[name]=digest
before=(out/'probe-before-dmesg.txt').read_text();after=(out/'probe-after-dmesg.txt').read_text()
errors=lambda s:re.findall(r'^.*frame done timeout.*$',s,re.M)
assert errors(before)==errors(after) and len(errors(after))==2
enc_before=(out/'probe-before-encoder.txt').read_text();enc_after=(out/'probe-after-encoder.txt').read_text()
for s in (enc_before,enc_after):assert 'frame_done_cnt:2mode:' in s and re.search(r'underrun:\s*0\s',s)
prior=(ref.parent/'kernel80/final-dmesg.txt').read_text();assert errors(prior)==errors(before)
# Validate completed event/CRC sequences with the previously reviewed parser.
s=(ref.parent/'kernel79/validate-pageflip.py').read_text().replace('kernel79','kernel81')
s=s.replace("'pageflip.txt'","'pageflip-after-timeouts.txt'").replace("'pageflip-validation.json'","'pageflip-after-timeouts-validation.json'")
(ref/'validate-pageflip.py').write_text(s)
exec(compile(s,str(ref/'validate-pageflip.py'),'exec'))
rows=(out/'pageflip-after-timeouts.txt').read_text();assert 'tool_rc=0' in rows
result={'device_captures_sha256_verified':hashes,'private_raw_archive_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'existing_frame_done_timeout_timestamps_seconds':[1545.683499,1775.069790],'session80_raw_log_already_contains_both_timeouts':True,'session80_selected_log_pattern_check_missed_frame_timeouts':True,'frame_done_timeout_count_before_after_probe':2,'new_frame_done_timeouts_in_600_flip_probe':0,'underrun_before_after_probe':0,'explicit_panel_power_cycle':False,'new_optical_observation':False,'kernel_or_device_tree_change':False,'display_stability_fully_fixed':False,'cause_established':False,'idle_or_fbcon_update_path_hypothesis_only':True,'actual_driver_counter_is_timeout_count':True,'source_counter_reference':'drivers/gpu/drm/msm/disp/dpu1/dpu_encoder.c frame_done_timeout_cnt','tracing_facility_in_running_kernel_not_available_at_checked_paths':True}
(ref/'display-timeout-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS all 15 capture hashes, 600 event/CRC samples; existing two frame-done timeouts retained, zero added by probe; idle cause not established')
