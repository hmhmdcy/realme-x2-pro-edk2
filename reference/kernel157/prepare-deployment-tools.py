from pathlib import Path
import ast,hashlib,json,tarfile
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel157');out=Path('/mnt/e/edk2-samurai-out/kernel157')
old=ref.parent/'kernel156'
names=['collect-preflash.py','quiesce-current154.sh','check-quiesce.py','freeze-for-bootloader.sh','enter-bootloader.ps1',
    'capture-startup.py','k156-startup-trace','display-power.py','capture-display-cycles.py','verify-runtime.py',
    'flash-first-frame-candidate.ps1','poll-first-boot.ps1']
for name in names:
    s=(old/name).read_text().replace('kernel156','kernel157').replace('k156','k157').replace('K156','K157')
    if name in ['collect-preflash.py','quiesce-current154.sh','check-quiesce.py','freeze-for-bootloader.sh']:
        s=s.replace('#154 ','#156 ').replace('CURRENT154','CURRENT156')
        s=s.replace('current_kernel=154','current_kernel=156').replace('target_kernel=156','target_kernel=157').replace('stage=156','stage=157')
    else:
        s=s.replace('#156 ','#157 ').replace('#156 *','#157 *').replace('New156','New157')
        s=s.replace('stage=156','stage=157').replace('kernel_build=156','kernel_build=157')
    if name=='flash-first-frame-candidate.ps1':
        s=s.replace('$q.current_kernel -ne 154','$q.current_kernel -ne 156').replace('$q.target_kernel -ne 156','$q.target_kernel -ne 157')
        s=s.replace('logdump-k157-first-frame.img','logdump-k157-early-stop.img').replace('first-frame-first','early-stop-first')
    if name=='enter-bootloader.ps1':s=s.replace("$Prefix='host-init-first'","$Prefix='early-stop-first'")
    if name=='capture-startup.py':
        s=s.replace("events += [('irq',n) for n in ['irq_handler_entry','irq_handler_exit','softirq_entry','softirq_exit']]\n",'')
        s=s.replace("events += [('power','cpu_idle'),('power','cpu_frequency')]\n",'')
    dest=ref/name.replace('quiesce-current154','quiesce-current156').replace('k156-startup','k157-startup').replace('flash-first-frame','flash-early-stop')
    assert not dest.exists();dest.write_text(s)
    if dest.suffix=='.py':ast.parse(s)
files=['collect-preflash.py','quiesce-current156.sh','check-quiesce.py','freeze-for-bootloader.sh',
    'capture-startup.py','k157-startup-trace','display-power.py','capture-display-cycles.py','verify-runtime.py']
with tarfile.open(out/'deployment-tools-private.tar','w') as t:
    for name in files:t.add(ref/name,arcname=name)
    t.add(ref/'build-package-validation.json',arcname='build-package-validation.json')
result=dict(stage=157,source_kernel=156,kernel_build=157,metadata_dependency_included=True,
    focused_dpu_dsi_panel_events=True,high_volume_generic_irq_and_cpu_events_removed=True,
    archive_sha256=hashlib.sha256((out/'deployment-tools-private.tar').read_bytes()).hexdigest())
(ref/'deployment-tools-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
