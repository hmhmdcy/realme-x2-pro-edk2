from pathlib import Path
import hashlib,json,re,tarfile,host

ref=Path(__file__).resolve().parent;out=host.PRIVATE
host.download('/var/lib/samurai/k200-export/export-summary.json',out/'native-export-summary-private.json');receipt=json.loads((out/'native-export-summary-private.json').read_text())
host.download('/var/lib/samurai/k200-export/evidence-private.tar.gz',out/'native-evidence-private.tar.gz');archive=out/'native-evidence-private.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()==receipt['archive_sha256']
with tarfile.open(archive) as tar:
 manifest=json.load(tar.extractfile('manifest-private.json'));assert len(manifest)==receipt['files']
 for name,digest in manifest.items():assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==digest
 def get(name):return json.load(tar.extractfile(name))
 full_quiesce=get('k200-quiesce/quiesce-validation.json');assert full_quiesce['quiesce_audit_pass'] and full_quiesce['taint']==512
 runtime=get('k200-runtime/summary.json');assert runtime['camss_four_domains_exact'] and runtime['boot_partition_readback_exact'] and runtime['paired_module_tree_784_files_exact']
 active_rates=[];raw_records=[];all_raw=[]
 for session in ['r1','r2']:
  base='k200-front-capture-'+session;front=get(base+'/summary.json')
  assert front['normal_driver_bound'] and front['physical_image_capture'] and front['no_external_performance_helper'] and front['no_clock_rate_cap'] and front['pmic_after_restore']==front['before']['pmic'] and front['camss_original_graph_restored'] and len(front['capture_cycles'])==len(front['idle_performance_dropped'])==2
  assert not any(front['fault_delta'].values()) and front['taint']==0
  if session=='r1':
   assert not front['pins_restored_exact'];restore=get(base+'/bias-restoration.json');assert restore['original_pull_restored_by_one_masked_mmio_write'] and restore['after']==1
  else:assert front['pins_restored_exact']
  for cycle in front['capture_cycles']:
   label=cycle['label'];assert cycle['active_performance_snapshot'];frames=cycle['frames'];assert len(frames)==3 and [f['sequence'] for f in frames]==[0,1,2] and all(f['bytes']==2628608 and f['active_bytes_changed']/f['active_bytes']>.999 for f in frames)
   assert all(a['timestamp_us']<b['timestamp_us'] for a,b in zip(frames,frames[1:]));log=tar.extractfile(base+'/'+label+'-capture-private.log').read().decode();assert 'PATTERNS sensor=0 csid=0 physical_link=enabled' in log
   pd=tar.extractfile(base+'/'+label+'-active-genpd-private.txt').read().decode();assert re.search(r'genpd:3:acb3000.camss\s+active\s+384\s',pd)
   clocks=tar.extractfile(base+'/'+label+'-active-clocks-private.txt').read().decode();rows={w[0]:w for l in clocks.splitlines() if (w:=l.split()) and w[0] in ['cam_cc_ife_0_clk','cam_cc_ife_0_csid_clk']};assert all(int(w[1])>0 and w[8]=='Y' for w in rows.values());assert int(rows['cam_cc_ife_0_clk'][4])>800000000 and int(rows['cam_cc_ife_0_csid_clk'][4])==600000000;active_rates.append(dict(vfe=int(rows['cam_cc_ife_0_clk'][4]),csid=int(rows['cam_cc_ife_0_csid_clk'][4])))
   idle=tar.extractfile(base+'/'+label+'-idle-genpd-private.txt').read().decode();assert re.search(r'genpd:3:acb3000.camss\s+suspended\s+0\s',idle)
   raw=tar.extractfile(base+'/'+label+'-first-frame-private.raw').read();assert len(raw)==2628608
   hist=[0]*1024;row_sums=[]
   for y in range(1088):
    row=raw[y*2416:y*2416+2410];total=0
    for x in range(0,2410,5):
     a,b,c,d,e=row[x:x+5]
     for v in [(a<<2)|(e&3),(b<<2)|((e>>2)&3),(c<<2)|((e>>4)&3),(d<<2)|((e>>6)&3)]:hist[v]+=1;total+=v
    row_sums.append(total)
   assert sum(hist)==1928*1088 and sum(n>0 for n in hist)>16 and len(set(row_sums))>1
   assert all(raw!=old for old in all_raw);all_raw.append(raw);raw_records.append(dict(session=session,label=label,raw_sha256=hashlib.sha256(raw).hexdigest(),histogram=hist,row_sums=row_sums))
 vio=get('k200-live-prepare-r2/vio-read-only-lookup.json');assert vio['before']==vio['after']==dict(state='unknown',microvolts='1800000',num_users='0') and vio['enable_state']==-22
 health=get('k200-final-health/summary.json');assert health['all_diagnostic_modules_unloaded'] and health['taint']==0 and not any(health['fault_counts'].values())
 peripheral=get('k200-peripheral-regression/summary.json');assert peripheral['bluetooth_discovery_stopped'] and peripheral['bluetooth_power_state_restored'] and not any(peripheral['fault_delta'].values())
 for name,data in [('native-health-validation.json',health),('peripheral-regression-validation.json',peripheral)]:
  (ref/name).write_text(json.dumps(data,indent=2)+'\n')
(out/'physical-raw-decode-private.json').write_text(json.dumps(raw_records,indent=2)+'\n')
r=dict(stage=200,new_static_mmcx_dt_and_persistent_module_boot_verified=True,physical_frames=12,capture_cycles=4,
 test_patterns_disabled=True,unmodified_frequency_tables=True,no_external_performance_helper=True,active_clock_rates=active_rates,
 own_mmcx_active_level=384,own_mmcx_idle_level=0,active_pixels_over99p9percent_changed=True,
 first_cleanup_mclk_pull_mismatch_and_single_masked_restoration_retained=True,final_sensor_overlay_preserves_fresh_boot_mclk_pull=True,
 final_pins_and_pmic_restored_exact=True,no_of_overlay_property_memory_warnings=True,new_kernel_warn_events=0,taint=0,
 four_saved_raw10_images_decoded_and_different=True,media_and_image_fingerprints_private=True,
 full_camera_function_not_yet_complete=True)
(ref/'front-native-validation.json').write_text(json.dumps(r,indent=2)+'\n')
public={k:v for k,v in receipt.items() if k!='archive_sha256'};public.update(host_archive_sha256_verified=True,all_member_hashes_verified=True,archive_and_image_fingerprints_private=True,contains_four_private_physical_raw_frames=True,initial_failed_attempts_retained=True)
(ref/'evidence-export-validation.json').write_text(json.dumps(public,indent=2)+'\n');print(json.dumps(public))
