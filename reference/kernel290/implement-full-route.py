"""Route FULL output through its crop/round/clamp block, retaining uncropped geometry."""
from pathlib import Path
import subprocess

TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel');ROOT=Path(__file__).resolve().parent
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')=='ff8d2e9fc04ef92407ff83c40c4e059eb620f0f7' and not git('status','--porcelain')
subprocess.run(['git','-C',str(TREE),'switch','-c','samurai-full-route290'],check=True,capture_output=True)
p=TREE/'drivers/media/platform/qcom/camss/camss-vfe-175-round.c';s=p.read_text()
s=s.replace('#define VFE_175_FULL_Y_ENABLE', '#define VFE_175_FRAME_ENABLE\t\t0x04c\n#define VFE_175_FRAME_FULL_POST_PROCESS\tBIT(4)\n#define VFE_175_FULL_Y_ENABLE',1)
needle='\tvfe_175_round_write(vfe, VFE_175_FULL_C_ENABLE, VFE_175_FULL_DEPTH_ENABLE, enabled);'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
	/* Route FULL through crop/round/clamp, even for the uncropped image. */
	wmb();
	vfe_175_round_write(vfe, VFE_175_FRAME_ENABLE,
			    VFE_175_FRAME_FULL_POST_PROCESS,
			    config->enabled ? VFE_175_FRAME_FULL_POST_PROCESS : 0);''')
needle='\tvfe_175_round_write(vfe, VFE_175_FULL_Y_ENABLE, VFE_175_FULL_DEPTH_ENABLE, 0);'
assert s.count(needle)==1
s=s.replace(needle,'''\tvfe_175_round_write(vfe, VFE_175_FRAME_ENABLE,
			    VFE_175_FRAME_FULL_POST_PROCESS, 0);
'''+needle)
p.write_text(s)
(ROOT/'vfe175-full-route-candidate.patch').write_bytes(subprocess.check_output(['git','-C',str(TREE),'diff','--',str(p)]))
print('FULL postprocessing route candidate saved; no CST fields, matrices, tuning, DT or userspace changes.')
