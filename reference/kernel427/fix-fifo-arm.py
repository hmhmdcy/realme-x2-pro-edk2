"""Arm DS4's WM before pushing its FIFO, defer the register update until filled."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
k=m.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text());git=lambda *a:subprocess.check_output(['git','-C',str(k),*a],text=True)
assert git('rev-parse','HEAD').strip()==state['commit'] and not git('status','--porcelain') and json.loads((P/'intree-build-state.json').read_text())['terminal']
def replace(t,a,b):assert t.count(a)==1,a;return t.replace(a,b)
p=k/'drivers/media/platform/qcom/camss/camss-vfe.c';t=p.read_text()
a='''		output->gen2.active_num++;
		if (ops->vfe_output_update)'''
b='''		output->gen2.active_num++;
	}

	/* A disabled WM does not accept its address FIFO. Queue ownership is
	 * established first; arm the WM, fill its FIFO, then commit once. */
	if (output->video_out.auxiliary && output->gen2.active_num)
		ops->vfe_output_start(vfe, output);

	for (i = 0; i < output->gen2.active_num; i++) {
		if (ops->vfe_output_update)'''
t=replace(t,a,b)
t=replace(t,'''	if (output->video_out.auxiliary && output->gen2.active_num) {
		ops->vfe_output_start(vfe, output);
		ops->reg_update(vfe, line->id);
	}''','''	if (output->video_out.auxiliary && output->gen2.active_num)
		ops->reg_update(vfe, line->id);''')
a='''		output->buf[output->gen2.active_num++] = buf;
		if (ops->vfe_output_update)'''
b='''		output->buf[output->gen2.active_num++] = buf;
		if (vid->auxiliary && output->gen2.active_num == 1)
			ops->vfe_output_start(vfe, output);
		if (ops->vfe_output_update)'''
t=replace(t,a,b)
t=replace(t,'''		if (vid->auxiliary && output->gen2.active_num == 1)
			ops->vfe_output_start(vfe, output);
		ops->reg_update''','''		ops->reg_update''')
p.write_text(t)
p=k/'drivers/media/platform/qcom/camss/camss-vfe-175-ds4.c';t=p.read_text();t=replace(t,'/* The caller validated geometry and queued addresses before enabling. */','/* Buffer ownership is established before arming the address FIFO. */');p.write_text(t)
local=HERE/'ds4-runtime.c';local.write_text(local.read_text().replace('/* The caller validated geometry and queued addresses before enabling. */','/* Buffer ownership is established before arming the address FIFO. */'))
subprocess.run(['git','-C',str(k),'add','--','drivers/media/platform/qcom/camss/camss-vfe.c','drivers/media/platform/qcom/camss/camss-vfe-175-ds4.c'],check=True)
subprocess.run(['git','-C',str(k),'commit','-m','media: camss: arm DS4 WM before populating its address FIFO'],check=True)
state['fifo_arm_fix_parent']=state['commit'];state['commit']=git('rev-parse','HEAD').strip();state['wm_armed_before_fifo_addresses_then_single_commit']=True
for row in state['source_hashes']:row['sha256']=hashlib.sha256((k/row['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');(HERE/'ds4-dma.patch').write_text(git('diff',state['parent_commit'],'HEAD'));print(json.dumps(dict(commit=state['commit'])))
