# 保护查询：现 provider 内的一次原始帧观察候选

本叶补足的是传输与证据出口：0050/0052/0056之前在任何I/O前被普通六命令API拒绝，已有离线codec没有总线调用；保护provider的五条完整帧此前只解码后丢弃。现以实际R8三份文件为基线，新增root-only显式一次固定batch与纯缓存show。当前只离线实现、21项实际函数检查和私有单对象W1/Werror通过，未link模块、安装或查询手机。

## 默认行为与准确来源

基线来自`charging-session-20261023/r8-source-integration`，不是旧历史charger替代源：provider `5d77236d…45b6`，gauge-i2c `897a961d…01e77`，gauge-protocol `0903f3fa…75f0f`。本叶完整源码、逐文件patch及source-pins绑定这些确切字节。旧R8源码、白名单调用、服务及现手机完全不改。

普通`sm_mac_data_size`仍只含0001/0051/0053/0054/0057/0071；普通`sm_gauge_mac_locked`对新三条仍在I/O前拒绝。新专用observe尺寸表仅额外允许0050/0052/0056，各4-byte payload、length8（0056第4byte保留仍须读取）。两入口共用原1–1.5ms选择等待、36-byte两消息读与一个校验主体，未复制现有TCA codec或引入任意selector。checksum仍在34、length在35、命令回显和精确长度均验证。

默认probe和每次PRESENT/HEALTH的原五查询保持，旧`sm_protection_read/get/protection_state_show/probe`等主体逐字不变；charger仍用其原段锁采温度/整包/0A/0C/0071。未把新三查询加到poll，也未变更保护Good、温控、TCA、Full、timer、旧fault或充电策略；诊断error不覆盖普通`last_error`。没有0055、NVM/OTP、FET/解封、PF_EN、REG14或裸I2C工具。

协议来源仍是已固定本机OEM legacy FFA5选择/等待/回读语义，以及缓存官方TI SLUUA65E对新三帧尺寸的定义；固定OEM源码没有实现这三状态的本机分类。0x2719仅是已观察扩展身份，不能冒认标准2610精确型号。本叶不置compatibility_verified，不解释新三状态位，不把帧校验通过或全0解释成正常TCA/安全合格。

## 一次证据接口

详见`protocol.json`。未来仅当实际新provider被root明确安排接入后：

- `/sys/devices/platform/samurai-gauge-protection/mac_evidence_capture`，0200；只接受`capture`及可选末尾换行。
- 同目录`mac_evidence`，0400；读操作始终只格式化缓存，初始attempted=0也不会发I2C。

合法capture在原`p.lock`内先设置attempted，然后一次持`I2C_LOCK_SEGMENT`完成：0001 → 0A前 → 0051/53/54/57 → 0050/52/56 → 0A后。0001必须先通过完整36字节、payload2/length6和2719值；否则不继续。段锁内只用既有unlocked primitives，禁止调用会再次拿adapter锁的外层接口。没有额外线程/定时器/自动重试或恢复动作。

任何选择/读取/回显/长度/checksum错误立即停止，保留已读原件和真实error/stage。失败也消费该实例唯一attempt，后续合法capture返回EALREADY；非法输入在claim前拒绝。不会通过自动重载来重武装。show与普通Health同用p.lock；无锁跨join问题，因为本叶没有新增异步worker。原devm属性组最后创建，移除时在provider/gauge引用和内存释放前撤销并等待活动sysfs访问，原device link/总线生命周期沿用。

每帧记录真实selector/read/validate尝试标志、返回值、BOOTTIME时间点与full_read。只有两条消息完整完成后才称为36字节原帧；即使随后的echo、length或checksum失败，也保留全部36字节。负值或短transfer可能已改变缓冲区，但内核接口不能提供可信的已读字节数，因此显示`raw=unavailable`，不把填零或部分缓冲冒称完整包。

header另记录0A前后原值/有效标志/时间，以及批次起止、最后stage和尝试数。`stage=6/error=0`只表示固定协议序列完成；本batch不比较0A前后，相同或不同都照实保存，不等于同一瞬时原子快照、一致充电模式或TCA因果。后续若接入旧classifier，仍须沿其规定mask比较并单独标记stable，不能从本次error0推定。所有输出仍带`compatibility_verified=0`，还需真实本机包及自然TCA/独立Full关联才能讨论分类。

一次性是次数上限，不是可硬中断的传输时限：同步I2C受adapter超时和内核调度约束。没有新增会在挂起/恢复时自动重跑的工作。纯缓存show在任何阶段都不触总线；本轮不以软件测试认证实机PM或协议兼容。

## 受影响验证与构建

`test-observer.py`提取实际provider结构和四个函数，直接编译候选headers；仅Linux/I2C/sysfs边界fake，ASan/UBSan+pthread。21项覆盖：默认show/非法输入零I/O；普通API仍拒新三；专用三条4/8读；旧六实际报文各回放一次；控制/NVM/0055等零I/O拒绝；正常五查询不增；一次claim；选择/读取/短传输及完整坏包保留；0001尺寸/2719门；0A前后错误与变化；PAGE_SIZE最大数字边界；两个capture竞争与另一真实段锁客户端线程join。旧149分类和其它大套只绑定旧收据，没有重跑。

新三回包是明确合成IO向量，不能冒充本机实包。首次测试误把既有0054包含在“新三条应拒绝”循环中，编译通过后断言失败；原binary/log与`test-attempt-r1.json`保留，改为精确三数组后21项通过。没有将该fixture错误改写成生产缺陷或删除失败历史。

私有单对象复用原284 Ubuntu/root的固定32GiB卷guard及原k363 saved command，W1+Werror真实rc0、零诊断；原source/config/旧obj/headers/cmd逐项不变。只编译`samurai-gauge-protection.o`，object SHA `939aee637dc018b8326a7efe5c5e4098bb9cc903eaf651dd0aefff6d0afa1965`。没有make、ko/Image链接、SDK、设备、Git或长期anchor；构建已wait终态，卷未卸载。

## 未来替换范围

当前实装保护模块仍是R8原件：`/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko`，SHA `75b97e0d…783c7`，loaded note `930e0e1f…6fe76`，manifest `320316c3…c10a1f`。这些旧身份不能冒用于本候选。将来至少需root单独生成真实新protection ko/intree+ABI/来源收据及对应manifest，再按当时真实charger引用/停充和模块生命周期安排替换；本轮没有ko或可部署cohort，也没有提前改服务、USB、charger、boot/Image或现manifest。
