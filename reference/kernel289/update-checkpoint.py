"""Archive stale entrypoints and reconcile deployed kernel288 with the separate 289 candidate."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'reference/kernel289'
build=json.loads((HERE/'fixes-full-build-validation.json').read_text())
assert build['terminal'] and all(p['exit']==0 for p in build['phases']) and build['not_deployed']
health=json.loads((HERE/'final-health-validation.json').read_text());assert health['kernel_build']==288 and health['all778_modules_verified']
archive=ROOT/'archive/camera-before289-2026-10-19';assert not archive.exists();archive.mkdir()
files=['NEXT-SESSION.md','DOCS-INDEX.md','linux-port/camera/kernel/source-lock.json','linux-port/camera/deployment-lock.json',
 'linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md','reference/kernel276/OEM-TUNING.md','reference/kernel287/README.md']
manifest={}
for name in files:
 data=(ROOT/name).read_bytes();target=archive/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 manifest[name]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest());assert target.read_bytes()==data
(archive/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
deployed='8c79b7e1912790d3e18a84c9c6621a6d92baa768';candidate=build['commit']
source=ROOT/'linux-port/camera/kernel/source-lock.json';s=json.loads(source.read_text())
s.update(stage=289,maintained_branch='samurai-vfe175-pix288',maintained_commit=deployed,
 actual_kernel_image_stage=288,actual_kernel_release=health['release'],boot_stage=276,module_count=778,
 deployed_camera_modules=health['modules'],current_boot_evidence='../../../reference/kernel288/postboot-identity-validation.json',
 complete_new_kernel_image_and_modules_deployed=True,complete_rootfs_rebuild_pending=True,
 full_kernel_candidate_evidence='../../../reference/kernel289/fixes-full-build-validation.json',
 previous_lock_archive='../../../archive/camera-before289-2026-10-19/linux-port/camera/kernel/source-lock.json',
 source_worktree_branch='samurai-tpg-gamma289',source_worktree_commit=candidate,source_worktree_is_undeployed_candidate=True,
 candidate_source_clean=True,candidate_source_evidence='../../../reference/kernel289/fixes-commit-validation.json',
 current_boot_auto_af_retest_pending=True,final_health_evidence='../../../reference/kernel289/final-health-validation.json')
s.pop('complete_new_image_and_rootfs_not_deployed',None)
source.write_text(json.dumps(s,indent=2,ensure_ascii=False)+'\n')
p=ROOT/'linux-port/camera/deployment-lock.json';d=json.loads(p.read_text())
d.update(stage=289,kernel_boot_stage=276,current_boot_guard_stage=288,kernel_image_stage=288,
 kernel_release=health['release'],kernel_module_count=778,kernel_modules=health['modules'],
 kernel_source_commit=deployed,kernel_source_branch='samurai-vfe175-pix288',
 image_sha256='6bad9512ac1481f864cb62f8da183761c240b01e7ece53f9f48026c9b55337f5',
 logdump_sha256='8ec8b1e4d28ed76906ac9c9d31d8d791cab9d190c28d7f27224f8fb47e4aa56c',
 kernel_config_sha256='34204656424a03b7904c6d079aa0b112dafcec220b2a27b23c7b9afaa4eca8b2',
 current_camera_evidence='../../reference/kernel289/README.md',final_health_evidence='../../reference/kernel289/final-health-validation.json',
 guard_path='/var/lib/samurai/k288-work/boot-id-private.txt',
 previous_lock_archive='../../archive/camera-before289-2026-10-19/linux-port/camera/deployment-lock.json',
 current_stack_four_camera_regression='../../reference/kernel288/four-camera-regression-validation.json',
 planned_boot_transition_evidence='../../reference/kernel288/postboot-identity-validation.json',
 complete_kernel_image_and_modules_deployed=True,full_rootfs_rebuild_pending=True,
 candidate_kernel_receipt='../../reference/kernel289/fixes-full-build-validation.json',candidate_kernel_deployed=False,
 candidate_kernel_source_commit=candidate,candidate_kernel_source_branch='samurai-tpg-gamma289',
 candidate_release_same_as_deployed_requires_install_plan=True,
 experimental_hardware_tpg_nv12_verified=True,experimental_hardware_color_neutrality_passed=False,
 experimental_gamma_cgc_upload_readback_words=192,
 experimental_gamma_evidence='../../reference/kernel289/gamma-upload-pixel-validation.json',
 hardware_isp_statistics_and_ipa_incomplete=True,spectra_hardware_image_processing_supported=False,
 current_boot_auto_af_retest_pending=True,current_boot_optical_scene_retest_pending=True,
 autofocus_verified_scope='GW1 Auto trigger/cancel and AE tested on boot276/r24; kernel288 AF search not retested; Continuous and distance calibration incomplete',
 current_stack_visual_scene_review_pending=True)
services=d['system_services'];services.update(stage=288,
 new_processes=[dict(name=r['comm'],pid=r['pid'],start_ticks=r['start_ticks']) for r in health['processes'] if r['comm'] in ['pipewire','wireplumber']],
 phosh_pid=next(r['pid'] for r in health['processes'] if r['comm']=='phosh'),current_manifest='/var/lib/samurai/k288-services-verified-private.json')
d['experimental_gamma_probe_is_temporary_not_deployed_driver_fix']=True
p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
notice='289（2026-10-19）：现机为288完整Image/778模块，四摄RAW＋CPU ISP回归234帧；本轮定位内部TPG继承C-PHY及Gamma SRAM上传缺时钟，修复候选ff8d2e9fc完整构建通过、未部署。临时硬件对照192个LUT字精确读回，黑白亮度恢复但色度仍错误，CST/统计/IPA继续；根部署锁已更新。[289证据]({link})。\n\n'
for name,link in [('linux-port/camera/README.md','../../reference/kernel289/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel289/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel289/README.md'),('reference/kernel276/OEM-TUNING.md','../kernel289/README.md'),('reference/kernel287/README.md','../kernel289/README.md')]:
 p=ROOT/name;p.write_text(notice.format(link=link)+p.read_text())
p=ROOT/'DOCS-INDEX.md';text=p.read_text()
old='[287 Demux/MNDS与分层](reference/kernel287/README.md)、[286 Gamma/输出位深](reference/kernel286/README.md)、[285 CST12/完整构建](reference/kernel285/README.md)'
new='[289 Gamma时钟/TPG](reference/kernel289/README.md)、[288统一内核/NV12](reference/kernel288/README.md)、[287分层](reference/kernel287/README.md)'
assert old in text;p.write_text(text.replace(old,new));assert p.stat().st_size<=10000
next_text='''# Realme X2 Pro 当前检查点

2026-10-19：[289 TPG/Gamma时钟](reference/kernel289/README.md)、[288统一内核部署](reference/kernel288/README.md)。完整多摄及骁龙ISP目标active；优先现有方案，按SoC/板级/驱动/用户态收敛，画质与硬件ISP尚未完成。

## 当前部署与启动身份

现机 **#288**、`7.3.0-rc6-rmx1931-samurai-k279candidate+`，源码8c79b7e1912790d3e18a84c9c6621a6d92baa768／samurai-vfe175-pix288；完整Image＋778模块已部署。boot276和DT保持，不再是Image183/k132+。961包、libcamera r24/config-r19、PW/SPA/Gst1.6.9-r3及50相机载荷保持。[部署锁](linux-port/camera/deployment-lock.json)、[源码锁](linux-port/camera/kernel/source-lock.json)

Image SHA 6bad9512ac1481f864cb62f8da183761c240b01e7ece53f9f48026c9b55337f5；logdump 8ec8b1e4d28ed76906ac9c9d31d8d791cab9d190c28d7f27224f8fb47e4aa56c；boot 0d6bbc0255fc7a44340b2c2c6a20f2bfa807f683f69dd20a3fb130d961dc4c64；DTB dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d。[读回](reference/kernel288/postboot-identity-validation.json)

运输用reference/kernel289/host.py，严格原SSH密钥、新发现USB端点和 `/var/lib/samurai/k288-work/boot-id-private.txt`；旧276 guard失效。按driver/实体找设备：本轮main8-0010/lens8-0072、tele6-002d、wide9-0010、front7-0010。Phoc3564/Phosh3792/PW5163/WP5165，启动ticks见手机k288-services-verified-private.json；续作重核。

## 已验证与当前缺陷

- 288实际TPG→CSID175 IPP→VFE175 FULL NV12取得3帧320×240；四实体摄像头18段234帧回归通过，仍RAW→CPU SoftwareIsp，不是实体硬件ISP。原r1/r2零帧失败和r3测试拓扑修正均保留。
- 289复现内部TPG继承主摄3线C-PHY导致不出帧；仅按标准MC链接建立D-PHY历史后恢复3帧。候选改gen2内部源固定4线D-PHY，保留外部PHY配置，不放机型判断。
- Gamma SRAM无时钟时逐地址/连续读均重复同一字；打开原厂0x34 bit3后每表64个不同字，但现机表全部不匹配要求曲线。临时上传同一sRGB曲线192字全部精确读回，9帧同流对照：黑白亮度0/254，色度仍0/0而非128。不能宣称颜色已修好。[像素](reference/kernel289/gamma-upload-pixel-validation.json)
- CST零矩阵、high/low字段512常量对照15帧；两者全零，偏移/色度域仍未解释，不据此猜改字段或应用补色。原Gamma及12个CST寄存器已恢复；旧inactive LUT恢复写入已发出，但未重读逐字验收。
- r4两帧后因恒定prefill碰上真实像素误判；r5改位置相关prefill并保持90%门槛，3帧通过。所有工具/worker已终态且进程消失，失败不抹去。[结果](reference/kernel289/constant-pixel-and-workers-validation.json)
- 原278标准Auto AF五场景890组＋AE AF389组已验证，r24/r19及主摄设备AF数据保持；#288未重测AF搜索/实景/旋转/GUI/录像。扫描9…12秒待加速，Continuous/距离标定、Shine OV02A1B及完整画质仍开放。
- [289最终健康](reference/kernel289/final-health-validation.json)：全部778模块/50载荷和原776模块保持；五sensor/lens/双CCI/CAMSS suspended，九rails/共享I/O OFF/users0，MCLK/CCI clocks0，fault0/taint0/pstore空、CCI错误0；桌面及三DSP/SensorProxy正常。历史GPU默认故障/CPU回退、modem watchdog和整机长稳仍开放。

## 源码回退与下一步

当前工作树camera279-isp-kernel／samurai-tpg-gamma289干净，提交ff8d2e9fc04ef92407ff83c40c4e059eb620f0f7；父5ad34a2d007c1506e70dc91739362d1bf801eb8b，部署8c79b7e保留。两个独立本地提交未推送，checkpatch0错误0警告；内核树内不等于上游接受。

实际函数ASan/UBSan：2621440组外部PHY历史；Gamma SRAM写时钟要求、四种原CGC恢复、inactive bank及现有处理/生命周期回归通过，旧Gamma负对照按时钟断言失败。完整39组件Werror＋Image/778实际ko两阶段exit0，101.64秒/增量诊断0；Image SHA a28ecd3d29ac7d3bac3c37ab1f336d33317e5c0ff70617d44b469ea185873d2b，DTB/config保持。[完整构建](reference/kernel289/fixes-full-build-validation.json)

**289候选未打包、未安装、未启动验收**。release仍与现机相同，不可套288脚本的新release独立目录假设。先完成CST/色度协议对照，再规划独立release及配套initramfs/模块、打包/回退和一次部署；不能直接刷仅编译的Image。所有实验MMIO工具仅开发诊断，不作为应用或生产接口。

输出/mnt/samurai-full282/build，先用284/storage.py核E盘backing并挂载，不能往空挂载点写。config现为带initramfs的34204656424a03b7904c6d079aa0b112dafcec220b2a27b23c7b9afaa4eca8b2；输入仍input-initramfs288。旧288六项完整产物存私人kernel289/completed-boot288；新289完整ko哈希在私人kernel289。构建/提交/上传/采集脚本已执行，不直接重放。

后续先修黑白中性/色序与处理域，再接实体硬件ISP；补真实统计/参数节点、libcamera pipeline/IPA及帧级对应、模组调校、四摄GUI录像与异常PM。资源保留参数clk/pd/regulator_ignore_unused仍在，不能承诺无补丁内核/关键包更新；完整rootfs复建待做。

回退仍保留boot276及旧logdump183（67108864字节，SHA e73754c7d327925acf031aed54e0e6d02069b7a112c32b187ac9bfb468da1358），原k132+776模块逐字未改；288镜像/778模块与整机248备份保持，未做回退往返。私人资料E:/edk2-samurai-out/kernel288及kernel289，不公开像素/校准/密钥。[操作边界](WORKING-BOUNDARIES.md)、[硬件清单](linux-port/docs/HARDWARE-STATUS.md)
'''
p=ROOT/'NEXT-SESSION.md';p.write_text(next_text);assert p.stat().st_size<=6500,p.stat().st_size
print(json.dumps(dict(stage=289,archived_files=len(files),next_bytes=p.stat().st_size,index_bytes=(ROOT/'DOCS-INDEX.md').stat().st_size,
 deployed_kernel_build=288,candidate_commit=candidate,candidate_not_deployed=True),indent=2))
