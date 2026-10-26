from pathlib import Path
import runpy,re,json,hashlib,difflib
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));v=Path('/home/cy122/pmos-samurai-rootfs122');k=v/'camera125/kernel';out=Path('/mnt/e/edk2-samurai-out/kernel125');ref=r/'reference/kernel125'
assert k.is_dir() and not (ref/'sm8150-cpas-iova-7.3.patch').exists()
assert hashlib.sha256((v/'camera124/kernel/arch/arm64/boot/Image').read_bytes()).hexdigest()=='feb6bfdc7991d26c6278d7d38afba47e86ee04573c78699e9eb3f3ef526fd0c1'
changes={}
def once(t,a,b):assert t.count(a)==1,(a,t.count(a));return t.replace(a,b,1)
def edit(n,fn):
 p=k/n;before=p.read_text();after=fn(before);assert after!=before,n;changes[n]=(before,after)
def new(n,text):assert not (k/n).exists();changes[n]=('',text)
base='drivers/media/platform/qcom/camss/'
header='''/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef QC_CAMSS_CPAS_H
#define QC_CAMSS_CPAS_H
struct camss;
struct camss_cpas;
int camss_cpas_init(struct camss *camss);
int camss_cpas_resume(struct camss *camss);
void camss_cpas_suspend(struct camss *camss);
#endif
'''
qos=(out/'native-ife-qos-private.h').read_text()
code='''// SPDX-License-Identifier: GPL-2.0-only
/* SM8150 CPAS: own active camera_8150 v175_100/101 IFE QoS contract.
 * Native register tables Copyright (c) 2018 The Linux Foundation.
 */
#include <linux/clk.h>
#include <linux/io.h>
#include <linux/iommu.h>
#include <linux/platform_device.h>
#include "camss.h"
#include "camss-cpas.h"

#define SM8150_CPAS_CLOCKS 7

struct camss_cpas {
	void __iomem *top;
	void __iomem *noc;
	struct clk_bulk_data clocks[SM8150_CPAS_CLOCKS];
	bool enabled;
};

struct camss_cpas_reg {
	u32 offset;
	u32 mask;
	u32 value;
};

'''+qos+'''
static int camss_sm8150_check_iova(struct device *dev)
{
	struct iommu_domain *domain = iommu_get_domain_for_dev(dev);
	struct iommu_resv_region *region;
	bool low = false, high = false;
	LIST_HEAD(regions);

	if (!domain || (domain->type != IOMMU_DOMAIN_DMA &&
			domain->type != IOMMU_DOMAIN_DMA_FQ))
		return -ENODEV;
	iommu_get_resv_regions(dev, &regions);
	list_for_each_entry(region, &regions, list) {
		if (region->type != IOMMU_RESV_RESERVED)
			continue;
		if (region->start == 0 && region->length == 0x07400000)
			low = true;
		if (region->start == 0xe0000000 && region->length == 0x20000000)
			high = true;
	}
	iommu_put_resv_regions(dev, &regions);
	/* Do not replace the safe mask without both actual allocator reservations. */
	return low && high ? 0 : -EINVAL;
}

int camss_cpas_init(struct camss *camss)
{
	static const char * const names[] = {
		"gcc_camera_ahb", "gcc_camera_axi", "gcc_camera_sf_axi",
		"slow_ahb_src", "cpas_ahb", "camnoc_axi_src", "camnoc_axi"
	};
	struct device *dev = camss->dev;
	struct platform_device *pdev = to_platform_device(dev);
	struct resource *res;
	struct camss_cpas *cpas;
	int i, ret;

	if (camss->res->version != CAMSS_8150)
		return 0;
	ret = camss_sm8150_check_iova(dev);
	if (ret)
		return dev_err_probe(dev, ret, "native IFE IOVA reservations missing\\n");
	cpas = devm_kzalloc(dev, sizeof(*cpas), GFP_KERNEL);
	if (!cpas)
		return -ENOMEM;
	res = platform_get_resource_byname(pdev, IORESOURCE_MEM, "cpas_top");
	if (!res || resource_size(res) != 0x1000)
		return -EINVAL;
	cpas->top = devm_ioremap_resource(dev, res);
	if (IS_ERR(cpas->top))
		return PTR_ERR(cpas->top);
	res = platform_get_resource_byname(pdev, IORESOURCE_MEM, "camnoc");
	if (!res || resource_size(res) != 0x5000)
		return -EINVAL;
	cpas->noc = devm_ioremap_resource(dev, res);
	if (IS_ERR(cpas->noc))
		return PTR_ERR(cpas->noc);
	for (i = 0; i < ARRAY_SIZE(names); i++)
		cpas->clocks[i].id = names[i];
	ret = devm_clk_bulk_get(dev, ARRAY_SIZE(cpas->clocks), cpas->clocks);
	if (ret)
		return ret;
	camss->cpas = cpas;
	return 0;
}

int camss_cpas_resume(struct camss *camss)
{
	struct camss_cpas *cpas = camss->cpas;
	u32 camera, version, value;
	int i, ret;

	if (camss->res->version != CAMSS_8150)
		return 0;
	if (!cpas)
		return -ENODEV;
	ret = clk_set_rate(cpas->clocks[3].clk, 80000000);
	if (ret)
		return ret;
	/* Native CPAS minimum bandwidth vote: 3GB/s, 32-byte bus, margin. */
	ret = clk_set_rate(cpas->clocks[5].clk, 150000000);
	if (ret)
		return ret;
	ret = clk_bulk_prepare_enable(ARRAY_SIZE(cpas->clocks), cpas->clocks);
	if (ret)
		return ret;
	/* Top domain and interconnects are active before these ordered reads. */
	camera = readl(cpas->top) & 0xffffff;
	version = readl(cpas->top + 4);
	if (camera != 0x010705 || (version != 0x10000000 && version != 0x10000001)) {
		dev_err(camss->dev, "unsupported CPAS camera %#x revision %#x\\n",
			camera, version);
		ret = -EOPNOTSUPP;
		goto disable_clocks;
	}
	for (i = 0; i < ARRAY_SIZE(sm8150_ife_qos); i++) {
		const struct camss_cpas_reg *reg = &sm8150_ife_qos[i];

		value = reg->value;
		if (reg->mask != U32_MAX)
			value |= readl(cpas->noc + reg->offset) & ~reg->mask;
		writel(value, cpas->noc + reg->offset);
		if ((readl(cpas->noc + reg->offset) & reg->mask) != reg->value) {
			ret = -EIO;
			goto disable_clocks;
		}
	}
	cpas->enabled = true;
	return 0;

disable_clocks:
	clk_bulk_disable_unprepare(ARRAY_SIZE(cpas->clocks), cpas->clocks);
	return ret;
}

void camss_cpas_suspend(struct camss *camss)
{
	struct camss_cpas *cpas = camss->cpas;

	if (cpas && cpas->enabled) {
		clk_bulk_disable_unprepare(ARRAY_SIZE(cpas->clocks), cpas->clocks);
		cpas->enabled = false;
	}
}
'''
new(base+'camss-cpas.h',header);new(base+'camss-cpas.c',code)
edit(base+'Makefile',lambda t:once(t,'\t\tcamss.o \\','\t\tcamss.o \\\n\t\tcamss-cpas.o \\'))
edit(base+'camss.h',lambda t:once(t,'\tvoid __iomem *csid_wrapper_base;','\tvoid __iomem *csid_wrapper_base;\n\tstruct camss_cpas *cpas;'))
def main(t):
 t=once(t,'#include "camss.h"','#include "camss.h"\n#include "camss-cpas.h"')
 marker='\tret = camss_init_subdevices(camss);';t=once(t,marker,'\tret = camss_cpas_init(camss);\n\tif (ret)\n\t\tgoto err_genpd_cleanup;\n\n'+marker)
 a=t.index('\t/*\n\t * The native SM8150 IFE IOVA region');b=t.index('\n\tif (ret)',a)
 t=t[:a]+'''\t/* Full native IFE window is enforced by checked IOMMU reservations. */
	ret = dma_set_mask_and_coherent(dev, DMA_BIT_MASK(32));'''+t[b:]
 # Native minimum internal-CAMNOC IB; DDR votes retain current full-IFE basis.
 a=t.index('static const struct resources_icc icc_res_8150');b=t.index('\n};',a)+3;s=t[a:b];s=once(s,'.name = "cam_hf_0_camnoc",\n\t\t.icc_bw_tbl.avg = 2097152,\n\t\t.icc_bw_tbl.peak = 2097152,','.name = "cam_hf_0_camnoc",\n\t\t.icc_bw_tbl.avg = 2097152,\n\t\t.icc_bw_tbl.peak = 3000000,');t=t[:a]+s+t[b:]
 def replace_function(t,name,new):
  m=re.search(r'^static int __maybe_unused '+name+r'\(',t,re.M);assert m;b=t.index('{',m.end());i=b+1;d=1
  while d:d+=(t[i]=='{')-(t[i]=='}');i+=1
  return t[:m.start()]+new+t[i:]
 t=replace_function(t,'camss_runtime_resume','''static int __maybe_unused camss_runtime_resume(struct device *dev)
{
	struct camss *camss = dev_get_drvdata(dev);
	const struct resources_icc *icc_res = camss->res->icc_res;
	int i, ret;

	for (i = 0; i < camss->res->icc_path_num; i++) {
		ret = icc_set_bw(camss->icc_path[i],
				 icc_res[i].icc_bw_tbl.avg,
				 icc_res[i].icc_bw_tbl.peak);
		if (ret)
			goto clear_votes;
	}
	ret = camss_cpas_resume(camss);
	if (!ret)
		return 0;

clear_votes:
	/* Clear the successful prefix and the possibly partially failed vote. */
	for (i = 0; i < camss->res->icc_path_num; i++)
		if (icc_set_bw(camss->icc_path[i], 0, 0))
			dev_err(dev, "failed to unwind CAMSS interconnect vote\\n");
	return ret;
}''')
 t=replace_function(t,'camss_runtime_suspend','''static int __maybe_unused camss_runtime_suspend(struct device *dev)
{
	struct camss *camss = dev_get_drvdata(dev);
	const struct resources_icc *icc_res = camss->res->icc_res;
	int i, j, ret;

	for (i = 0; i < camss->res->icc_path_num; i++) {
		ret = icc_set_bw(camss->icc_path[i], 0, 0);
		if (ret) {
			/* PM keeps the device active after a failed suspend. */
			for (j = 0; j < camss->res->icc_path_num; j++)
				if (icc_set_bw(camss->icc_path[j],
					icc_res[j].icc_bw_tbl.avg, icc_res[j].icc_bw_tbl.peak))
					dev_err(dev, "failed to restore CAMSS interconnect vote\\n");
			return ret;
		}
	}
	camss_cpas_suspend(camss);
	return 0;
}''')
 return t
