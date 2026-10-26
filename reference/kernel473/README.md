# 473：processed IPE Manager容量租约的底层候选与实测

初稿完成源码审查和[最小补丁](0001-camss-lease-manager-capacity-for-processed-ipe.patch)时尚未编译；随后独立源码准备及仅 core 增量构建通过；主线再完成隔离长焦1080p旧／新／旧实测，见[硬件结果](HARDWARE.md)和[独立验收](hardware-validation.json)。候选未永久安装。复用[448 原有 helper 与恢复契约](../kernel448/README.md)，只将获取条件从 `lensActive_` 改为 `lensActive_ || (processedEnabled_ && ipe_)`，获取和释放位置保持原样。未改 IPA／proxy、原厂 IQ、PLL、缓冲数、成功历史或 461 所有权检查。

## 候选依据和作用范围

[471 的旧／新／旧实测](../kernel471/ANALYSIS.md)中，tone 日志至 host 返回中位为 15.626／3.566／4.073ms，Pair 至成功 receipt 为 37.105／25.543／15.170ms。A2 旧基线自身已经明显变快，不能把 B 的短段结果解释为稳定吞吐修复。实际 FULL ioctl 事件显示 A1、B 多在 CPU0—3，A2 从 SOF10 起的最后 22 次 DQ 均在 CPU4；这是事件点观察，未保存 worker CPU 或本轮新鲜频率，448 的 capacity 只作历史分组。

长焦三段均没有已部署活动镜头，因此当前 gate 未获取租约。processed IPE 的 FULL DQ／QBUF、请求所有权与 host 同步 IPA 调用仍在同一 Manager 上运行，这些工作不依赖 lens 存在。扩展 gate 是与该调度观察相符、可独立比较的候选；源码和短段迁移观察均不证明它能消除缺口或改善热、功耗及持续录像。

实际 461 `camss_vfe.cpp` SHA256 为 `befec1da3743545652adc669cc649860d6840738e38a3798305d213b2e874b40`；私有缓存与挂载守卫后读取的候选源码一致。当前 `thread_capacity.h` 与 448 公共头逐字节一致，SHA256 为 `5801d89dcd326873df9d518df5a2667e5deeacf87bd0274bd1a241569bc9a463`。补丁基于这份源码，保留成员名 `focusCapacity_`，避免无关重命名。

## 独立源码准备和实际构建

[prepare-source.py](prepare-source.py)先计量 461 源码及可复用 output 共 575,326,015 字节、2156 个文件／链接，再复制到独立私有目录；没有共享 O 或硬链接。复制前后逐文件 inventory 核对，仅 `camss_vfe.cpp` 改动，补丁零 fuzz、零 offset；候选源 SHA256 为 `be3199aec5ad4c5ffc65043bded6ec85b37a3eeaf20db6087226543fc89ece19`。复制后余量 5,901,623,296 字节，高于 2GiB 预留。[源码收据](source-validation.json)中 `built=false` 是这一准备阶段的事实，后续状态见[当前 source-state](source-state.json)。

SDK 经独占交接并核实未绑定、无其它 compiler 后，[build-core.py](build-core.py)的 r1 定向构建 118.858 秒、exit0。计划只含管线对象、必要的版本生成／对象及 core 链接；实际版本内容没有改变，执行管线对象、版本生成及 core 链接三步。没有编译 IPA、proxy、base 或内核。[r1 原始构建收据](build-r1-validation.json)与[最终结果](build-validation.json)一致，SDK bind 已卸载并明确释放。

私有 core 为 51,259,496 字节，SHA256 `a21fcedde2f591f809a9c388a9a6ab78fa5072f33e06c91bbd55c8abf34cd97b`。461 原始源、core `9b352a12…` 及生成版本保持；旧 IPA `4c90047d…`、proxy `c7887708…`、签名 `f5c351bd…` 逐字节不变，0065 UAF 修复保留。这个结果只证明候选可构建，不证明 affinity 实际获取、恢复、性能或画质。

## 实际启动时序：Manager 租约不等于 worker 租约

| 源码链 | 已核实行为 |
| --- | --- |
| `CameraManager::Private::run/init/createPipelineHandlers`；`CamssVfeData::init` 379；`initIPA` 250—268 | Manager 初始化／枚举即可调用 `createIPA`。配置也会调用 `initIPA`；已有 IPA 直接复用。 |
| `IPAManager::createIPA`；`module_ipa_proxy.cpp.tmpl` 130—154；`IPCPipeUnixSocket` 27—50；`Process::start` 141—209 | 隔离 proxy 的构造函数立即创建 socket 并以 `clone3`／`execv` 启动进程。这早于 Camera start 内的租约获取。后续给 Manager 设置 affinity 不会重设已存在 worker 的 mask。 |
| `Camera::start` 1400—1427；`PipelineHandler` start／stop 契约 | Camera 通过 blocking invoke 调用管线，start／stop 运行在 CameraManager 线程，不是消费者调用线程。 |
| `CamssVfePipeline::start` 724—727、750、807—818 | IPE start、IPA start 均早于现有租约；获取在 `running_=true`、coarse/VFE streamOn 之前。非隔离模板的 `thread_.start()` 在 IPA start 内，也早于获取。 |
| 非隔离 proxy 模板 93—115；隔离模板 167—207 | 非隔离同步方法直接调用 IPA；异步方法投递到 IPA 线程。隔离同步方法经 IPC；等待期间 Manager event dispatcher 可重入。Manager 租约覆盖本线程实际执行的同步工作，不能据此宣称隔离 worker／异步 IPA 线程也被选核。 |

