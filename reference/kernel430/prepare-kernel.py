"""Select the recovered PPS topology and serialize its implicit coarse output."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage430',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
k=storage.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(k),*a],text=True)
parent='91be804b74c12288d1de0f7f8a5488c9687d8a47';assert git('rev-parse','HEAD').strip()==parent and not git('status','--porcelain')
subprocess.run(['git','-C',str(k),'switch','-c','samurai-ipe-dc-topology430'],check=True)
d=k/'drivers/media/platform/qcom/camss';names=['camss-icp-a5-boot.c','camss-icp-a5-ipe.c']
p=d/names[0];t=p.read_text();a='\t\tput_unaligned_le32(coarse->slice_height, image + 56);';assert t.count(a)==1
t=t.replace(a,a+'''
		/* Stock PPS-only multipass topology. Without it the native scheduler
		 * can discard the DC stripe when no NPS output is requested.
		 */
		put_unaligned_le32(3, output + 1200);''');p.write_text(t)
p=d/names[1];t=p.read_text();a='\tltm_coarse_axis(output + 24, 120, 108, false);';assert t.count(a)==1
t=t.replace(a,a+'''
	/* The PPS topology owns an implicit PD10 intermediate in scratch.
	 * Describe its Y/chroma write extent as well as the LTM DC geometry;
	 * an empty write extent makes the native distributor drop this stripe.
	 */
	put_unaligned_le16(119, output + 24 + 270);
	put_unaligned_le16(59, output + 24 + 274);
	put_unaligned_le16(119, output + 24 + 376);''')
a='\tput_unaligned_le16(159, output + 2268 + 6);';assert t.count(a)==1
t=t.replace(a,a+'''
	put_unaligned_le16(159, output + 2268 + 30);
	put_unaligned_le16(159, output + 2268 + 318);
	put_unaligned_le16(159, output + 2268 + 322);''');p.write_text(t)
subprocess.run(['git','-C',str(k),'diff','--check'],check=True)
subprocess.run(['git','-C',str(k),'add','--',*[str(d/n) for n in names]],check=True)
subprocess.run(['git','-C',str(k),'commit','-m','media: camss: preserve LTM DC stripe in PPS multipass topology'],check=True)
state=dict(stage=430,parent_commit=parent,commit=git('rev-parse','HEAD').strip(),branch=git('branch','--show-current').strip(),
 source_hashes=[dict(path=str((d/n).relative_to(k)),sha256=hashlib.sha256((d/n).read_bytes()).hexdigest()) for n in names],
 same_user_abi_and_dma_ownership=True,board_dt_sensor_and_power_policy_unchanged=True,unsafe_mmio_diagnostic_absent=True,installed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');(HERE/'dc-topology.patch').write_text(git('diff',parent,'HEAD'))
# Reuse the existing actual-C/architecture checks with the recovered IO topology.
text=(HERE.parent/'kernel429/check-runtime.py').read_text().replace("(HERE/'runtime-contract.c')","(HERE.parent/'kernel429/runtime-contract.c')")
text=text.replace("config=(P.parent/'kernel425/width-640-dc-1-config-private.bin').read_bytes();", "config=bytearray((P.parent/'kernel425/width-640-dc-1-config-private.bin').read_bytes());struct.pack_into('<I',config,1200,3);config=bytes(config);")
text=text.replace('stage=429','stage=430').replace('scratch_bytes=meta[\'required_scratch_bytes\']','scratch_bytes=meta[\'required_scratch_bytes\']')
(HERE/'check-runtime.py').write_text(text)
(HERE/'build-intree.py').write_text((HERE.parent/'kernel429/build-intree.py').read_text().replace('stage=429','stage=430'))
print(json.dumps(state,indent=2))
