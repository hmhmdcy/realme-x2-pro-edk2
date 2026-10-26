"""Remove the invalid PPS read from a mapping reserved for IPE top controls."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
k=m.mounted_build().parent/'source354';p=k/'drivers/media/platform/qcom/camss/camss-icp-a5-boot.c';git=lambda *a:subprocess.check_output(['git','-C',str(k),*a],text=True)
assert git('rev-parse','HEAD').strip()=='48f5717f0089580ac56d79a83d21c71ccd2e364a' and not git('status','--porcelain')
t=p.read_text();a=t.index('\t\tif (coarse)\n\t\t\tdev_info(a5->dev, "A5 IPE PD10 completed cores=');b=t.index('\n\t\tif (coarse && coarse->scratch_output)',a)
t=t[:a]+t[b:];assert 'readl(a5->resources.ipe[' not in t;p.write_text(t)
subprocess.run(['git','-C',str(k),'diff','--check'],check=True);subprocess.run(['git','-C',str(k),'add','--',str(p)],check=True)
subprocess.run(['git','-C',str(k),'commit','-m','media: camss: remove PPS diagnostic outside mapped IPE top window'],check=True)
state=json.loads((HERE/'source-state.json').read_text());state.update(commit=git('rev-parse','HEAD').strip(),
 temporary_read_only_final_ltm_control_diagnostic=False,unsafe_pps_mmio_diagnostic_removed=True,
 r3_diagnostic_caused_kernel_oops=True,one_core_hardware_functional_result_invalidated_by_diagnostic=True)
for row in state['source_hashes']:row['sha256']=hashlib.sha256((k/row['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');(HERE/'pd10-runtime.patch').write_text(git('diff',state['parent_commit'],'HEAD'));print(json.dumps(dict(commit=state['commit'],unsafe_diagnostic_removed=True)))
