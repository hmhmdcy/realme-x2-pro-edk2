"""Clear the retired stream's software PIX RUP before initial parameters."""
from pathlib import Path
import importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('storage434fix',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);K=m.mounted_build().parent/'source354'
git=lambda *a:subprocess.check_output(['git','-C',str(K),*a],text=True).strip()
base='04f8c5a3c815e2fa4244564da108227561a0321b'
assert git('rev-parse','HEAD')==base and not git('status','--porcelain')
rel='drivers/media/platform/qcom/camss/camss-vfe-17x.c';p=K/rel
for d in [p.parent,*p.parents]:assert not (d/'AGENTS.md').exists()
old='''	/* Queued PIX parameters must override defaults before the first frame. */
	if (line->is_pix)
		vfe_params_apply_queued(vfe, line);
'''
new='''	/* Queued PIX parameters must override defaults before the first frame. */
	if (line->is_pix) {
		unsigned long flags;

		/* The stopped stream can leave its last RUP bit set. Retire it
		 * before GTM's defer check, otherwise the initial DS4/GTM packet
		 * waits for an ACK from a stream which no longer exists.
		 * The output is not ON yet; live-stream RUP ordering is unchanged.
		 */
		if (vfe->camss->res->version == CAMSS_8150) {
			spin_lock_irqsave(&vfe->output_lock, flags);
			vfe->res->hw_ops->reg_update_clear(vfe, line->id);
			spin_unlock_irqrestore(&vfe->output_lock, flags);
		}
		vfe_params_apply_queued(vfe, line);
	}
'''
text=p.read_text();assert text.count(old)==1
subprocess.run(['git','-C',str(K),'switch','-c','samurai-vfe175-gtm-reopen434'],check=True,capture_output=True)
p.write_text(text.replace(old,new));subprocess.run(['git','-C',str(K),'diff','--check'],check=True)
(HERE/'gtm-reopen.patch').write_text(subprocess.check_output(['git','-C',str(K),'diff','--',rel],text=True))
subprocess.run(['git','-C',str(K),'add','--',rel],check=True);subprocess.run(['git','-C',str(K),'commit','-m','media: camss: retire stopped PIX update before initial GTM packet'],check=True,capture_output=True)
r=dict(stage=434,parent_commit=base,commit=git('rev-parse','HEAD'),kernel_clean=not git('status','--porcelain'),files=[rel],passed=True)
(HERE/'source-state.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