edit(base+'camss.c',main)
def dt(t):
 a=t.index('\t\tcamss: camss@');b=t.index('\t\tcamcc: clock-controller@',a);s=t[a:b]
 s=once(s,'<0 0x0acb6000 0 0x4000>;','<0 0x0acb6000 0 0x4000>,\n\t\t\t      <0 0x0ac40000 0 0x1000>,\n\t\t\t      <0 0x0ac42000 0 0x5000>;')
 na=s.index('reg-names');nb=s.index(';',na);names=s[na:nb];names=once(names,'"vfe1"','"vfe1", "cpas_top", "camnoc"');s=s[:na]+names+s[nb:]
 # Append native SF bridge and explicit CAMNOC AXI source clocks.
 s=once(s,'<&camcc CAM_CC_IFE_1_CLK_SRC>;','<&camcc CAM_CC_IFE_1_CLK_SRC>,\n\t\t\t\t <&gcc GCC_CAMERA_SF_AXI_CLK>,\n\t\t\t\t <&camcc CAM_CC_CAMNOC_AXI_CLK_SRC>;')
 s=once(s,'"vfe1_src";','"vfe1_src",\n\t\t\t\t      "gcc_camera_sf_axi", "camnoc_axi_src";')
 s=once(s,'\t\t\tstatus = "disabled";','\t\t\tmemory-region = <&camss_iova_resv>;\n\t\t\tmemory-region-names = "ife-iova";\n\t\t\tstatus = "disabled";')
 t=t[:a]+s+t[b:]
 # This fixed kernel and dtschema2026.9 implement no-reg IOVA carveouts.
 # It reserves no physical RAM. Future iommu-ranges migration is documented.
 marker='\treserved-memory {';node='''
		camss_iova_resv: reservation-camss-ife {
			iommu-addresses = <&camss 0 0 0 0x07400000>,
					  <&camss 0 0xe0000000 0 0x20000000>;
		};
''';assert t.count(marker)==1;ri=t.index(marker);rp=t.index('ranges;',ri)+len('ranges;');t=t[:rp]+node+t[rp:];return t
edit('arch/arm64/boot/dts/qcom/sm8150.dtsi',dt)
def schema(t):
 t=once(t,'minItems: 31\n    maxItems: 31','minItems: 33\n    maxItems: 33')
 t=once(t,'      - const: vfe1_src','      - const: vfe1_src\n      - const: gcc_camera_sf_axi\n      - const: camnoc_axi_src')
 assert t.count('minItems: 8\n    maxItems: 8')==3
 t=t.replace('  reg:\n    minItems: 8\n    maxItems: 8','  reg:\n    minItems: 10\n    maxItems: 10')
 t=once(t,'      - const: vfe1\n\n  interrupts:', '      - const: vfe1\n      - const: cpas_top\n      - const: camnoc\n\n  interrupts:')
 t=once(t,'  vdda-phy-supply:', '  memory-region:\n    maxItems: 1\n\n  memory-region-names:\n    items:\n      - const: ife-iova\n\n  vdda-phy-supply:')
 t=once(t,'  - interconnect-names\n','  - interconnect-names\n  - memory-region\n  - memory-region-names\n');return t
edit('Documentation/devicetree/bindings/media/qcom,sm8150-camss.yaml',schema)
# All replacement preconditions are checked before any source file is written.
patch=''
for n,(before,after) in changes.items():
 (k/n).write_text(after);patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+n if before else '/dev/null',tofile='b/'+n))
(ref/'sm8150-cpas-iova-7.3.patch').write_text(patch)
report=dict(candidate=125,base=124,changed_files=list(changes),patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),managed_cpas_mmio_resources=True,native_v175_100_101_ife_qos_10_updates=True,unknown_and_v120_rejected_before_qos=True,masked_urgency_preserves_unrelated_bits=True,readback_failure_unwinds_clocks_and_icc=True,native_full_iova_window=[0x07400000,0xe0000000],dma_bits=32,iommu_reservation_callback_policy_required_before_probe=True,opaque_dma_allocator_cookie_not_inspected=True,legacy_iommu_address_schema_fixed_to_2026_9=True,future_iommu_ranges_migration_pending=True,camss_still_disabled=True,phone_unchanged=True)
(ref/'cpas-iova-port-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
for n in ['build-full.sh','package-candidate.sh']:(ref/n).write_text((r/'reference/kernel124'/n).read_text().replace('124','125'))
