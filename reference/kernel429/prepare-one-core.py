"""Native-supported core-count isolation, with read-only final LTM control."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
k=m.mounted_build().parent/'source354';d=k/'drivers/media/platform/qcom/camss';git=lambda *a:subprocess.check_output(['git','-C',str(k),*a],text=True)
assert git('rev-parse','HEAD').strip()=='2e199f338780c1508a95bd69485ad198a17b3487' and not git('status','--porcelain')
assert json.loads((HERE/'runtime-r2-validation.json').read_text())['state']['terminal']
assert json.loads((HERE/'one-core-oracle-validation.json').read_text())['passed']
p=d/'camss-icp-a5-ipe.c';t=p.read_text();a='io->output_port != 8 || io->input.uv_swap || cores != 2)';assert t.count(a)==1;t=t.replace(a,'io->output_port != 8 || io->input.uv_swap || (cores != 1 && cores != 2))');p.write_text(t)
p=d/'camss-icp-a5-m2m.c';t=p.read_text();a='.bl_bytes = 512 * 1024, .max_cores = 2,';assert t.count(a)==1;t=t.replace(a,'.bl_bytes = 512 * 1024, .max_cores = ctx->coarse ? 1 : 2,');p.write_text(t)
p=d/'camss-icp-a5-boot.c';t=p.read_text();a='\t\ta5->frames_completed++;\n\t\tdma_rmb();';assert t.count(a)==1;t=t.replace(a,'''\t\ta5->frames_completed++;
		dma_rmb();
		if (coarse)
			dev_info(a5->dev, "A5 IPE PD10 completed cores=%u LTM=%08x/%08x\\n",
				 job->max_cores, readl(a5->resources.ipe[0] + 0x5c60),
				 readl(a5->resources.ipe[1] + 0x5c60));''');p.write_text(t)
subprocess.run(['git','-C',str(k),'diff','--check'],check=True)
subprocess.run(['git','-C',str(k),'add','--',*[str(d/n) for n in ['camss-icp-a5-ipe.c','camss-icp-a5-m2m.c','camss-icp-a5-boot.c']]],check=True)
subprocess.run(['git','-C',str(k),'commit','-m','media: camss: isolate PD10 two-pass collection to one IPE core'],check=True)
state=json.loads((HERE/'source-state.json').read_text());state.update(commit=git('rev-parse','HEAD').strip(),
 native_two_pass_initial_scope='640x480 NV12, display8, cores1/2 encoder; m2m coarse isolates core1',
 two_core_replay_complete_but_statistics_and_repeatability_failed=True,temporary_read_only_final_ltm_control_diagnostic=True)
for row in state['source_hashes']:row['sha256']=hashlib.sha256((k/row['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');(HERE/'pd10-runtime.patch').write_text(git('diff',state['parent_commit'],'HEAD'));print(json.dumps(state,indent=2))
