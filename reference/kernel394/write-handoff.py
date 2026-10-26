from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
text='''# 当前检查点：394（ACK丢失恢复失败已取证，新启动四摄恢复，目标active）

先读WORKING-BOUNDARIES.md、reference/kernel394/README.md。393交接归档archive/NEXT-SESSION-through393-2026-10-21.md。完整多摄/骁龙ISP目标仍active，用户关灯黑场/噪点不单独判故障，光照相关校准后做。

## 故障实验和实际边界

本轮只有一次受控ACK丢失实验。临时核心从私有路径加载，正式模块/板级/FW/包/配置未写；测试宏仅在临时构建启用，维护源还原393且干净。两个session各完成预热帧后，客户端设置一次开关，已过尺寸/type/opcode/token/成功状态校验的真实帧ACK被消费但不唤醒等待者。超时/复位原路径未变，没有改DMA地址、命令载荷或IRQ mask。7解析器模型ASan/UBSan和ARM64 Werror通过。

旧boot390的ramoops：5780.728684丢ACK；5785.871385超时-110，queued1/pending1；随后pending1/request_mapped1/input_ref1/output_ref1保留；A5 stopped cooperative0/block_reset1；最后reset_acks3,3，pending0/request_mapped0，但input/output引用仍1。之后无完整DMA aliases retired或PM release记录，设备自行重启。故只证明真实完成超时、引用保留和两路IPE复位ACK，完整恢复实验FAILED，不能外推客户端传播/第三上下文拒绝/重开/退映射/PM完成。根因和精确故障指令未证明。

旧worker13432已因已核实启动变化消失；旧client/collector同属前启动，不可能仍运行。但state/launch/运行日志/collector-result未完整落盘，不能伪造worker terminal成功或把文件缺失当具体执行点。只留阶段化文件和collector-ready。完整206061B console-ramoops及新启动dmesg私存kernel394/recovery-collected，pstore未清空。勿重启旧worker或重复同一注入；下次故障实验前提高文件/目录fsync与主机侧预保存，并先解决恢复顺序。

## 新启动身份与正常恢复

当前必须host394，走private394/postboot-adoption-private.json与新guard=/var/lib/samurai/k394-recovered/boot-id-private.txt。host394.raw_ssh仍原USB密钥/known_hosts，未重授权。旧390guard和host393已不适用。adopt-recovered-boot已读回boot389/logdump365精确匹配、正常393两模块磁盘/加载note及qcom-camss/adapter note匹配、四私有配置SHA保持、test参数不存在、taint0、probe未启FW。新启动不是重新刷写，临时测试核心随重启消失，正常393从原磁盘自动加载。

新启动恢复worker6370在/var/lib/samurai/k394-camera-recovery-r1，已terminal，client/collector也结束。默认r30四摄GStreamer各12，共48direct/错误0，fixture恢复，无LD_LIBRARY_PATH或私有配置覆盖；新epoch jobs/completed/direct48、starts/stops4，failed/cancel/first_error0。旧393计数55与旧394故障2预热+丢ACK单独保留，不跨启动混算。

当前CPU/IRQ/PM/backing/map/import均回收；ICP/CAMSS/双CCI suspended，17clks0、9rails disabled/users0。PW6411/WP6417各一/uid10000，owner_refs53是桌面普通CAMSS句柄，m2m users0/fatalfalse。正常恢复窗口无dump/timeout/newfault，taint0。正常状态通过不改写原故障实验失败，也未全面复查SSC/旋转或宣称旧EPERM/daemon4修复。

## 维护源、分层及回退

WSL Ubuntu root，源码/build访问先reference/kernel284/storage.py::mounted_build()；现有32GiB ext4 backing不可格式化或重建。驱动source354仍branch samurai-ipe-errors393、HEAD64aaf4f78c05f0912e658780294fbded531d87ce，干净；临时测试差分在394/temporary-ack-loss.patch，正常源无测试宏块。正式core e22253916088e58a221c1948f025c44c939c819310c7d3f67106053dd39502f6，adapter ff2bfa7a9439b2ef67087ff6f5db8c9d26e9a92596cd1f63b14c3a047111d4c1；两者仍393匹配pair。

Image363/release7.3.0-rc6-rmx1931-samurai-k363+、boot389/logdump365、DT389静态7SID/5IOVA、原qcom-camss复合模块/SG/helper、FW与r30/r25保持。用户空间维护源libcamera391-ipe-r30-built；完整摘要和来源见源锁/393归档，不重做无关全量核验。新SG owner API不可混旧SG；模块总781不变。测试核心b40200a0e9903451a8528a29d1df535b17b5c25adf1d6882f196e0b0aeeee2a3仅私有产物，未写/lib/modules，当前无test_drop_frame_ack参数。

393局部拒绝隔离仍生效：明确REJECTED只限作业transfer MAP前且临时映射/引用清理成功；已尝试MAP和未知完成默认RESET_REQUIRED，不能按errno猜安全。本轮没有为绕过重启放松DMA所有权或改正式恢复实现。393 pair回退备份仍设备k393-deployment-r4/backup和private389；391旧r29/r24七包、390整个平台/boot366回退资料都保持，本轮没执行它们。不要重跑已有state的部署脚本。

## 下一步，不缩减完整目标

优先审完原厂强制/恢复停机与资源deinit间接链，定位全局ICP块复位、总线可访问性和DMA退映射顺序。394/recovery-source-audit.json核对已保留Realme GPL9668fcdc6ec15be7a10d66f7b93c347829e0fdb6的352/hfi.c及355/cam_icp_hw_mgr.c摘要；直接恢复先IPE/BPS reset，CPU disable为WFI轮询/本地CSR，所查函数无直接ICP_BCR。间接资源退出未审全，不能宣称OEM全路径从不复位。375正常路径去掉额外全局BCR后实机通过，394错误路径仍在该边界重启，这是下一候选焦点，非精确机制证明。必须保留可证CPU停机、新IPE复位ACK和未知DMA引用，再做针对性实机验证。

然后原厂Gamma/LTM/CCM完整IQ及reference/kernel363/REMAINING-CAMERA-SCOPE.md全部：第五2MP身份/mux、多模式、动态帧长/防频闪、几何/多摄同步、连续AF和光学画质。当前仍1:1 NV12/NV21 IQ旁路，异步implicit-fence发布和完整校准未证明。保留373/375/376/379启动ACK、381未知DMA/reset、388 DMA-only SG禁sg_page/sg_phys及自有IOMMU别名、377/378失败审计、383 Unicorn全局MEM_READ破坏ThumbIT/SP。

private=/mnt/e/edk2-samurai-out/kernel394及前序；FW/HAL/OEM源码/ASM/CDM/全日志/图像/个体数据不公开。公共mirror=/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150，仅本地提交、不push/PR、保留其它改动。
'''
(ROOT/'NEXT-SESSION.md').write_text(text)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续active多摄/ISP目标。读WORKING-BOUNDARIES.md、NEXT-SESSION.md、reference/kernel394/README.md。394临时核心一次丢真实已校验帧ACK：5.142701s超时，pending/FW映射/两个引用保留，A5强制reset后IPE ACK3,3，但完整退映射前设备重启，实验失败，根因未证明，不重复同一注入。ramoops已私存，旧state/log未完整落盘，勿伪造终态；旧进程因新启动结束。当前新guard=/var/lib/samurai/k394-recovered/boot-id-private.txt，必须host394/新adoption，旧390guard/host393无效，原密钥未重授权。boot389/logdump365读回匹配，正式393 core/adapter和四私有配置保持，测试参数消失。新启动四摄各12共48direct通过，当前计数48/failed0，资源回收/服务恢复/taint0，恢复worker终态。source354仍samurai-ipe-errors393/64aaf4f78c05f0912e658780294fbded531d87ce干净，访问先mounted_build；无正式源码/模块/DT/FW/包变更或刷写，r30/r25保持。下一步审OEM强制恢复和资源deinit全链，解决全局ICP_BCR/总线/退映射边界，不能删reset或提前归还未知DMA取巧；保留ACK/引用证明后针对性验证。继续完整IQ及363第五2MP/模式/帧长/几何/同步/连续AF/光学全范围。低照度按关灯解释，总目标未完成。\n')
