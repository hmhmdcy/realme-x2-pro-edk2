"""Integrate the normal ICP owner into CAMSS; prepare static SoC/board data."""
from pathlib import Path
import difflib,hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
source=m.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
parent='95caf30a629bbaf454ebfc9ed25ce16ea3a952b5';assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
relative='drivers/media/platform/qcom/camss/';after={}
def edit(name,a,b):
 path=relative+name;s=after.get(path,(source/path).read_text());assert s.count(a)==1,(name,a);after[path]=s.replace(a,b)
after[relative+'camss-icp-platform.c']=(HERE/'camss-icp-platform.c').read_text()
edit('camss-icp-a5-m2m.h','bool (*bound)(void)','bool (*bound)(struct device *dev)')
edit('camss-icp-a5-m2m.c','bool (*bound)(void);','bool (*bound)(struct device *dev);')
assert after[relative+'camss-icp-a5-m2m.c'].count('dev->bound()')==2
after[relative+'camss-icp-a5-m2m.c']=after[relative+'camss-icp-a5-m2m.c'].replace('dev->bound()','dev->bound(dev->a5->dev)')
edit('camss-icp-a5-m2m.c','bool (*bound)(void))','bool (*bound)(struct device *device))')
edit('camss-icp-a5-m2m.c','!a5 || !owner || !firmware','!a5 || !firmware')
edit('camss-icp-a5-m2m.c','module_refcount(dev->owner), dev->first_error,','dev->owner ? module_refcount(dev->owner) : 0, dev->first_error,')
edit('camss-icp-a5-boot-test.c','static bool m2m_bound(void)','static bool m2m_bound(struct device *dev)')
edit('camss.c','\t\t.pm = &camss_pm_ops,','\t\t.pm = &camss_pm_ops,\n\t\t/* Static ICP DMA backing pins this shared module owner. */\n\t\t.suppress_bind_attrs = IS_ENABLED(CONFIG_VIDEO_QCOM_CAMSS_ICP),')
edit('camss.c','module_platform_driver(qcom_camss_driver);','''#if IS_ENABLED(CONFIG_VIDEO_QCOM_CAMSS_ICP)
extern struct platform_driver camss_icp_driver;
#endif

static struct platform_driver * const camss_drivers[] = {
	&qcom_camss_driver,
#if IS_ENABLED(CONFIG_VIDEO_QCOM_CAMSS_ICP)
	&camss_icp_driver,
#endif
};

static int __init camss_init(void)
{
	return platform_register_drivers(camss_drivers, ARRAY_SIZE(camss_drivers));
}
module_init(camss_init);

static void __exit camss_exit(void)
{
	platform_unregister_drivers(camss_drivers, ARRAY_SIZE(camss_drivers));
}
module_exit(camss_exit);''')
after[relative+'Makefile']=(source/relative/'Makefile').read_text()+'\nqcom-camss-$(CONFIG_VIDEO_QCOM_CAMSS_ICP) += camss-icp-platform.o\n'
after[relative+'Kconfig']=(source/relative/'Kconfig').read_text()+'''
config VIDEO_QCOM_CAMSS_ICP
	bool "Qualcomm SM8150 ICP/IPE support"
	depends on VIDEO_QCOM_CAMSS && IOMMU_DMA && OF && PM && PM_GENERIC_DOMAINS && RESET_CONTROLLER
	select VIDEO_QCOM_CAMSS_ICP_A5_CORE if VIDEO_QCOM_CAMSS
	select VIDEO_QCOM_CAMSS_ICP_A5_M2M if VIDEO_QCOM_CAMSS
	help
	  Register the SM8150 ICP/IPE platform driver in the CAMSS module.
	  Firmware and frame processing start when V4L2 queues have work.
	  Open streams, exported buffers and retained DMA pin the shared
	  CAMSS/ICP module owner. These static devices do not expose manual
	  driver unbind. Board firmware RAM and IOVA reservations are required.
'''
path='arch/arm64/boot/dts/qcom/sm8150.dtsi';s=(source/path).read_text()
old='\t\t\tiommus = <&apps_smmu 0x2222 0>;';assert s.count(old)==1
specs=[(0x2222,0),(0x2080,0x20),(0x20a0,0x20),(0x2100,0x20),(0x2120,0x20),(0x20c0,0),(0x2140,0)]
s=s.replace(old,'\t\t\tiommus = '+',\n\t\t\t\t '.join(f'<&apps_smmu {sid:#x} {mask:#x}>' for sid,mask in specs)+';')
s=s.replace('/* A5 firmware backend; board memory and a driver are needed to enable it. */','/* A5 and its BPS/IPE engines share a firmware-managed DMA domain. */')
after[path]=s
path='arch/arm64/boot/dts/qcom/sm8150-samurai.dts';s=(source/path).read_text()
old='''/* Original 19781 board reservation. The unvalidated ICP backend stays dormant. */
&camss_icp {
	memory-region = <&camera_mem>;
	memory-region-names = "firmware";
};''';assert s.count(old)==1
s=s.replace(old,'''/* The physical firmware RAM remains the original 19781 camera reservation.
 * Address-only reservations below describe the A5 firmware IOVA ABI, not RAM.
 */
&camss_icp {
	status = "okay";
	firmware-name = "qcom/sm8150/camera-icp.elf";
	memory-region = <&camera_mem>, <&icp_fw_iova>, <&icp_shared_iova>,
			<&icp_heap_iova>, <&icp_trace_iova>, <&icp_images_iova>;
	memory-region-names = "firmware", "firmware-iova", "shared", "heap", "trace", "images";
};

&{/reserved-memory} {
	icp_fw_iova: reservation-icp-firmware {
		iommu-addresses = <&camss_icp 0 0 0 0x00500000>;
	};
	icp_shared_iova: reservation-icp-shared {
		iommu-addresses = <&camss_icp 0 0x07400000 0 0x09600000>;
	};
	icp_heap_iova: reservation-icp-heap {
		iommu-addresses = <&camss_icp 0 0x10a00000 0 0x00100000>;
	};
	icp_trace_iova: reservation-icp-trace {
		iommu-addresses = <&camss_icp 0 0x10b00000 0 0x00100000>;
	};
	icp_images_iova: reservation-icp-images {
		iommu-addresses = <&camss_icp 0 0x20000000 0 0x08000000>;
	};
};''')
after[path]=s
git('switch','-c','samurai-icp-platform389');patch=''
for name,s in after.items():
 p=source/name;a=p.read_text() if p.exists() else ''
 dest=P/'changes'/name;dest.parent.mkdir(parents=True,exist_ok=True)
 dest.with_suffix(dest.suffix+'.before').write_text(a);dest.write_text(s);p.write_text(s)
 patch+=''.join(difflib.unified_diff(a.splitlines(True),s.splitlines(True),fromfile='a/'+name if a else '/dev/null',tofile='b/'+name))
git('diff','--check');git('add','--',*after);git('commit','-m','media: camss: share platform ownership with the SM8150 ICP and IPE backend')
(HERE/'platform-and-board.patch').write_text(patch)
state=dict(stage=389,parent=parent,source=str(source),commit=git('rev-parse','HEAD'),branch=git('branch','--show-current'),changed=list(after),
 shared_camss_module_owner=True,firmware_path_from_dt=True,per_device_binding_guard=True,builtin_owner_supported=True,static_soc_default_disabled=True,board_candidate_enabled=True,board_physical_reservation_unchanged=True,installed=False,
 sha256={n:hashlib.sha256((source/n).read_bytes()).hexdigest() for n in after})
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state,indent=2))
