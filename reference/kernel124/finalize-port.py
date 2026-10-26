from pathlib import Path
import runpy,difflib,json,hashlib
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'))
v=Path('/home/cy122/pmos-samurai-rootfs122');k=v/'camera124/kernel';base='drivers/media/platform/qcom/camss/'
def change(n,a,b,count=1):
 p=k/(base+n);t=p.read_text();assert t.count(a)==count,(n,a,t.count(a));p.write_text(t.replace(a,b))
change('camss-csiphy.h','const struct csiphy_lane_regs *cphy_regs;','const struct csiphy_lane_regs *cphy_regs[3];')
change('camss-csiphy.c','!csiphy->regs->cphy_regs','!csiphy->regs->cphy_regs[0]')
change('camss.c','if (is_cphy && fwnode_property_present(ep, "clock-lanes"))','if (is_cphy && (fwnode_property_present(ep, "clock-lanes") ||\n\t\t\tfwnode_property_present(ep, "lane-polarities")))')
change('camss-csiphy-3ph-1-0.c','ui = div_u64(1000000000000ULL, link_freq) / 2;','ui = div64_u64(1000000000000ULL, link_freq) / 2;')
change('camss-csiphy-3ph-1-0.c','csiphy->regs->cphy_regs + c->data[i].pos * size,','csiphy->regs->cphy_regs[c->data[i].pos],')
change('camss-csiphy-3ph-1-0.c','regs->cphy_regs = &lane_regs_sm8150_cphy[0][0];','regs->cphy_regs[0] = lane_regs_sm8150_cphy[0];\n\t\tregs->cphy_regs[1] = lane_regs_sm8150_cphy[1];\n\t\tregs->cphy_regs[2] = lane_regs_sm8150_cphy[2];')
report=json.loads((r/'reference/kernel124/cphy-port-validation.json').read_text());patch=''
for n in report['changed_files']:
 before=(v/'camera123/kernel'/n).read_text();after=(k/n).read_text();patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+n,tofile='b/'+n))
(r/'reference/kernel124/sm8150-cphy-power-7.3.patch').write_text(patch);report['patch_sha256']=hashlib.sha256(patch.encode()).hexdigest();(r/'reference/kernel124/cphy-port-validation.json').write_text(json.dumps(report,indent=2)+'\n')
for script in ['build-full.sh','package-candidate.sh']:
 t=(r/'reference/kernel123'/script).read_text().replace('123','124');(r/'reference/kernel124'/script).write_text(t)
print('CPHY124_BOUNDED_PORT_FINALIZED')
