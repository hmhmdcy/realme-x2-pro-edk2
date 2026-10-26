from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
scope='Normal CAMSS/board390 and signed userspace391 retained; explicit local-rejection core+adapter393 pair permanently installed; no Image/DT/FW/userspace change393'
for n in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 p=ROOT/n;d=json.loads(p.read_text());d['in_progress_installed_scope']=scope;p.write_text(json.dumps(d,indent=2)+'\n')
text='''# 当前检查点：393（IPE局部错误隔离已正式部署，目标active）

读WORKING-BOUNDARIES.md、reference/kernel393/README.md。392完整交接归档archive/NEXT-SESSION-through392-2026-10-21.md。多摄／ISP校准目标仍active，用户关灯黑噪点不单独判链路故障，依赖照明的校准后做。

## 已改源和正式部署

修复392发现的输入错误连带peer问题：核心新增camss_a5_ipe_run_status及显式RESET_REQUIRED/REJECTED/COMPLETE结果，保留旧camss_a5_ipe_run符号／调用方式。默认全局恢复；只有配置／引擎可信、未尝试本作业transfer MAP、清理成功且临时作业映射／DMA-BUF引用均释放时，负返回才可REJECTED。任何作业MAP尝试后的负返回、失效状态／IRQ／协议／残留 backing仍默认全局停机。不是按EINVAL/ETIMEDOUT猜安全，也不是从未发过session配置命令。未知MAP/FRAME/UNMAP保留/resetACK与owner机制不变。

adapter仅对显式REJECTED不置全局fatal、不重启后端，坏队列ERROR/EIO后仍需STREAMOFF修复。source354 branch samurai-ipe-errors393，HEAD64aaf4f78c05f0912e658780294fbded531d87ce，干净。改boot.c/ipe.h/m2m.c三个文件，reference/kernel393/local-job-errors.patch保存完整差分。访问源码/build先284/storage.py::mounted_build()，现32GiB ext4 backing不得重建／格式化。

18个实际核心/DMA传输函数测试＋10个实际device_work测试均ASan/UBSan通过；包括同errno不同结果、提交前fence超时、释放失败、失效IRQ/协议、未知MAP/FRAME/UNMAP引用保留和取消。固件/MMIO是provider，不外推真实硬件错误并发。ARM64 W=1/-Werror通过、诊断0；第一次只指定两目标缺modpost依赖符号，补所需媒体依赖目标后r2构建通过。依赖SG/m2m helper与旧摘要相同，未替换。

只正式替换两个匹配模块，393-intree-r2：core352776B SHAe22253916088e58a221c1948f025c44c939c819310c7d3f67106053dd39502f6；adapter119368B SHAff2bfa7a9439b2ef67087ff6f5db8c9d26e9a92596cd1f63b14c3a047111d4c1。两者成对使用。原qcom-camss复合模块389、标准SG/helper、Image363、boot389/logdump365、DT389、FW和用户空间r30/r25保持，无重启或刷写。正常停止消费者、模块卸载/成对换文件/depmod/modprobe，最终新磁盘摘要和加载note匹配。原两文件精确backup在设备/var/lib/samurai/k393-deployment-r4/backup，private389原件仍在。

## 实机、失败和当前计数

r4完整窗口：同DMA-BUF输入输出局部-EINVAL，failed只加1/fatalfalse；坏文件仍打开时peer连续两帧不同模式／时间戳／有效Y正确。坏队列单独STREAMOFF，原fd换不重叠DMA-BUF出帧，peer session保持，starts1/stops0。并发取消回归cancel1、peer与原fd重启帧正确。默认r30 GStreamer四摄各12，共48处理帧，bus0，fixture恢复，无LD_LIBRARY_PATH或私有配置覆盖。

最终r4新epoch：jobs55=completed/direct53+cancel1+预期failed1，first_error=-22累计诊断，starts/stops7；硬件完成日志54=53正常+1上层取消。最后FW单会话12帧/43消息/44IRQ，INIT/PC完成、watchdog/protocol0。不要按旧failed/first_error全0断言误判或额外清零；后续比增量和fatal。

三个失败窗口保留，核心源／模块在尝试间未变：r1卸载后错误要求静态平台设备节点消失，清理又对未绑定设备等PM，旧文件没替换。inspect确认模块全无、静态device仍在但driver无，独立recover-unloaded恢复旧平台/桌面，probe无FW。r2 probe后owner_refs立即0断言遇临时引用，自动恢复旧pair/服务；r3记录初始ref1，有界等归0。r3实际局部拒绝＋peer两帧成功，但客户端借旧offset16辅助未预留额外行，QBUF长度拒绝；整体失败自动回退。改客户端offset0后r4完整通过。r2/r3真实回退均成功，r4保留新版，不重跑已有worker。

r3两帧是失败窗口部分证据，不加到r4完成53。本轮全部尝试硬件完成日志56；392旧累计132在首次正常卸载前保存，后续真实模块切换重新计数，不能把各epoch当同一counter叠加。r4末实际只55。r1/r2无图像作业，r3三个job对应1局部拒绝＋2peer完成，未完成同fd修复。

current-state：新两文件及loaded note、原两备份相符，原CAMSS note未变；七包仍r30/r25、四份私有配置SHA保持。CPU/IRQ/PM/backing/map/import回收，ICP/CAMSS/双CCI suspended，17clks0，9rails disabled/users0。PW12387/WP12390各一/uid10000；m2m users0/runningfalse/fatalfalse/pinnedfalse/orphans0，owner_refs53为桌面CAMSS句柄，非缓冲数。四窗口全部worker/client/collector终态，无dump/timeout/newfault，taint0。无后台实验。

## 保持的启动／用户空间与回退

同一390启动，host393→392→391→390，guard=/var/lib/samurai/k390-active/boot-id-private.txt，private390/postboot-adoption-private.json；原USB密钥/known_hosts不变，旧378guard失效，勿重授权。真实icp@ac10000绑定qcom-sm8150-icp，CAMSS/ICP同模块，静态7SID/5仅IOVA节点，无test/overlay。静态device在卸载后应仍存在，要查driver和m2m_status是否注销，不能要求device目录消失。新probe可能有临时owner1，等其归0且无作业、无FW启动后继续。

Image363源ba61a62293e0f6bc5838c06f2e85e033e3d702a8，release7.3.0-rc6-rmx1931-samurai-k363+；实际Image配置/源码不同于后续模块。boot389 SHAe0256ff5bad0f6a2139de8690974d5fc25a0b58cad4cec1bb22f26bf0280884f；logdump365 SHAaca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da。原qcom-camss SHA24fcfa685d07eb8d0e1a0b8356d9ee005e5413faf29c1b384e8c79c364630288，SG SHA735bded11ddedc9e0cad393bb3e35d2aa97b9d161161562ae9856f909cd6a643；原778+新增3=781数量不变。新SG owner API不能换回旧SG配现adapter。FW=/lib/firmware/qcom/sm8150/camera-icp.elf/SHAa22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63保持。

五libcamera99990.7.2-r30/config-stack0.1.0-r25，维护源libcamera391-ipe-r30-built，部署核心SHAb948765ea94423d628a1d455a7de8f737a84b45b3bee969a949b6886a4dee6b8。391完整13包/7实装、六IPA签名及同r29算法、四摄/RAW/隔离IPA/PipeWire证据保持；无需重建用户空间或重复全矩阵。

393 pair回退：先停消费者确认DMA/owner0，卸载正常qcom_camss→adapter→core，成对恢复r4/backup原两文件、depmod、modprobe正常CAMSS并恢复服务；r2/r3已走通，勿重跑带已有state的部署脚本。用户空间签名r29/r24七包仍391；整个平台原两CAMSS/SG模块及原缺失三模块/FW记录仍390，配boot366 SHA c3e4e9c85d80c8ec37605cd522cf716525ae5ebe4fa801342dbf7586c292d924。restore-files.py --offline-files-only只恢复文件/depmod，非切换已加载代码，不全量重装778模块。

## 下一步和完整范围

真实硬件错误／未知完成的并发恢复仍未实测；不能把提交前局部拒绝或模型故障当作硬件fault证明。继续原厂Gamma/LTM/CCM完整IQ与reference/kernel363/REMAINING-CAMERA-SCOPE.md全部：第五2MP身份/mux、多模式、动态帧长/防频闪、几何/多摄同步、连续AF和光学画质。仍1:1 NV12/NV21 IQ旁路，异步implicit-fence发布/缩放未证明；不因局部隔离完成缩小总目标。低光照后做相关标定，旧SSC间歇EPERM/daemon4未宣称修复。

保留373/375/376/379启动与ACK、381未知DMA/reset、388 DMA-only SG禁sg_page/sg_phys及自有IOMMU别名、377/378失败审计、383 Unicorn全局MEM_READ破坏ThumbIT/SP。private=/mnt/e/edk2-samurai-out/kernel393及前序；FW/HAL/ASM/CDM/全日志/图像/个体配置不公开。公共mirror=/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150，仅本地提交、不push/PR、保留其它改动。
'''
start=text.index('Image363源');end=text.index('\n\n## 下一步',start)
text=text[:start]+'''Image363/release7.3.0-rc6-rmx1931-samurai-k363+、boot389/logdump365、原qcom-camss复合模块和SG/helper、7SID/5IOVA板级DT与原厂FW保持；具体摘要／来源见源锁、393 README及archive/NEXT-SESSION-through392-2026-10-21.md。当前只是core/adapter新pair，不是完整Image重建；模块总781不变，新SG owner API不可换回旧SG配现adapter。

五libcamera r30/config-stack r25保持，用户空间维护源libcamera391-ipe-r30-built；391四摄／RAW／隔离IPA／PipeWire与六IPA签名证据复用，无需重建包或重复全矩阵。

393 pair回退：先停消费者并确认DMA/owner0，卸载qcom_camss→adapter→core，成对恢复r4/backup原两文件、depmod、modprobe正常CAMSS并恢复服务；r2/r3已走通。不得重跑已有state的worker。用户空间旧七包仍391，整个平台原CAMSS/SG与原缺失三模块/FW记录、boot366仍390；细节见归档，restore-files.py只恢复文件/depmod，不切已加载代码，不全量重装778模块。'''+text[end:]
start=text.index('18个实际核心');end=text.index('\n\n只正式替换',start)
text=text[:start]+'''18核心/DMA＋10实际device_work用例均ASan/UBSan通过，保留未知MAP/FRAME/UNMAP引用；固件/MMIO provider不外推硬件错误。ARM64 W=1/-Werror诊断0。首构建缺modpost依赖，补媒体依赖后通过；SG/m2m helper未变，未替换。'''+text[end:]
start=text.index('三个失败窗口');end=text.index('\n\ncurrent-state',start)
text=text[:start]+'''失败均保留，核心源/模块未变：r1误判静态device应消失，旧文件没替换，独立恢复原平台/桌面；r2 probe瞬时owner1未等待，自动回退；r3客户端offset16无额外空间，peer两帧已成功但同fd修复QBUF失败，自动回退。r4用offset0补齐通过。细节见attempts-validation和README，不重跑已有worker。r3两帧不计入r4的53，全尝试日志共56帧。392旧132已在正常卸载前归档，各模块epoch不得混算。'''+text[end:]
text=text.replace('，无需重建包或重复全矩阵。','。')
(ROOT/'NEXT-SESSION.md').write_text(text)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续active多摄/ISP目标。读WORKING-BOUNDARIES.md、NEXT-SESSION.md、reference/kernel393/README.md。393核心显式区分提交前安全局部拒绝，不按errno猜；未知MAP/FRAME/UNMAP仍全局恢复/保留引用/resetACK。core+adapter匹配pair已正式安装，source354 branch samurai-ipe-errors393/64aaf4f78c05f0912e658780294fbded531d87ce干净，访问先mounted_build。18核心＋10实际device_work模型、ARM64 Werror通过。r4局部别名错误不影响peer两帧，同fd可在peer session存活时STREAMOFF修复而不重启后端；并发取消及默认四摄各12通过。新epoch jobs55/completed53/cancel1/failed1/first_error=-22，fatalfalse，旧392累计132已归档。失败r1静态device存在检查错、r2 probe瞬时owner1、r3客户端offset16无额外空间，均审计保留；r1恢复、r2/r3自动回退通过，r4保持新pair。所有worker/client/collector终态，资源回收/服务恢复/taint0。Image363/boot389/logdump365/板级/原qcom-camss与SG/FW/r30-r25保持，无重启或刷写，guard390/原密钥。下一步真实硬件错误或未知完成并发，原厂Gamma/LTM/CCM完整IQ及363全范围第五2MP/模式/帧长/几何/同步/连续AF/光学。仍IQ旁路，不能把输入拒绝当硬件fault证明。关灯黑噪点按低照度解释，整体未完成。\n')
