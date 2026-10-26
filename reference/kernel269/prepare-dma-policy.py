"""Keep handset IOVA reservations in DT and use the standard IOMMU/DMA path."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269');U=Path('/home/cy122/x2pro-linux/upstream')
G=['git','-c','safe.directory='+str(U),'-C',str(U)]
def git(*args):return subprocess.check_output(G+list(args),text=True).rstrip()
assert not git('status','--porcelain') and git('rev-parse','HEAD')==json.loads((R/'cleanup-validation.json').read_text())['commit']
names=['drivers/media/platform/qcom/camss/camss-cpas.c','drivers/media/platform/qcom/camss/camss-video.c',
 'drivers/media/platform/qcom/camss/camss.c','arch/arm64/boot/dts/qcom/sm8150.dtsi','arch/arm64/boot/dts/qcom/sm8150-samurai.dts']
before={n:(U/n).read_text() for n in names}
backup=P/'dma-policy-before';backup.mkdir(mode=0o700)
for n,s in before.items():(backup/Path(n).name).write_text(s)
def change(s,old,new):assert s.count(old)==1,(old[:80],s.count(old));return s.replace(old,new,1)
s=before[names[0]];a=s.index('static int camss_sm8150_check_iova(');b=s.index('static int camss_cpas_stop(',a)
s=s[:a]+'''/* The DMA/IOMMU core reserves the IOVA regions described by firmware. */
static int camss_cpas_check_dma_domain(struct device *dev)
{
	struct iommu_domain *domain = iommu_get_domain_for_dev(dev);

	if (!domain || (domain->type != IOMMU_DOMAIN_DMA &&
			domain->type != IOMMU_DOMAIN_DMA_FQ))
		return -ENODEV;

	return 0;
}

'''+s[b:]
s=change(s,'camss_sm8150_check_iova(dev)','camss_cpas_check_dma_domain(dev)')
s=change(s,'"native IFE IOVA reservations missing\\n"','"translated DMA domain is required\\n"');(U/names[0]).write_text(s)
s=before[names[1]];s=change(s,'#include <linux/module.h>','#include <linux/dma-mapping.h>\n#include <linux/module.h>')
s=change(s,'''/* Bounded bring-up diagnostics; normal camera operation stays quiet. */
static bool trace_dma;
module_param_named(dma_trace, trace_dma, bool, 0600);
MODULE_PARM_DESC(dma_trace, "Log prepared SM8150 DMA plane ranges");

''','')
s=change(s,'\tsize_t remaining = size;','\tsize_t remaining = size;\n\tu64 limit = dma_get_mask(video->camss->dev);')
s=change(s,'''\tif (address < 0x07400000 || address >= 0xe0000000 ||
\t    size > 0xe0000000 - address)''','''\tif (address > limit || size - 1 > limit - address)''')
s=change(s,'''\t\tif (trace_dma && video->camss->res->version == CAMSS_8150)
\t\t\tdev_info(video->camss->dev, "DMA plane %u address %pad size %lu\\n",
\t\t\t\ti, &buffer->addr[i], vb2_plane_size(vb, i));''','''\t\tdev_dbg(video->camss->dev, "DMA plane %u address %pad size %lu\\n",
\t\t\ti, &buffer->addr[i], vb2_plane_size(vb, i));''');(U/names[1]).write_text(s)
s=change(before[names[2]],'/* Full native IFE window is enforced by checked IOMMU reservations. */',
 '/* Hardware address width; IOVA reservations come from firmware data. */');(U/names[2]).write_text(s)
reservation='''\t\tcamss_iova_resv: reservation-camss-ife {
\t\t\tiommu-addresses = <&camss 0 0 0 0x07400000>,
\t\t\t\t\t  <&camss 0 0xe0000000 0 0x20000000>;
\t\t};
'''
s=change(before[names[3]],reservation,'');s=change(s,'\t\t\tmemory-region = <&camss_iova_resv>;\n\t\t\tmemory-region-names = "ife-iova";\n','');(U/names[3]).write_text(s)
s=change(before[names[4]],'\treserved-memory {\n','\treserved-memory {\n\t\t/* RMX1931 firmware IFE exclusions, enforced by the IOMMU core. */\n'+reservation+'\n')
s+='\n&camss {\n\tmemory-region = <&camss_iova_resv>;\n\tmemory-region-names = "ife-iova";\n};\n';(U/names[4]).write_text(s)
for n in names[:3]:assert '0x07400000' not in (U/n).read_text() and '0xe0000000' not in (U/n).read_text()
subprocess.run(G+['diff','--check'],check=True)
out=R/'source';out.mkdir()
for n in names:(out/Path(n).name).write_bytes((U/n).read_bytes())
report=dict(stage=269,files_sha256={n:hashlib.sha256((U/n).read_bytes()).hexdigest() for n in names},
 handset_iova_numbers_only_in_board_dt=True,same_reservation_values_and_memory_region_reference=True,
 generic_iommu_dma_reservation_path_unchanged=True,translated_dma_domain_still_required=True,
 full_plane_dma_mask_and_sg_contiguity_guard=True,custom_dma_trace_parameter_replaced_with_dynamic_debug=True,
 candidate_not_built_or_deployed=True)
(R/'dma-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
