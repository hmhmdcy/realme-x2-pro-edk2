# 蓝牙完整功能与现有修复固化

2026-10-23。目标尚未完成。当前 k363 普通 LE 核心已由现场 MGMT 确认支持且启用；手机已实际完成 GATT 服务和广告注册。已配对漫步者的软件连接/重连和低音量音频发送通过，用户反馈没有听到，声音验收未通过。GATT数据、新配对及其它角色仍待验收。

**最新范围为静态修复与离线验证，暂不做蓝牙实测。** [六类修复及结果](../bluetooth-static-fixes-20261023/README.md)已完成两项P1（serdev注销竞态、GATT诊断异常截断清理）及四类P2的源码修复。内核候选保留PM r2并补齐退出/分配失败路径，两个k363对象Werror编译通过；GATT29项、主机/音频9项及radio故障注入通过。内核/radio按独立候选交付，尚未签新包或采用；旧签名包和历史验证仍保持原含义。[修复前审查](../bluetooth-static-review-20261023/README.md)保留为历史依据。

## 当前串行窗口

已与“验证441候选双遍与LTM链路”和“梳理可并行的适配工作”直接协调。相机451/452终态、恢复正式440/434组合后，蓝牙只做了一次只读基线和有界 GATT 服务实验；未刷写、重启、安装包或做整机 PM。r2恢复核对通过后明确交回充电。

相机457终态后，用户USB重插触发PMIC FLOAT源识别问题。充电会话明确交接约10分钟的r6安全INHIBIT窗口：独立gauge保护正常、硬件充电禁止且原100mA预算保留。本线读回manifest `944f2d91f66c5642bbcb130c3ef59e022ca6652e599401908f8528a29d34202d`，完成漫步者r1–r4及恢复核对后已明确交回。充电会话随后报告R7已同Image正常启动、原key严格验证恢复，保护及正式相机配置通过，继续持图标复测窗口，之后交相机；本线未独立读回新boot/manifest。**用户现要求先停止蓝牙实测，修正静态问题并离线验证，本线不加入设备排队。** 已与两线同步；本轮只在蓝牙独立source-view/O编译两个受影响对象，共享源码/构建输入、SDK和相机候选未改。

充电r5曾在SDP100mA条件下RTC实际睡眠3396秒且USB未及时恢复，旧raw true已撤回；用户操作后原boot、原key的NCM/SSH恢复。该次没有追加整机休眠，旧CDP睡眠结论不能套到该SDP现场；当前蓝牙实测按用户要求延期。

## 本轮实机证据

[只读基线](runtime-baseline.json)对应r5交还时状态：exact k363、taint0，三只蓝牙模块磁盘和已加载build-id一致，BlueZ运行、一个adapter，关电/不发现/不可配对/不可发现，一个既有paired且无连接；MGMT只读原生查询确认LE supported/enabled。GattManager和AdvertisingManager均存在。BNEP/UHID文件及加载均缺失，原HIDP文件存在。

模块、蓝牙helper和TFTP现场文件未被APK登记，包括 `/usr/sbin` 到 `/usr/bin` 的实际路径；尚未做采用安装。PulseAudio17实际运行，pactl原始记录有 bluetooth-policy、bluetooth-discover、bluez5-discover 三模块。旧摘要仅用 `pulse-*/modules` 文件glob计数0，不能据此判插件缺失；公开摘要已从缓存原件改正，无需重新操作设备。地址、boot ID、密钥摘要及原始HCI/日志仅私存。

GATT r1被Properties.Set错误签名ssb拒绝，尚未改变Powered。只将Boolean设为variant_level=1，严格GIO跨进程单项验证收到ssv；旧九项API结果继续保留各自版本摘要。[手机脚本及验证](../bluetooth-le-peer-20261023/README.md)。

[GATT r2结果](gatt-r2-validation.json)：约1.46秒完成上电、GATT和广告注册，native monitor实际收取443包并关闭，服务到期退出0。人工确认时只剩17.83秒，低于旧35秒门禁，Windows未启动、accepted_write=0，数据测试记未执行。恢复检查确认同boot/release/manifest、三模块/helper、BlueZ owner、音频进程、密钥、adapter属性/UUIDs、充电预算及保护保持；广告0、连接0、worker结束、taint0。内核环形日志前端滚动，使用唯一连续末64行锚定后审计新增17行，无指定故障和日志丢失标志；没有伪称原始全前缀仍保留。

[run-gatt-window.py](run-gatt-window.py)将有界手机服务与Windows中央程序放在同一主机进程联动；默认仅离线preflight，显式run及本次窗口确认才访问设备。固定已审查两端摘要、当前manifest/boot guard、新基线、精确双方地址和新输出目录；就绪后立即启动客户端，要求保守剩余45秒，异常也等待所拥有的手机事务。七项离线调度检查通过，未把模拟回调记为硬件连通。Windows程序只发20B一次、条件允许才47B一次，不配对、不连接未知地址；Dispose仍不是物理断开证据。[中央程序](../bluetooth-windows-central-20261023/README.md)。

