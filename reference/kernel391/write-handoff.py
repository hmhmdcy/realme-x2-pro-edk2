from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
text='''# 当前检查点：391（正式IPE用户空间已安装，94新增作业通过，目标active）

先读WORKING-BOUNDARIES.md、reference/kernel391/README.md。390交接归档archive/NEXT-SESSION-through390-2026-10-21.md。完整目标仍active。用户关灯睡觉，黑场／噪点不单独判链路故障；光学校准后做。

## 用户空间与实测

已安装五个libcamera运行包99990.7.2-r30，config/stack0.1.0-r25；默认管线含IPE，无需387私有LD_LIBRARY_PATH。构建13包、实装7包，原功能包保留。包内新核心验证六IPA签名，六IPA二进制与r29一致，算法/API复用362证据；/etc四份个体Preview配置SHA保持，不在公共包内。部署核心SHA b948765ea94423d628a1d455a7de8f737a84b45b3bee969a949b6886a4dee6b8，不与未strip的387私有库60181…混用。

维护源/mnt/samurai-full282/libcamera391-ipe-r30-built/src/libcamera-v0.7.2；复制387最终候选，0040补丁零fuzz复现四文件，IPA/dispatcher未变。正常linux-port/packages/libcamera、samurai-camera-config及源锁已更新。构建前一条错误空目录断言在绑定/编译前退出；删断言并保留SDK原底层目录后构建通过、bind卸载。不要重跑prepare-release/prepare-install覆盖产物。

r1实际新包七组测试：四摄GStreamer各12、主摄RAW＋NV12六、RAW-only六且IPE0、隔离主摄28/5阶段/GammaACK1，合计82direct。原IFE时间戳/SOF保持。随后脚本错误在PipeWire服务器查libcamera映射断言失败，自动回退r29/r24/world/repo并清理。真实加载相机SPA/核心的是WirePlumber；r2只修检查，重装相同包，核对SHA复用82作业、不重跑。普通用户PipeWire四节点/广角12帧、IPE增加12、errors0，实际WirePlumber映射已安装新核心。最终相机仓库指向/var/lib/samurai/k391-install-r2/repository/forward/packages.adb。

本轮新增94direct/cancel0/failed0；390重载后的旧计数12未重复计入，当前累计106，starts/stops8。最后FW单session create/destroy/peak1，12帧/43消息/43IRQ，INIT/PC完成、watchdog/protocol0。r1整体失败保留，不能改成成功；r2复用成功suite另计12。GammaACK为IFE IPA证据，不是IPE完整IQ。

current-state：八部署文件及CAMSS note相符、个体配置未变、taint0/newfault0；CPU/IRQ/backing/PM/map/import释放，四相机设备suspended，17clks0、9rails disabled/users0。PW9234/WP9237各一、uid10000；owner_refs53是桌面CAMSS句柄，m2m users0，非缓冲数。全部391 worker/client/collector终态，无后台实验。r1回退已实测，r2保持新包。

## 保持390内核和板级

同一390启动；host391→host390，guard=/var/lib/samurai/k390-active/boot-id-private.txt，private390/postboot-adoption-private.json。原USB SSH密钥/known_hosts保持，旧378guard失效，勿重授权。真实icp@ac10000绑定qcom-sm8150-icp，CAMSS/ICP同模块，五模块/FW/正式DT已永久部署，无test/overlay。391无内核/DT/模块/FW改动，无刷写/重启/模块卸载，复用390相关证据，不全量重复核验。

boot389 SHA e0256ff5bad0f6a2139de8690974d5fc25a0b58cad4cec1bb22f26bf0280884f；DT SHA0cc9dfd29044d7ca9ed2dbadbb62cedacd0298eba23fce377112ffe70d3b5db7；Image363 SHA15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468；logdump365 SHAaca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da。release7.3.0-rc6-rmx1931-samurai-k363+，Image源ba61a62293e0f6bc5838c06f2e85e033e3d702a8，与后续模块源区别。

WSL Ubuntu root；源码/build访问先284/storage.py::mounted_build()，现有32GiB ext4 backing不可格式化/重建。驱动source354 branch samurai-icp-platform389、HEAD a3c2b4cfacad2eefaadd4ef3efd35de3d9244d07，干净。模块389-intree-r4；qcom-camss SHA24fcfa685d07eb8d0e1a0b8356d9ee005e5413faf29c1b384e8c79c364630288；adapter SHAa0167f6acce4edad159d43101a723846ed494cf71fe3bb27857d2d145b44a7b8。core/helper/SG与388一致，新SG owner符号不可混旧SG。原778＋新增3=781，非全树原哈希保持。FW=/lib/firmware/qcom/sm8150/camera-icp.elf，SHAa22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63。

SoC默认disabled，Samurai静态DT启用7SID/5个仅IOVA节点；camera_mem9ab00000/5MiB/no-map保持。注册CAMSS→ICP/逆序退出，context/export/未知DMA共用owner，static suppress_bind_attrs。NULL builtin owner安全不等于完整builtin内核/任意热拔插已测。390原生18＋pipeline81＋重载后12共111direct、正常卸载/重载和r29 IFE四摄回归已验证，不重复计入391。

## 回退与续作

用户空间七个旧包及签名索引在/var/lib/samurai/k391-install-r2/repository/rollback，backup存原world/repo，rollback.list准备。先停消费者/回收DMA，离线精确装r29/r24并恢复world/repo/服务；r1已回退验证，r2未执行。内核回退仍设备k390-deployment/backup、private390/offline-module-rollback原两模块及原缺失三模块/FW记录。restore-files.py --offline-files-only仅恢复文件/depmod，须配合boot366切换，未执行。boot366 SHA c3e4e9c85d80c8ec37605cd522cf716525ae5ebe4fa801342dbf7586c292d924。勿全量重装778模块/旧logdump。

下一步显式在途取消/硬件错误并发、原厂Gamma/LTM/CCM完整IQ；保留reference/kernel363/REMAINING-CAMERA-SCOPE.md全部第五2MP身份/mux、多模式、动态帧长/防频闪、几何/多摄同步、连续AF、光学校准。当前1:1 NV12/NV21 IQ旁路和显式V4L2所有权，不外推异步implicit-fence发布/缩放/真实硬件错误并发/完整IPE IQ。旧SSC间歇EPERM/daemon4未宣称修复，不能因包完成缩小总目标。

保留373 reset-before-HFI、375 PC/WFI、376严格token/ACK、379未初始化MAP/UNMAP尾部；381未知DMA/reset所有权、388 DMA-only SG禁sg_page/sg_phys及自有IOMMU域别名检查；377/378失败审计、383 Unicorn全局MEM_READ破坏ThumbIT/SP陷阱。FW/HAL/汇编/CDM/完整日志/图像/个体校准仅private /mnt/e/edk2-samurai-out/kernel391及前序。公共mirror=/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150，仅本地提交，不push/PR，保留其它改动。
'''
(ROOT/'NEXT-SESSION.md').write_text(text)
prompt='''继续active多摄/ISP目标。读WORKING-BOUNDARIES.md、NEXT-SESSION.md、reference/kernel391/README.md。391正式安装签名libcamera r30/config-stack r25，默认四摄/RAW/隔离IPA82作业＋普通用户PipeWire12共94新增direct，failed/cancel0，个体校准保持。r1在82作业成功后误查PipeWire库映射失败并自动回退；实际核心由WirePlumber相机SPA加载。r2修检查重装相同包，复用82不重跑，补12帧通过、保持新版。全部worker/client/collector终态、服务恢复/资源回收/taint0。累计106=旧12+新增94。13包功能保持、7实装，六IPA二进制同r29、签名通过，r29/r24离线回退保存。内核/板级/五模块/FW保持390，无重启/刷写/卸载；host391→host390，guard390，旧378不可用。boot389/Image363/logdump365保持，驱动source354 a3c2b4cfacad2eefaadd4ef3efd35de3d9244d07干净，源码访问先mounted_build。用户空间维护源libcamera391-ipe-r30-built、正式配方和源锁已更新。下一步显式在途取消/硬件错误并发、原厂Gamma/LTM/CCM完整IQ及363全部剩余范围（第五2MP/多模式/帧长/几何/同步/连续AF）。当前1:1 IQ旁路/显式V4L2所有权，不外推完整IQ/implicit-fence。关灯黑噪点不单独判失败，光学校准后做，总目标未完成。
'''
(ROOT/'NEXT-SESSION-PROMPT.md').write_text(prompt)
