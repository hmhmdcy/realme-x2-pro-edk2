"""Archive previous checkpoints and reconcile the verified kernel290 deployment."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def write(p,s):
 p=ROOT/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
def dump(p,v):write(p,json.dumps(v,ensure_ascii=False,indent=2)+'\n')
health=read('reference/kernel290/final-health-validation.json')
pixels=read('reference/kernel290/standard-tpg-pixel-validation.json');assert pixels['passed']
assert read('reference/kernel290/four-camera-regression-validation.json')['frames']==235
assert read('reference/kernel290/postboot-identity-validation.json')['new_boot_verified']
archive=ROOT/'archive/camera-before290-2026-10-19';assert not archive.exists()
paths=['NEXT-SESSION.md','DOCS-INDEX.md','sessions/INDEX.md','linux-port/camera/deployment-lock.json',
 'linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md',
 'reference/kernel276/OEM-TUNING.md','linux-port/docs/HARDWARE-STATUS.md']
saved=[]
for name in paths:
 data=(ROOT/name).read_bytes();p=archive/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 saved.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
dump('archive/camera-before290-2026-10-19/manifest.json',dict(stage=290,files=saved))
commit='15c8639d8badf5d4146bfd1b2c2fcb2460a137e5';branch='samurai-full-route290'
release='7.3.0-rc6-rmx1931-samurai-k290+'
build=read('reference/kernel290/boot-candidate-build-validation.json')
dep=read('linux-port/camera/deployment-lock.json')
dep.update(stage=290,current_boot_guard_stage=290,kernel_image_stage=290,ko_count=778,kernel_module_count=778,
 kernel_source_commit=commit,kernel_source_branch=branch,kernel_release=release,
 image_sha256=build['artifacts']['arch/arm64/boot/Image']['sha256'],
 logdump_sha256='0f169a331d1c4aac98cd67f636c9f30dd0c727ffc20a6031e4de142d7f57396a',
 kernel_config_sha256='9c1b4f24d42519af211b81fc015c948239ea6cfc1550d197469b07c779053581',
 guard_path='/var/lib/samurai/k290-work/boot-id-private.txt',
 current_camera_evidence='../../reference/kernel290/README.md',
 final_health_evidence='../../reference/kernel290/final-health-validation.json',
 current_stack_four_camera_regression='../../reference/kernel290/four-camera-regression-validation.json',
 planned_boot_transition_evidence='../../reference/kernel290/postboot-identity-validation.json',
 candidate_kernel_receipt='../../reference/kernel290/boot-candidate-build-validation.json',candidate_kernel_deployed=True,
 candidate_kernel_source_commit=commit,candidate_kernel_source_branch=branch,
 candidate_release_same_as_deployed_requires_install_plan=False,
 experimental_hardware_color_neutrality_passed=True,
 experimental_gamma_evidence='../../reference/kernel290/standard-tpg-pixel-validation.json',
 experimental_gamma_probe_is_temporary_not_deployed_driver_fix=False,
 standard_tpg_no_userspace_mmio=True,hardware_isp_statistics_and_ipa_incomplete=True,
 physical_hardware_isp_image_validation_pending=True,
 independent_red_blue_validation_pending=True,
 previous_lock_archive='../../archive/camera-before290-2026-10-19/linux-port/camera/deployment-lock.json',
 autofocus_verified_scope='GW1 Auto trigger/cancel and AE tested on boot276/r24; kernel290 AF search not retested; Continuous and distance calibration incomplete',
 previous288_778_modules_preserved=True,original132_776_modules_preserved=True)
process={p['comm']:p for p in health['processes']}
services=dep['system_services'];services.update(stage=290,new_processes=[dict(name=n,pid=process[n]['pid'],start_ticks=process[n]['start_ticks']) for n in ['pipewire','wireplumber']],
 phosh_pid=process['phosh']['pid'],current_manifest='/var/lib/samurai/k290-services-verified-private.json')
dump('linux-port/camera/deployment-lock.json',dep)
src=read('linux-port/camera/kernel/source-lock.json')
src.update(stage=290,maintained_branch=branch,maintained_commit=commit,actual_kernel_image_stage=290,
 actual_kernel_release=release,module_count=778,deployed_camera_modules=health['modules'],
 current_boot_evidence='../../../reference/kernel290/postboot-identity-validation.json',
 full_kernel_candidate_evidence='../../../reference/kernel290/boot-candidate-build-validation.json',
 previous_lock_archive='../../../archive/camera-before290-2026-10-19/linux-port/camera/kernel/source-lock.json',
 source_worktree_branch=branch,source_worktree_commit=commit,source_worktree_is_undeployed_candidate=False,
 candidate_source_evidence='../../../reference/kernel290/full-route-commit-validation.json',
 final_health_evidence='../../../reference/kernel290/final-health-validation.json')
dump('linux-port/camera/kernel/source-lock.json',src)
write('NEXT-SESSION.md','''# Realme X2 Pro 当前检查点

2026-10-19：[290 原厂协议、FULL路径修复与完整部署](reference/kernel290/README.md)。完整多摄及骁龙ISP目标active，画质、统计/IPA及实体硬件ISP仍未完成。

## 当前部署与启动身份

现机 **#290**、`7.3.0-rc6-rmx1931-samurai-k290+`，源码15c8639d8badf5d4146bfd1b2c2fcb2460a137e5／samurai-full-route290；完整Image及独立release的778模块已部署并读回验证。boot276、DT、961包、libcamera r24/config-r19、PW/SPA/Gst1.6.9-r3和50相机载荷保持。[部署锁](linux-port/camera/deployment-lock.json)、[源码锁](linux-port/camera/kernel/source-lock.json)

Image SHA 132012f2e0b2c1191a959098ceae8bb026316001fce4985e196fb2ef50bd6d5f；logdump 0f169a331d1c4aac98cd67f636c9f30dd0c727ffc20a6031e4de142d7f57396a；boot 0d6bbc0255fc7a44340b2c2c6a20f2bfa807f683f69dd20a3fb130d961dc4c64；DTB dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d。

运输用reference/kernel290/host.py，严格原SSH密钥、新USB端点和 `/var/lib/samurai/k290-work/boot-id-private.txt`；旧288 guard不再使用。按driver/实体发现设备：本轮main8-0010/lens8-0072、tele6-002d、wide9-0010、front7-0010。Phoc3717/Phosh3937/PW5294/WP5304；start_ticks见[最终健康](reference/kernel290/final-health-validation.json)及手机k290-services-verified-private.json。续作核实际身份，不重放已执行部署/构建/采集脚本。

## 已验证与当前缺陷

- 原厂HAL与固定CamX参考共同确认VFE175 0x4c bit4为FULL后处理路径门控。原来缺此位使10-bit数值取低8位；临时有界对照证明补齐后128/256/512/1023准确变为32/64/128/255，输出clamp生效，无需猜改CST字段、矩阵或packer。[协议](reference/kernel290/full-route-contract-validation.json)
- 公共SoC后端生命周期已实现门控，连同289的TPG内部D-PHY历史隔离及Gamma SRAM时钟修复部署。仅SoC驱动修复，无机型判断、DT/用户态变化。checkpatch0错误0警告，实际函数ASan/UBSan及完整Image/778ko构建通过。
- #290四摄18段235帧、主摄SIGINT退出及重开全部通过，仍RAW＋CPU SoftwareIsp。最后主摄C-PHY后直接标准MC/V4L2内部TPG→CSID175 IPP→VFE175 FULL NV12取得3帧320×240，无用户态MMIO或D-PHY历史绕行。像素与先前临时正确路径逐字相同，黑白Y0/255、U/V128，绿/品红响应通过。[标准采集](reference/kernel290/standard-tpg-validation.json)、[像素](reference/kernel290/standard-tpg-pixel-validation.json)
- 该TPG的R=B，不能独立证明红蓝顺序；实体sensor硬件PIX、真实统计/参数及libcamera硬件pipeline/IPA仍待接通。前摄/广角/长焦日志实际回退uncalibrated.yaml；主摄专用配置不是完整原厂调校。[实际用户态路径](reference/kernel290/regression-path-validation.json)、[原厂资料边界](reference/kernel276/OEM-TUNING.md)
- 首次新启动检查服务尚未就绪，后续自然启动，无手动重启或改配置；失败及诊断保留。最终五sensor/lens/双CCI/CAMSS suspended、九rails及共享I/O OFF/users0、MCLK/CCI clocks0、fault0/taint0/pstore空，三DSP/SensorProxy及桌面正常。历史GPU默认故障/CPU回退与modem watchdog不因此结案。
- 278标准单次Auto AF及AE下AF证据保留，#290尚未重测AF搜索、实景、旋转、GUI或录像。AF约9–12秒待加速，Continuous/距离标定、Shine OV02A1B与完整画质仍开放。

## 源码回退与下一步

维护树 `/home/cy122/x2pro-linux/camera279-isp-kernel`，samurai-full-route290／15c8639d8badf5d4146bfd1b2c2fcb2460a137e5；父ff8d2e9fc及288部署8c79b7e保留，本地提交未推送，内核树内不等于上游接受。完整构建147.27秒/增量诊断0，39个CAMSS组件Werror；只改LOCALVERSION/INITRAMFS_SOURCE，BT嵌入模块与实际安装新release匹配。

构建输出/mnt/samurai-full282/build；先用284/storage.py核E盘backing并挂载，不往空挂载点写。config SHA9c1b4f24d42519af211b81fc015c948239ea6cfc1550d197469b07c779053581，input-initramfs290和modules290。旧289六项产物在私人kernel290/completed-boot289，旧288在kernel289/completed-boot288。

下一步用可区分R/B的标准RAW图案补色序验证，再将普通Bayer广角实体sensor接入硬件FULL；使用标准选择/格式/控制接口，保存恢复图、模式、选择和controls。之后补真实统计/参数、帧级对应及libcamera pipeline/IPA，按模组版本解析原厂配置/EEPROM并实测标定。实验MMIO工具仅诊断，不作为应用生产接口。

仍有clk/pd/regulator_ignore_unused和下游内核/关键包补丁，不能承诺无补丁升级。目标是通用功能进入上游，设备差异留标准DT、固件和调校数据包；完整rootfs重建、关键栈跨版本及整机冷启/PM/长稳验收仍待做。

首选即时回退为保留的288 logdump镜像，SHA8ec8b1e4d28ed76906ac9c9d31d8d791cab9d190c28d7f27224f8fb47e4aa56c及原288独立778模块；boot276不变，旧k132的776模块/183 logdump及整机248备份保持。未做回退往返。私人资料E:/edk2-samurai-out/kernel290；不公开像素、校准、密钥。[操作边界](WORKING-BOUNDARIES.md)、[硬件清单](linux-port/docs/HARDWARE-STATUS.md)
''')
assert (ROOT/'NEXT-SESSION.md').stat().st_size<=6500
summary='290（2026-10-19）：#290完整Image/独立778模块已部署，原厂协议确认并修复VFE175 FULL后处理门控，带入TPG历史隔离和Gamma时钟修复。四摄RAW＋CPU ISP 235帧；标准接口TPG硬件NV12三帧、黑白中性通过，无用户态MMIO。实体硬件ISP/独立红蓝/统计与IPA/完整画质仍待做。'
for name,link in [('linux-port/camera/README.md','../../reference/kernel290/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel290/README.md'),('reference/kernel276/OEM-TUNING.md','../kernel290/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel290/README.md')]:
 old=(ROOT/name).read_text(encoding='utf-8');write(name,summary+f'[290证据]({link})。以下旧阶段按当时状态阅读。\n\n'+old)
index=(ROOT/'DOCS-INDEX.md').read_text(encoding='utf-8')
old=next(l for l in index.splitlines() if '289' in l and 'reference/kernel289/README.md' in l)
index=index.replace(old,'| 最新相机驱动与调校边界 | [290 FULL门控修复/完整部署/标准TPG](reference/kernel290/README.md)、[原厂调校资料](reference/kernel276/OEM-TUNING.md) |')
write('DOCS-INDEX.md',index);assert (ROOT/'DOCS-INDEX.md').stat().st_size<=10000
write('reference/kernel290/README.md','''# 290：原厂FULL后处理协议、公共驱动修复及完整部署

2026-10-19。'''+summary+'''

本轮按SoC/板级/驱动/用户态分层继续。原厂资料可参考，但开源内核不等于完整CamX/Chromatix算法开源；原厂DTS承载硬件事实，sensor/lens资料用于标准驱动协议，模组标定和图像算法进入匹配的IPA及数据包。[资料范围](../kernel276/OEM-TUNING.md)

## 原厂依据与硅上对照

固定CamX Chi参考9f17f1b568626b393e785b369c5dc94543774d7a的crop实现与本机HAL静态指令共同指向0x4c bit4。原来只打开CST bit0、MNDS bit3和单独Y/C round/clamp，FULL并未经过该后处理路径。仅增加全局门控后10→8位响应正确、clamp生效；不需要反转CST偏移字段、改矩阵、FULL client3/4或NV12 packer0xe。[固定来源](crop-reference-validation.json)、[HAL与硬件契约](full-route-contract-validation.json)

两次有界实验各15阶段93帧，先恢复Gamma表后控制CST常量和输出clamp；缺门控时512→0，补门控后512→128，128/256/1023分别变为32/64/255。恢复寄存器、原图及原inactive Gamma LUT192字逐字重读确认，资源回收无新增fault。[原响应](cst-response-capture-validation.json)、[正确路径](cst-route-capture-validation.json)、[临时像素对照](route-pixel-validation.json)。均为内部TPG，不证明实体画质。

生产修复位于camss-vfe-175-round.c，只在配置/停止FULL时读改写bit4，保留其它处理位。实际函数ASan/UBSan覆盖启停、无效参数零MMIO及旧路径隔离；checkpatch0 errors/0 warnings。提交15c8639d8badf5d4146bfd1b2c2fcb2460a137e5／samurai-full-route290，带入289两个修复，未推送。[主机验证](full-route-host-validation.json)、[提交阶段收据](full-route-commit-validation.json)。该收据not_deployed表示提交当时，实际部署由后续读回收据界定。

## 完整构建与单次部署

完整Image、DTB及778模块从同一提交构建，release7.3.0-rc6-rmx1931-samurai-k290+。39个CAMSS组件Werror，五阶段147.27秒、增量诊断0；BT三个模块先按新release构建再嵌入initramfs，与安装树完全匹配。depmod无未解析符号，CPIO/EFI FAT/Image/DTB与fsck核对通过。[完整构建](boot-candidate-build-validation.json)、[打包](boot-package-validation.json)

新release独立模块目录先安装并核778项，288及k132旧目录保留。正常停流、一次restart2进入bootloader，重新发现身份/分区后仅刷logdump、一次reboot；boot276/DT保持。新SSH端点/原hostkey及guard采用后，logdump/boot读回与778项匹配。[模块暂存](module-staging-validation.json)、[刷写](flash-validation.json)、[新启动读回](postboot-identity-validation.json)

首轮服务检查捕获尚未就绪阶段，之后服务自然启动，没有手动重启/修改配置；原失败保留私人日志，后续只读复核通过。[启动跟进](postboot-first-check-followup-validation.json)、[运行时](postboot-runtime-validation.json)。不能用旧rc.log历史失败代表本启动故障。

## 新驱动实际验收

四摄标准cam独立进程18段235帧通过，包含主摄SIGINT/重开，PM/rail/clock正常回收，无强杀或用户态服务重启。[四摄](four-camera-regression-validation.json)。日志确认普通相机仍Simple＋RAW＋CPU SoftwareIsp；imx471/imx319/s5k3m5缺专用调校文件，回退uncalibrated.yaml，主摄有s5kgw1.yaml但不是完整原厂调校。[实际路径及调校文件](regression-path-validation.json)

随后在最后主摄C-PHY历史下，标准MC/V4L2工具直接内部TPG→CSID175 IPP→VFE175 FULL，得到三帧320×240 NV12，图恢复，五sensor/lens保持休眠。工具不访问/dev/mem、不上传Gamma、不改路由寄存器、不预置D-PHY历史。[标准工具](standard-tpg-tool-validation.json)、[三帧实测](standard-tpg-validation.json)

第一帧与先前临时正确路径输出SHA完全相同：黑白Y0/255、U/V128，绿/品红响应正确。私人预览已核看。该TPG所有条纹R=B，仍需独立红蓝输入验证，不称完整色彩或实体硬件成像验收。[像素](standard-tpg-pixel-validation.json)

最终778项、旧288778项及旧k132776项、50用户载荷和961包核对通过；相机/CCI/CAMSS休眠、九rails/共享IO关闭、MCLK/CCI clocks0，fault0/taint0/pstore空，三DSP、SensorProxy、桌面、Wi-Fi/HCI保持。[最终健康](final-health-validation.json)。历史GPU与modem watchdog未因此结案。

## 仍需推进

实体sensor→硬件PIX、独立红蓝、统计/参数节点及帧级对应、libcamera硬件pipeline/IPA、模组校准与画质仍未完成。278单次Auto AF证据不晋升为290重测，Continuous/距离标定、GUI录像、旋转、第四后摄和长稳继续开放。当前仍有下游内核/关键包补丁及ignore_unused资源保留策略，不能保证无补丁更新；源码在树内不等于上游接受。目标保持active。

当前身份和回退见[检查点](../../NEXT-SESSION.md)。所有已执行部署/采集脚本先检查运行状态及产物再决定复用；私人像素、原厂二进制、校准、密钥未公开。289/288旧阶段记录和失败保留。
''')
write('sessions/290-vfe175-full-route-and-standard-tpg.md','# 290：原厂FULL路径修复、完整部署与标准硬件TPG验收\n\n'+summary+'\n\n[完整证据](../reference/kernel290/README.md)、[当前部署](../NEXT-SESSION.md)。\n')
dump('reference/kernel290/documentation-validation.json',dict(stage=290,previous_files_archived=saved,
 next_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,index_bytes=(ROOT/'DOCS-INDEX.md').stat().st_size,
 source_and_deployment_locks_updated=True,goal_incomplete=True))
print('Kernel290 checkpoints reconciled; previous files archived.')