[漫步者实测与缓存审计](../bluetooth-speaker-20261023/README.md)：用户已撤回一加15目标，只连接既有paired/trusted的EDIFIER S2000MKⅢ。修复PA17 card/sink共同owner_module的字符串/整数类型兼容后，r3及用户要求重放的r4均完成连接→10%低音量短音→断开→重连→短音，四轮paplay与MediaTransport软件路径通过。r4缓存HCI确认两次认证/加密、连续aptX HD媒体和13/127音量accepted；离线解码为非静音。用户明确“没有听到”，原因仍待定位，不记音响发声通过。r1/r2选择器失败均未开始播放，四次均回收完成。窗口恢复检查新增561行日志、指定故障0，原密钥/模块/预算/保护保持。

该INHIBIT基线不等于健康充电。拟联动的GATT r3在主机preflight即因`mp2650-input` health非Good而停止，没有启动手机服务或Windows客户端；无新的GATT数据失败记录。

## 已固化的软件

- [现有修复包](../package-hardening-20261023/README.md)：k363蓝牙r0、QCA PM r2、TFTP207及平台5-r2已签名，可复现构建与实际载荷校验通过。现场仍使用原r0手工文件，PM r2没有部署；平台包含USB脚本，不能直接覆盖充电会话当前现场。平台副本1被旧收尾脚本误写为JSON，已隔离；交付源为保持原签名摘要的副本2。
- [BNEP/UHID构建](../bluetooth-host-config-20261023/README.md)：复用固定原363源码/配置/符号表，只把两选项n改m，Werror零诊断构建，77+38导入符号全部匹配原363。既有私有O配置和Symvers逐字恢复，共享输入与PM产物保持，未构建Image。
- [新增主机协议包](../bluetooth-host-modules-20261023/README.md)：`samurai-bluetooth-host-k363-0.1.0-r0.apk`，15171B，SHA256 `982e7aff09cb696e921b6058f5f0c6f74b06afe13ed767eda988b5ea469bec9f`。两构逐字一致，签名及三文件（bnep、uhid、标准modules-load配置）真实载荷/模式与隔离APK owner通过。隔离依赖使用明确元数据fixture，未证明依赖服务、depmod trigger或现场功能；未安装/加载。

真实APK3实验已证明hook失败仍可能提交文件/数据库；不能将安装器非零当作未写入。[固定源码依据](apk-hook-semantics.json)、[隔离r0→r2→r0及外部门禁](../package-hardening-20261023/STAGED-ROLLBACK.md)。新增[只读采用预检与事务计划](../bluetooth-host-adoption-20261023/README.md)已用115真实936条installed记录完成实际APK add/del、exit1部分提交后的原生del回退；依赖实体和原系统trigger未执行，live apply仍禁用。现场须先核对canonical路径/owner、安装后modules.order和索引回退边界，再启用安装入口；禁止force/replaces和手写APK数据库。保存候选包不等于已验证现场回退。

[真实trigger输入对齐审查](../bluetooth-host-trigger-20261023/README.md)发现：当前两份只读库存相同，但14个模块索引中的6项、APK DB/world与363/115旧缓存不同。已定位原kmod/busybox trigger及最小ELF依赖；当前索引原字节和模块overlay尚未缓存，因此未运行不等价fixture，现场apply继续禁用。下一窗口按清单仅补取变化原件，不复制完整rootfs或重建Image。

## 底层依据与待验范围

原厂资料、固定仓库及已缓存方案见[OEM研究](../bluetooth-oem-20261023/README.md)、[服务前提](../bluetooth-service-prereqs-20261023/README.md)和[传输候选](../bluetooth-transport-20261023/README.md)。继续沿用本机DMS地址及个体NVM/密钥，不使用他机NV覆盖。

原363 Image/IKCONFIG已与构建摘要核对。最初由CONFIG_BT_LE=n推断普通LE缺失是错误的，已更正：固定ba61a622的Makefile仅用它加入iso.o，SMP/L2CAP/MGMT始终编入；现场MGMT也已证实普通LE。真正缺口为PAN需要的BNEP及HOG需要的UHID，已做独立模块候选。HIDP已在原归档。旧rootfs实际OBEX为obexd-enhanced，与bluez-obexd冲突，不能盲目叠装。

QCA PM r2真实函数33返回值案例和19组生命周期ASan/UBSan通过、k363模块构建通过，尚无现场PM验收。GENI flow/RFR锁契约候选只构建对象，不证明phase5重组根因。Linux HCI SCO路径优先验证，原厂19781 SLIM拓扑仅作必要时的匹配候选，未提前改音频路由。

当前唯一授权音频对端为漫步者S2000MKⅢ，不连接一加15。音响支持本机A2DP Source到远端Sink的验收，不能替代HFP HF、A2DP Source、HID或PAN对端。完整范围及未验项见[feature-status.json](feature-status.json)：GATT数据、新绑定、实际发声、HFP双工/SCO、HID/PAN/OBEX、外部事件唤醒和phase5均未通过。
