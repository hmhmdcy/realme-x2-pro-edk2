"""Bounded, read-only bring-up diagnostics for the experimental DS4 output."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
k=m.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text());git=lambda *a:subprocess.check_output(['git','-C',str(k),*a],text=True)
assert git('rev-parse','HEAD').strip()==state['commit'] and not git('status','--porcelain') and json.loads((P/'intree-build-state.json').read_text())['terminal']
p=k/'drivers/media/platform/qcom/camss/camss-vfe-17x.c';t=p.read_text();a='\tif (status0 & STATUS_0_RESET_ACK)\n';assert t.count(a)==1
b='''	if (vfe->pixel175.ds4_running &&
	    vfe->line[VFE_LINE_PIX].output[0].sof_sequence < 4)
		dev_info(vfe->camss->dev,
			 "DS4 bringup irq top=%08x/%08x bus=%08x/%08x/%08x zoom=%08x wm=%08x/%08x/%08x\\n",
			 status0, status1, vfe_bus_status[0], vfe_bus_status[1],
			 vfe_bus_status[2], readl_relaxed(vfe->base + 0x4c),
			 readl_relaxed(vfe->base + 0x2508),
			 readl_relaxed(vfe->base + 0x2608),
			 readl_relaxed(vfe->base + 0x2708));

'''+a
t=t.replace(a,b);p.write_text(t)
subprocess.run(['git','-C',str(k),'add','--',str(p)],check=True);subprocess.run(['git','-C',str(k),'commit','-m','media: camss: trace bounded DS4 bring-up IRQ status'],check=True)
state['diagnostics_parent']=state['commit'];state['commit']=git('rev-parse','HEAD').strip()
for row in state['source_hashes']:row['sha256']=hashlib.sha256((k/row['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');(HERE/'ds4-dma.patch').write_text(git('diff',state['parent_commit'],'HEAD'));print(json.dumps(dict(commit=state['commit'])))
