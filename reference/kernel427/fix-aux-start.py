from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);kernel=m.mounted_build().parent/'source354'
state=json.loads((HERE/'source-state.json').read_text());git=lambda *a:subprocess.check_output(['git','-C',str(kernel),*a],text=True)
assert git('rev-parse','HEAD').strip()==state['commit'] and not git('status','--porcelain')
assert json.loads((P/'intree-build-state.json').read_text())['terminal']
assert json.loads((HERE/'queue-negative-validation.json').read_text())['passed']
path=kernel/'drivers/media/platform/qcom/camss/camss-vfe.c';text=path.read_text()
old='\tif (!output->video_out.auxiliary && ops->vfe_output_start)\n\t\tops->vfe_output_start(vfe, output);\n\telse\n\t\tops->vfe_wm_start(vfe, output->wm[0].bus_client, line);'
new='''	if (!output->video_out.auxiliary) {
		if (ops->vfe_output_start)
			ops->vfe_output_start(vfe, output);
		else
			ops->vfe_wm_start(vfe, output->wm[0].bus_client, line);
	}'''
assert text.count(old)==1;path.write_text(text.replace(old,new))
subprocess.run(['git','-C',str(kernel),'add','--',str(path)],check=True);subprocess.run(['git','-C',str(kernel),'commit','-m','media: camss: defer both auxiliary start paths until DMA addresses exist'],check=True)
state['initial_aux_start_fix_parent']=state['commit'];state['commit']=git('rev-parse','HEAD').strip();state['legacy_rdi_fallback_start_fixed']=True
for row in state['source_hashes']:row['sha256']=hashlib.sha256((kernel/row['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');(HERE/'ds4-dma.patch').write_text(git('diff',state['parent_commit'],'HEAD'))
print(json.dumps(dict(commit=state['commit'],legacy_rdi_fallback_start_fixed=True)))
