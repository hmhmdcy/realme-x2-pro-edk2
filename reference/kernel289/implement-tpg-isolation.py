"""Keep gen2 internal TPG wire encoding independent of the last external PHY link."""
from pathlib import Path
import subprocess

TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')=='8c79b7e1912790d3e18a84c9c6621a6d92baa768' and not git('status','--porcelain')
subprocess.run(['git','-C',str(TREE),'switch','-c','samurai-tpg-gamma289'],check=True,capture_output=True)
p=TREE/'drivers/media/platform/qcom/camss/camss-csid-gen2.c';s=p.read_text()
old='''	u8 lane_cnt = csid->phy.lane_cnt;
	int val;

	if (!lane_cnt)
		lane_cnt = 4;

	val = (lane_cnt - 1) << CSI2_RX_CFG0_NUM_ACTIVE_LANES;
	val |= phy->lane_assign << CSI2_RX_CFG0_DL0_INPUT_SEL;
	val |= phy->csiphy_id << CSI2_RX_CFG0_PHY_NUM_SEL;
	val |= phy->is_cphy << CSI2_RX_CFG0_PHY_TYPE_SEL;'''
new='''	u8 lane_cnt = phy->lane_cnt;
	u32 val;

	if (csid->testgen.enabled) {
		/* The internal source emits four D-PHY lanes, not C-PHY trios. */
		val = 3 << CSI2_RX_CFG0_NUM_ACTIVE_LANES;
		val |= 0x3210 << CSI2_RX_CFG0_DL0_INPUT_SEL;
	} else {
		if (!lane_cnt)
			lane_cnt = 4;

		val = (lane_cnt - 1) << CSI2_RX_CFG0_NUM_ACTIVE_LANES;
		val |= phy->lane_assign << CSI2_RX_CFG0_DL0_INPUT_SEL;
		val |= phy->csiphy_id << CSI2_RX_CFG0_PHY_NUM_SEL;
		val |= phy->is_cphy << CSI2_RX_CFG0_PHY_TYPE_SEL;
	}'''
assert s.count(old)==1;s=s.replace(old,new)
old='\tu8 lane_cnt = csid->phy.lane_cnt;\n\tu32 val;'
assert s.count(old)==1;s=s.replace(old,'\tu32 val;')
old='\tif (!lane_cnt)\n\t\tlane_cnt = 4;\n'
assert s.count(old)==1;s=s.replace(old,'')
old='\tval |= (lane_cnt - 1) << TPG_CTRL_NUM_ACTIVE_LANES;'
assert s.count(old)==1;s=s.replace(old,'\tval |= 3 << TPG_CTRL_NUM_ACTIVE_LANES;')
p.write_text(s)
patch=subprocess.check_output(['git','-C',str(TREE),'diff','--',str(p)])
(Path(__file__).resolve().parent/'csid-gen2-tpg-isolation-candidate.patch').write_bytes(patch)
print('Gen2 internal TPG candidate saved; not deployed.')
