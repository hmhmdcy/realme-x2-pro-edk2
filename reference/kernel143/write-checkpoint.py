from pathlib import Path
import ast
import json
import subprocess

root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel143';out=Path('/mnt/e/edk2-samurai-out/kernel143')
health=json.loads(ref.joinpath('rollback-health-validation.json').read_text())
runtime=json.loads(ref.joinpath('rollback-runtime-validation.json').read_text())
latency=json.loads(ref.joinpath('threaded-console-latency-validation.json').read_text())
startup=json.loads(ref.joinpath('startup-irq-idle-validation.json').read_text())
assert health['current_kernel']==140 and health['taint_values']==[0] and health['counters_unchanged'] and health['desktop_pids_unchanged']
assert runtime['new_boot_verified'] and runtime['boot132_and_logdump140_readback_exact']
assert latency['error'] is None and startup['trace_stream_loss_free']
assert not root.joinpath('sessions/143-threaded-console-live-regression-and-rollback.md').exists()
counts=health['counts_after']
count_text=f"DPU{counts['dpu_timeouts']}/DSI{counts['dsi_errors']}/GPU{counts['gpu_faults']}/WARN{counts['warnings']}/TXprepare{counts['tx_dma_errors']}"
summary=f"阶段143线程化EUD候选已编译并实测：16项实际函数宿主测试通过，77字节日志调用0.540ms（旧140为73.346ms），异步发送期间CPU0有36次中断、最大事件空档6.417ms。97.563秒无丢失启动追踪DPU0，却有持续DSI FIFO/MDP欠载；恢复到启动管理器时F1确认回执缺失，候选拒收。已只刷logdump回退#140/software132，boot/logdump/liveDT/GPT18/persist/770模块及来源全通过；临时服务和自建trace已移除。回退后{health['elapsed_seconds']:.3f}秒8次观察桌面PID、taint0与计数不变，累计{count_text}。显示、136迟发CCU GPU和充电控制保护仍未验收，goal active。"
session='''# 阶段143：线程化控制台实机回归与140回退

2026-10-12，完整系统目标继续 active。

'''+summary+'''

## 已做的最小修改和证明

从实际140基线仅修改 drivers/tty/serial/eud.c。完整Git差异对比证明其他源码字节相同，139未提交TX回收、140诊断、内核配置保持。普通打印改为nbcon线程；TTY发送与关闭共享互斥锁，UART IRQ锁只保护完整4字节帧和RX收集。200us寄存器等待、2ms帧节奏、RX/F1/journal代码保持。旧原子回调仅允许最终不安全panic路径，没有实机panic验收。

16项实际函数宿主模拟在普通编译与ASAN/UBSAN下通过，checkpatch零错误/警告；Image、770模块、DTB构建通过，模块和DTB与132字节一致。宿主3.2ms临界区上限是模拟结果，不能写成实机最长关中断时间。候选镜像及源码均保存，禁止把构建成功解释为完整功能成功。

## 实机结果与拒收

旧140部署前停机首次触发一次 ida_free 编号1重复释放警告，taint512，链路包含 slim_unregister_controller、slim_pd_status、pdr_notifier_work。完整旧日志和检查保存；全部远端离线、桌面/PCM停止、模块分区核对通过后，仅对这一具体旧boot的已知警告允许一次切换，未把taint改为0或宣称该错误修复。

候选143首次启动追踪97.563秒、20样本、8CPU零丢失。DPU timeout0、GPU fault0、WARN0、TXprepare0；188条包含dsi_err_worker的日志含限流提示，不能等同物理故障总次数。status=c对应FIFO错误与MDP FIFO欠载，驱动会软件复位DSI。完整trace有884组kickoff/PP完成，没有看门狗超时，但不能据此接受显示；942组普通桌面GPU提交/刷新/退休也不能替代136的专项迟发CCU故障验收。运行核对时197条DSI日志，桌面停止前累计199，随后停止。

在桌面已停止、屏幕空闲后，实际 pr/eud0 与发日志进程临时固定CPU0，发送77字节INFO一次，再过滤第二条；第一条完整发送日志出现后才切换过滤，最后恢复两处affinity、ignore_loglevel=Y与consolelevel1。日志调用A0.539897ms/B0.188490ms；A异步发送窗口79.887ms、36次CPU0 IRQ、最大CPU0事件空档6.417ms，原140同长记录调用73.346285ms。两个发送日志CRC及追踪零丢失验证通过，两条INFO均留在dmesg，B不进入发送日志，计数/taint不变。没有主机收到全部帧的确认，也没有直接测得最长IRQ关闭区间。该单条跨boot比较确认调用者长阻塞改善，不能证明原始显示故障完整因果。

回退停机又出现70次TXprepare失败，首诊断state=DOWN、qmi1、channel/device/sg/config_sg全0、len8；70条限于0.2秒内，全部远端离线后不再发生，无BUG/Oops/panic/新增GPU故障或停止屏幕后显示错误。没有重放停机；完整记录后只允许这个确定的失败范围用于恢复，未接受为无报错。与139/141生命周期问题相符，源代码仍未修改。

候选143进入bootloader的一次90 02 OUT已完成，之后USB断开，未观察到F1确认。独立核实同一私有手机身份和msmnile产品已处于fastboot，再核分区64MiB与回退镜像哈希，只刷logdump恢复原140；没有重复F1、重新停机、全刷或擦除userdata。F1确认丢失也是候选拒收项，即使未修改RX或F1函数仍会受到新异步时序影响。

## 当前状态和下一步

当前实际手机#140、release k132、software132，身份只使用私有kernel143/embedded-boot-id-private.txt或phone k143-rollback140-runtime。143/rejected-boot-id为候选143，143/source-boot-id和142/embedded均更早旧140启动，不能混用。回退完整分区/来源核对及8样本观察通过；启动早期采样桌面未出现，后续自动出现且观察PID稳定。当前累计'''+count_text+'''. 不满足无报错。

C:/WSL树 /home/cy122/pmos-samurai-kernel136/kernel 仍为拒收的143源码/Image，modules-root143保留；手机140镜像在私有kernel140。下一候选先明确基线，不能混用源码和产物。143所有部署、两次停机、启动recorder、A/B和回退均终态，禁止重放。临时OpenRC服务/link/pidfile、自建启动与A/B trace均已移除，默认display/radio配置随正常新boot恢复。

优先离线检查异步控制台退出时F1最后一帧的发送/排空合同，以及打印时序变化与DSI欠载的联系；现有候选不能再次直接部署。保持83ms看门狗与原有MMIO节奏，不通过加超时、屏蔽错误或全局缓存刷新宣称修复。SLIMbus需独立验证控制器注册/注销生命周期与DOWN时发送路径，避免重新引入上游已删除的tx_lock/ctrl->lock ABBA。

GPU136迟发CCU fault仍开放。充电138已确认2节目标8.725V与恢复阈值8.525V及终止状态，零小电流可能是阈值内尚未恢复；当前132没有134 USB额度驱动，持续控制/温度保护/失联安全尚未验收。

## 查到的上游资料

- [Linux printk文档](https://cdn.kernel.org/doc/html/latest/core-api/printk-basics.html)：legacy控制台同步输出可能导致长期关中断，nbcon线程输出是推荐迁移方向。
- [nbcon控制台接口](https://www.kernel.org/doc/html/next/driver-api/tty/console.html)：ownership/unsafe和设备互斥合同，device_lock必须限制迁移；仅迁移API不足以证明本板恢复协议正确。
- [DPU忙标志清零后误超时补丁](https://www.mail-archive.com/dri-devel@lists.freedesktop.org/msg632873.html)：讨论的是busy已清零的竞态；141/142实际超时busy仍1，不能直接当本机解法。
- [SLIMbus描述符回收讨论](https://lkml.iu.edu/2610.0/02660.html)：作者明确仅静态分析与编译、没有目标硬件；本机139采用实际函数和实机证据，不能直接复制推进head的做法而释放较早在途槽位。
- [Mesa Freedreno](https://docs.mesa3d.org/drivers/freedreno.html#cache-hierarchy)：CCU缓存和GPU流水线解释迟发错误，转储估算位置会晚于真正触发命令；仍需自身页表/BO/命令流证据。
- [MP2650原厂资料](https://www.monolithicpower.com/en/mp2650.html)：2–4节降压或升压充电器、保护/状态与限值合同，充电观测不等于控制验收。
- [Realme官方Android源码](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source)：原厂面板和充电顺序核对来源，不能整体移植为当前主线补丁。

公开reference/kernel143仅放脚本、补丁和去身份验证摘要；原始日志、内核镜像、ID、地址和数据保存在私有edk2-samurai-out/kernel143或phone /var/lib/samurai。

约束保持：不配对蓝牙、不新振动脉冲，不写充电FET/OTG/OTP/unseal，不全刷userdata，不提交推送。显示/GPU/充电与完整系统目标未完成。
'''
root.joinpath('sessions/143-threaded-console-live-regression-and-rollback.md').write_text(session)
next_text='''# Realme X2 Pro继续检查点（阶段143，2026-10-12）

'''+summary+'''

先读[阶段143](sessions/143-threaded-console-live-regression-and-rollback.md)和reference/kernel143的threaded-console-latency-validation.json、startup-irq-idle-validation.json、rollback-runtime-validation.json、rollback-health-validation.json。当前手机#140/software132936包770模块；身份仅用私有kernel143/embedded-boot-id-private.txt或phone k143-rollback140-runtime。143/rejected是已退出的143候选boot，143/source与142/embedded是更早140，不能混用。143所有动作终态，禁止重放。临时启动服务/link/pidfile和自建trace均已移除，A/B参数/两处affinity恢复。

WSL /home/cy122/pmos-samurai-kernel136/kernel仍为拒收143source/Image，modules-root143保留，140原镜像在私有kernel140；不能把手机140与构建树143混为同一基线。E118访问需ensure和相关读取同一WSL调用，原C VHD不动，空间紧不复制全树/rootfs。

下一项先离线核查EUD线程退出/最后F1帧排空与显示DSI欠载时序。143降低单条调用者阻塞已实证，但产生持续欠载且丢F1确认，不能直接重新刷入或接受。保持原83ms看门狗和200us/2ms MMIO节奏，禁止仅屏蔽日志/加超时宣布成功。普通942次GPU提交不能代替136迟发CCU专项。

SLIMbus现有139未提交TX槽位/TID/PM回收保留。旧140关ADSP触发IDA重复释放警告；143关闭时70次DOWN/NULL prepare，全部现场已封存，后续离线核查注册标志与通知/PM时序，不猜测重加tx_lock造成ABBA。首次runtime_resume丢弃power_up返回值仍候选，直接return ret可能造成sticky runtime_error阻止QMI恢复。

GPU136两次延迟CCU READ TRANSLATION尚未修，gpu_probe_allowed=false；禁止重放旧33场景/全局debug/全局缓存刷新。充电138只读24交易已经终态；8.525V恢复阈值与8.725V目标解释当时低电流，当前132无134 USB额度驱动，温度/输入/保护/失联与持续控制仍待办。BT不配对、振动不新脉冲，不写FET/OTG/OTP/unseal、不全刷userdata、不提交推送，私人材料不公开，完整goal保持active。
'''
root.joinpath('NEXT-SESSION.md').write_text(next_text)
root.joinpath('NEXT-SESSION-PROMPT.md').write_text('''# 下一会话短提示词

继续Realme X2 Pro postmarketOS适配，显示、GPU、充电无报错并达到安卓般可用。先读NEXT-SESSION.md和sessions/143-threaded-console-live-regression-and-rollback.md。当前实际手机已回退#140/software132，身份只用私有kernel143/embedded-boot-id-private.txt；WSL源码/Image仍为拒收143，必须明确构建基线。143线程化日志实机调用73.346→0.540ms、CPU0异步发送有中断，却持续DSI欠载且退出F1确认缺失，候选已拒收，所有停机/切换/recorder/A-B/回退均终态，禁止重放。优先离线核查控制台最后帧退出合同和欠载时序，保留139回收；136CCU及充电控制保护仍未验收。保留Android/数据/GPT/NV/F2FS及快照，BT不配对、振动不新脉冲、不全刷userdata、不提交推送，私人材料不公开，goal active。
''')
for name,target in [('README.md','sessions/143-threaded-console-live-regression-and-rollback.md'),
                    ('linux-port/README.md','../sessions/143-threaded-console-live-regression-and-rollback.md'),
                    ('linux-port/docs/HARDWARE-STATUS.md','../../sessions/143-threaded-console-live-regression-and-rollback.md')]:
    path=root/name;text=path.read_text();head,rest=text.split('\n',1)
    path.write_text(head+'\n\n最新阶段143：'+summary+'\n\n详见[阶段143]('+target+')。以下为此前历史。\n'+rest)
