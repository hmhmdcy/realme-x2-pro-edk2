from pathlib import Path
import tarfile,json,hashlib,re
out=Path('/mnt/e/edk2-samurai-out/kernel147'); ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel147')
labels=dict(aligned147=8,control147=4,novbo147=2,nearest147=3,linear147=3,stressbuild147=2,stresstexture147=2,stressphong147=2)
reports={}; boot_ids=set(); trace_events={}; verified_files=0
for label,expected in labels.items():
    archive=out / (label+'-private.tar.gz')
    with tarfile.open(archive) as t:
        data={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
    for line in data['SHA256SUMS'].decode().splitlines():
        digest,name=line.split('  ',1)
        assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
        verified_files+=1
    host=(out / (label+'-host-private.log')).read_text()
    assert 'ARCHIVE_SHA256 '+hashlib.sha256(archive.read_bytes()).hexdigest() in host
    r=json.loads(data['result.json']); reports[label]=r
    assert not r['error'] and r['kernel']=='#147' and r['taint']=='0'
    assert r['desktop_preserved'] and r['packages_preserved'] and r['trace_removed']
    assert len(r['results'])==expected and r['debug']==''
    assert all(r['before'][key]==r['after'][key]==0 for key in ['gpu_faults','warnings','dpu_timeouts','dsi_errors','dma_prepare'])
    assert all(x['exit']==0 and x['renderer_fd640'] for x in r['results'])
    bench=r.get('benchmark_only',False)
    assert all(x['benchmark_completed'] if bench else x['pixel_success'] for x in r['results'])
    for case in r['results']:
        pixel=data['pixel-%02d.txt'%case['index']].decode()
        actual=re.search(r'Actual FBO Size:\s*(\d+)x(\d+)',pixel)
        assert actual and tuple(map(int,actual.groups()))==((1080,2259) if bench else (800,600))
    boot_ids.add(data['boot-id-private.txt'])
    trace=data['submission-trace-private.txt'].decode()
    events={n:len(re.findall(r'\b'+n+':',trace)) for n in ['msm_gpu_submit','msm_gpu_submit_flush','msm_gpu_submit_retired']}
    assert events['msm_gpu_submit']>0 and events['msm_gpu_submit_retired']>0
    stats=json.loads(data['trace-stats-private.json'])
    assert all(re.search(r'(?m)^overrun:\s*0\s*$',s) and re.search(r'(?m)^dropped events:\s*0\s*$',s) for s in stats.values())
    trace_events[label]=events
assert len(boot_ids)==1
assert json.loads((ref / 'gmem-command-validation.json').read_text())['candidate_default_gmem_confirmed']
report=dict(stage=147,device_fix_accepted=True,scope='A640 legacy kernel-managed private GPU VM, GLES default GMEM rendering',pixel_validations=20,sustained_render_runs=6,total_process_exits=26,same_boot=True,zero_gpu_faults=True,taint=0,zero_warnings=True,zero_dpu_dsi_errors=True,zero_dma_prepare=True,desktop_preserved=True,default_driver_settings=True,delayed_observation_seconds=[35,40,90],all_archive_sha256_and_members_verified=True,verified_evidence_files=verified_files,trace_events=trace_events,trace_drops=0,rd_alignment_confirmed=True,unverified_scope=['Vulkan user-managed VM_BIND','Other Adreno models','Other display/audio/charging adaptation issues'])
report['pixel_validation_fbo']=[800,600]
report['sustained_draw_fbo']=[1080,2259]
(ref / 'gpu-regression-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(out / 'regression-verified-private.json').write_text(json.dumps(reports,indent=2)+'\n')
print('K147_26_DEFAULT_GMEM_RUNS_ARCHIVES_AND_TRACES_VERIFIED')