保持获取位置意味着本候选不调整已经创建的 IPA 线程或隔离进程。仅把获取点移到 `ipa_->start()` 前，也无法统一覆盖在枚举时已经启动的隔离进程，反而会改变非隔离新线程的继承范围，因此本补丁不这样做。

该租约是 Manager 线程的 affinity，不是逐请求调度属性。同一 Manager 上其它管线的事件、热插拔处理也处于这个 mask 下；其它进程和消费者线程没有被显式改动。持有期间若 Manager 新建用户线程或进程，它可能继承当时的 mask；本补丁没有给这类子线程单独设置或恢复 affinity，不能把现有 worker 不受后设 mask 影响外推为所有未来 worker 永不受影响。

## 条件、回退、并发与停止边界

- 有 lens 的现有路径，包括既有 RAW-only lens 行为保持；无 lens 的 processed IPE 新增资格。无 lens 的 RAW-only、无 IPE 的直接 processed 路径不新增获取。lens＋IPE 仍只调用一次 acquire，不叠加两个租约。
- helper 从当前允许 mask 读取所有 CPU 的 capacity，仅保留高于该允许集合最小值的 CPU；不硬编码 CPU4、4—7，不强改频率。容量缺失、同质允许集合、外部策略或 syscall 失败仍记录 status／reason，并继续原有相机路径，不新增 start 失败条件。
- 当前 handler 的 `active_` 在 start 拒绝第二个活动 camera；这不等于所有 libcamera handler／设备只能单摄。若其它 handler 在同一 Manager 也持有该 helper，thread-local 状态及 users 共享引用计数，最后释放者才恢复；本轮未验证物理多摄并发。
- 获取前的启动失败经既有 error→stopDevice，release 为 inactive；获取后的任意 streamOn 失败仍走相同清理。正常 stop 先置 `running_=false`、停队列、取消／完成所有权、停 IPA、关闭 lens、释放相关 buffer，最后释放租约；位置未改。非隔离 IPA stop 先停止并 join 自己的线程；隔离 IPA stop 不等于销毁 worker，worker 生命周期仍由 proxy 管理。
- 释放前若实际 mask 已被外部策略改变，helper 不覆盖该策略。运行中没有持续监视 mask 的新机制，`active` 也不能代替实际 affinity 读回。restore 读／写失败保留租约状态以便后续 retry；不能把 CAPACITY_STOP 出现本身当作恢复成功。所有者退出、跨线程释放、pending restore 与 cpuset 交集继续使用原 helper 语义，无新增热插拔并发保证。

448 已有生产头的宿主 ASAN／UBSAN、实际 ARM64 共 21 合同案例及无特权 syscall 恢复证据，本轮不重复编译它们，也不把旧 lens 实测当作新 processed gate 通过。本轮后续已在独立窗口固定这些载荷完成旧／新／旧，实际Manager mask及正常stop恢复通过；同一Manager重复配置／重开仍待验证。worker CPU 若仍缺失，继续明确保留该边界。任何通过都仅覆盖实际跑过的路径，不能代替多摄、光学或持续录像验收。

源码审查／准备阶段没有 SDK bind；随后按独占交接仅构建上述私有 core。以上源码／构建子任务零SSH或设备动作，未改共享源码、build或Git index；主线之后的实机与NAV更新按独立收据记录。私有审查原件及候选二进制仅在 `E:/edk2-samurai-out/kernel473`。

## 本轮实机增量

固定旧proxy的长焦mode2 1080p旧core／新core／旧core各32帧，96消费／96IPE严格同SOF通过；99原始回执保留各段1条stop未入队失败观察。B的live Manager mask动态选为4—7，全部35次FULL QBUF／33次DQ在CPU4／6；正常stop经原helper syscall读回恢复0—7，没有外部poststop探测。

Pair→receipt中位为38.272／29.403／38.389ms，B的29张数学样本最大32.554ms；两旧段各3缺口、B短段无缺口，支持本窗口Manager gate改进。该结果不证明长期无缺口、功耗或worker CPU改变。原sensor／正式栈／PM／服务及R8已恢复，worker退出、fault0／taint0；[HARDWARE.md](HARDWARE.md)给出全部计数、时间及范围。

下一先组合本core与451已验证proxy做功能验证，补长焦1080p native／隔离及独立LTM因果，再收敛可回退包；控制阶跃工具见[472](../kernel472/BUILD.md)。同Manager重开、原生／其它新增路径、光学／AF、编码录像、长期与多摄仍按实际范围验证。
