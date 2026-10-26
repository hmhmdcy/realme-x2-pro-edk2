# BNEP/UHID adoption 与回退审查

本目录交付默认只读的 `preflight.py` 和可审查事务计划。**live apply 禁用**：`--apply` 总是先拒绝，不执行 APK 变更。手机、原rootfs、SDK和冻结APK均未写入；没有SSH、加载模块、服务操作或重启。当前充电会话继续持有设备，某次manifest摘要不是交还窗口的许可。

范围仅为已冻结的 [三文件 host APK](../bluetooth-host-modules-20261023/artifact-manifest.json)：BNEP、UHID和标准 `/usr/lib/modules-load.d/60-samurai-bluetooth-host.conf`。其SHA256固定为 `982e7aff09cb696e921b6058f5f0c6f74b06afe13ed767eda988b5ea469bec9f`。不改平台包、蓝牙helper、USB、充电或相机，不使用 `force`、`replaces`、手改数据库或伪造依赖。

## 只读入口

调用方须先从私有 `kernel449/boot-adoption-private.json` 取得原始guard路径，并核对其中原SSH密钥和440 baseline验证事实。ID和密钥不进入公开文件。将当前明确交接的guard路径、充电manifest SHA、三个依赖的实际已安装版本、实际 `modules.order` owner填入私有handoff；[模板](baseline-lock.template.json) 中的空值不是已验证状态。guard和manifest均通过参数与handoff传入，工具不硬编码某次r5/r6摘要，也不把身份一致当成当前健康或窗口许可。

参数为 `--root`（现场只读为 `/`）、`--action adopt|rollback`、`--baseline-lock`、`--guard-file`、`--charging-manifest-sha256`、`--candidate`、`--artifact-manifest`、`--apk` 和 `--verification-keys`。输出仅为stdout JSON；调用方应另存到全新的私有证据文件，失败输出也须保留。`--fixture`只用于明确的非live测试root，公开结果会标注身份和进程状态来自fixture。

检查包括当前boot与原guard一致、设备compatible、exact363、当前充电manifest、bluetoothd已静止、BNEP/UHID未加载、canonical路径和APK owner、精确字节前态、依赖版本及错误标志、现存 `modules.order`、签名和冻结hash，以及APK实际三个数据块/模式/依赖且无脚本、trigger或replaces。读取完成后再次核对身份、manifest、数据库、modules.order和目标状态。正常 `f:S` 允许；小写f/s/x是失败标志，不能伪装成成功。

当前入口仅接受明确的 `lib -> usr/lib` 布局；其余祖先/文件symlink、hardlink和未知owner/字节均拒绝，不自动修正路径。adopt仅接受包记录不存在、三个目标均absent且unowned。rollback审查要求该包只拥有这三个文件，版本恰为0.1.0-r0，存在的载荷均为冻结字节/0644/root；允许真实APK部分提交后的已知 `fS` 与缺失载荷，仍拒绝未知脚本/xattr失败和外来路径漂移。

`modules.order`固定核对363模块归档中的**安装后版本**，32289字节、SHA `81507a3119cebd985936e87d10b1ccbc28677d0fca370a979521449e1dc8e81f`。原构建报告的26065字节、`7e7098…`是构建目录`.o`路径版本，不能混用。现场文件缺失或不同即停止调查，入口不会把归档文件复制到手机。现有kmod trigger若缺此文件可能清索引，不能省略此门禁。

## 可审查事务与未闭环部分

只读输出的argv带明确root和arch，仅供审查，不执行。拟采用原生 `apk --no-network add <frozen.apk>`，拟回退原生 `apk --no-network del samurai-bluetooth-host-k363`；依赖必须已真实安装，无新增依赖事务。只有初始三个文件absent/unowned的本次前态才适用此删除回退，不能泛化为任意软件包恢复器。

未来启用现场变更前，主线还须在真实窗口核对原系统kmod trigger通过 `/lib/modules` 实际作用到该 `/usr/lib/modules` 树、索引文件的owner/变化及索引恢复方案，并固定world和反向依赖前态，保证回退不会牵连其它包。应立即重跑本次身份/状态检查，保留APK锁与退出码；无论退出码是否为零，均读回三个文件、包版本/owner/f/s/x、原包集合、world、modules.order与索引，再决定完成或回退。当前入口没有实现这些索引写入/回退与事务锁衔接，因此不提供可执行live apply，也不声称hook能阻止APK提交。

未知祖先漂移、未知字节或新owner先停下并保留证据；入口不会删除外来文件。原生APK失败仍可能已经提交部分载荷/数据库。不能仅凭exit1认定未修改，也不能跳过后验而重复安装。实际PAN、HOG/HID消费者、模块加载/释放和硬件回退仍待现场，普通GATT验收不能由这两个模块代替。

## 本次真实隔离验证

[规范结果](offline-validation.json) 使用只读复制的115原始installed数据库（1503359字节、936原记录）和world，没有制造依赖记录或依赖APK。只复制这1.5MB元数据、固定363的modules.order及明确模拟的身份/进程状态；依赖实体未复制，不算依赖服务功能验证。所有实际APK安装仅在全新私有root，禁网络、scripts和commit hooks，原系统kmod trigger/索引没有执行。

1. 只读adopt检查不改数据库/目标；`--apply`和缺失modules.order均拒绝且零APK变更。
2. 真实冻结APK `add` 成功，rollback检查核实三文件精确字节、owner和版本，原生 `del` 返回0；原936包的名称/版本/失败标志、world条目、modules.order和三文件absent前态恢复。
3. 在成功preflight之后，由测试注入者将自己的临时祖先变成普通文件。原签名APK `add` 真实exit1，却已提交两模块和 `f:fS`。原日志完整保留。这说明外部preflight本身也不是跨未来事务的原子保证。
4. rollback先拒绝该未知祖先。测试注入者只撤销自己创建的阻断文件后，入口识别已知部分提交，实际原生APK `del` 返回0并恢复相同前态。没有修改DB来抹除f标志。

验证代码 `validate-offline.py` 可用相同真实输入在新的私有Linux目录复跑，不重用或覆盖旧root。规范报告引用最终源码hash；此前准备阶段报告仅留私有scratch。原始完整证据保留在 `/home/cy122/x2pro-linux/bluetooth-host-adoption20261023-fixture3`，便携日志副本见新私有输出 `E:/edk2-samurai-out/bluetooth-host-adoption-20261023`。旧host包的历史隔离验证使用三条人工metadata-only依赖fixture；包内依赖声明并未改变，旧结果没有被本轮冒认为真实依赖或现场能力。
