from pathlib import Path
import ast,hashlib,json,subprocess,tarfile
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel156')
base=ref.parent/'kernel155'
out=Path('/mnt/e/edk2-samurai-out/kernel156')
for name in ['collect-preflash.py','quiesce-current154.sh','check-quiesce.py','freeze-for-bootloader.sh',
    'enter-bootloader.ps1','capture-startup.py','k155-startup-trace','display-power.py','capture-display-cycles.py']:
    s=(base/name).read_text().replace('kernel155','kernel156').replace('k155','k156').replace('K155','K156')
    s=s.replace('stage=155','stage=156').replace('target_kernel=154','target_kernel=156')
    if name in ['capture-startup.py','k155-startup-trace']:
        s=s.replace("'#154 '","'#156 '").replace("'^#154 '","'^#156 '").replace('kernel_build=154','kernel_build=156')
    if name in ['capture-startup.py','capture-display-cycles.py']:
        marker="events=[('drm_msm_dsi',n)" if name=='capture-startup.py' else "events = [('drm_msm_dsi', n)"
        assert marker in s
        old="events += [('dpu',n) for n in ['dpu_enc_frame_watchdog'" if name=='capture-startup.py' else "events += [('dpu', n) for n in ['dpu_enc_frame_watchdog'"
        assert old in s
        s=s.replace(old,("events += [('drm_panel','drm_panel_backlight'),('dpu','dpu_first_frame_backlight')]\n" if name=='capture-startup.py' else
            "events += [('drm_panel','drm_panel_backlight'),('dpu','dpu_first_frame_backlight')]\n")+old,1)
    dest=ref/name.replace('k155-startup','k156-startup')
    assert not dest.exists(),dest
    dest.write_text(s)
    if dest.suffix=='.py':ast.parse(s)
    if dest.suffix=='.sh' or name=='k155-startup-trace':subprocess.run(['sh','-n',str(dest)],check=True)
# Reuse the verified #154 deployment procedure with fresh #155-source guards.
for name in ['flash-host-init-candidate.ps1','poll-first-boot.ps1','verify-runtime.py']:
    s=(ref.parent/'kernel154'/name).read_text().replace('kernel154','kernel156').replace('k154','k156').replace('K154','K156')
    s=s.replace("'#154 '","'#156 '").replace("'#154 *'","'#156 *'")
    s=s.replace('New154','New156').replace('stage=154','stage=156').replace('kernel_build=154','kernel_build=156')
    s=s.replace('$q.current_kernel -ne 153','$q.current_kernel -ne 154').replace('$q.target_kernel -ne 154','$q.target_kernel -ne 156')
    s=s.replace('logdump-k156-host-init.img','logdump-k156-first-frame.img').replace('host-init-first','first-frame-first')
    s=s.replace('!$build.modules770_byte_identical132','!$build.modules132_runtime_compatible')
    dest=ref/name.replace('flash-host-init','flash-first-frame')
    assert not dest.exists(),dest;dest.write_text(s)
    if dest.suffix=='.py':ast.parse(s)
files=['collect-preflash.py','quiesce-current154.sh','check-quiesce.py','freeze-for-bootloader.sh',
    'capture-startup.py','k156-startup-trace','display-power.py','capture-display-cycles.py','verify-runtime.py','install-early-greetd.py']
with tarfile.open(out/'deployment-tools-private.tar','w') as tar:
    for name in files:tar.add(ref/name,arcname=name)
    tar.add(ref/'build-package-validation.json',arcname='build-package-validation.json')
result=dict(stage=156,kernel_build=156,source_kernel=154,metadata_dependency_included=True,
    module_reuse_compatibility_gate=True,first_frame_events_enabled=True,
    archive_sha256=hashlib.sha256((out/'deployment-tools-private.tar').read_bytes()).hexdigest())
(ref/'deployment-tools-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
