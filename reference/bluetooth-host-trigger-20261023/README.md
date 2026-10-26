# 原kmod trigger隔离验证的输入对齐审查

本轮只完成 [alignment audit](input-alignment-audit.json)，没有创建或执行APK trigger fixture，现场apply继续禁用。两份新实机只读快照的模块安装库存和APK事务上下文完全一致；但它们与原363模块归档、115旧rootfs并非同一完整前态，按主线要求在具体缺项处收束。没有SSH、手机访问、服务/模块操作、安装、构建、重启或共享SDK写入；此前冻结包和adoption目录保持不变。

## 已核对事实

`lib -> usr/lib`，两条modules路径均规范化到 `/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+`。实际 `modules.order` 存在且无APK owner，32289字节、SHA `81507a3119cebd985936e87d10b1ccbc28677d0fca370a979521449e1dc8e81f`，与363归档安装后版本相同。14个索引/元数据中8项逐字相同；六项不同：`modules.alias`、`modules.alias.bin`、`modules.dep`、`modules.dep.bin`、`modules.symbols`、`modules.symbols.bin`。它们在两份现场快照中均无APK owner，完整差异摘要见JSON。

现场installed数据库1527254字节、SHA `24c97224f2a1aa0832fd546c36c1449965679b6be4d3973187efba0c32f5cdc5`；115原件1503359字节、SHA `7a608476af9f8bae0c8dabd8a68155eeb406c845dfbf9369d9fdf0a4f65cd87e`。现场world1215字节，115原件621字节，摘要也不同。现场快照的commit_hooks为空；lock路径存在不等于已持有APK排他锁。当前输入只有这些原件的摘要，无法从摘要重建当前事务数据库或索引。

115原始脚本实际存于 `lib/apk/db/scripts.tar.gz`。原kmod34.2-r1 trigger为494字节、SHA `ffa9c255f44ed83911be3b76e2dc0c2e11b9f044ed31b715bf53c2b6c8d15d3b`；原busybox1.38.0-r7 trigger为576字节、SHA `c7840b111dd82669de2074ea3c7e345c063928db2bbff650a81289777b3ff98f`。触发器登记与真实installed记录关联，两者均监视 `/lib/modules/*` 和 `/usr/lib/modules/*`。kmod在modules.order存在时调用depmod，缺失时可能删除索引；busybox有kmod时不重复depmod。

可定位的最小AArch64 ELF闭包是原busybox、kmod、musl及zstd/lzma/z/crypto相关实际文件；逐文件hash和DT_NEEDED见审查结果。主机已有static PIE qemu-aarch64与POF binfmt登记。这些证明所需文件和登记可取得，**尚未实跑chroot或完整执行链**。实际手机的trigger登记、脚本和ELF字节尚未与115副本逐项比较。

六项索引差异的来源仍未知，不能据此判定现场索引损坏，也不能把旧归档覆盖过去。只在旧归档上跑真实trigger可形成archive-only功能证据，不能证明当前现场索引的功能或回退；本轮没有运行这种不等价fixture。

## 下一次授权窗口的最小只读缓存

由持有设备窗口的主线采集，保存在私有目录，本代理不会主动访问手机：

- 当前 `/lib/apk/db/installed`、`/etc/apk/world` 原字节及hash。保留真实记录，不改DB、不制造依赖。
- 当前六项不同索引的原字节，并保留其余八项及modules.order的hash/owner核对，以建立可恢复前态。
- 当前完整`.ko`路径、长度和hash清单；与已存363归档比对后，只补缓存新增/改变的模块overlay原件与来源。现有相同原件直接复用，不复制整个rootfs。
- 当前APK trigger登记及真实脚本存储原字节，确认kmod/busybox的对应脚本、checksum和版本。缓存实际commit hook库存，若不再为空则保留相关脚本内容、模式、owner和hash。
- 相关最小执行链的实际路径/链接、owner和hash：busybox、sh、kmod、depmod、musl和DT_NEEDED库。若与115原件相同即复用，不重复复制。
- 当次真实boot guard、manifest和明确交还窗口由主线管理，ID/地址/keys不公开。R7或正常重启后的状态不能沿用这两份旧快照作为当前授权。

输入对齐后再在新的独占隔离root执行原签名host APK、真实原trigger和depmod，观察APK原生锁/commit hooks、索引功能、删除回退与前态恢复。外部入口继续不含force/replaces/DB编辑；APK非零退出后仍须读回可能已提交的状态。当前只读 [adoption计划](../bluetooth-host-adoption-20261023/README.md) 的apply禁用不变，PAN/HOG硬件后验仍待现场。

`audit-inputs.py`只导出选定模块库存、APK上下文、来源hash及依赖闭包，不导出boot ID、蓝牙地址或密钥。规范报告绑定其源码hash；file-stability自排除。没有执行旧安装/回滚测试或重建签名包。