path=root/'DOCS-INDEX.md';text=path.read_text();head,rest=text.split('\n',1)
path.write_text(head+'\n\n- [阶段143：线程化控制台实机回归与140回退](sessions/143-threaded-console-live-regression-and-rollback.md)\n'+rest)
path=root/'HANDOVER-NEXT.md';text=path.read_text();head,rest=text.split('\n',1)
path.write_text(head+'\n\n当前交接以[NEXT-SESSION](NEXT-SESSION.md)和[阶段143](sessions/143-threaded-console-live-regression-and-rollback.md)为准：手机已回退140，线程化候选143拒收；下方为旧历史，不是当前状态。\n'+rest)
for filename in ['source-preparation-validation.json','threaded-console-build-package-validation.json']:
    path=ref/filename;meta=json.loads(path.read_text());meta.update(deployed=True,candidate_rejected=True,rolled_back_to140=True,current_phone_kernel_build=140)
    path.write_text(json.dumps(meta,indent=2)+'\n')
for file in ref.glob('*.py'):ast.parse(file.read_text())
for file in ref.glob('*.sh'):subprocess.run(['bash','-n',str(file)],check=True)
report=dict(stage=143,current_phone_kernel=140,current_build_tree_kernel=143,candidate143_rejected=True,
    documents_latest143=True,all_operations_terminal=True,rollback_and_health_validated=True,
    script_syntax_pass=True,goal_complete=False)
ref.joinpath('documentation-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K143_ALL_TERMINAL_REJECTED143_RESTORED140_HANDOVER_WRITTEN')
