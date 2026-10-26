# 现场事务输入的只读字节缓存工具

**仅达到可审查状态，未在手机运行。** `cache-inputs.py` 默认输出离线precheck，不读取设备身份或开始采集。本轮用户暂不进行蓝牙实际测试；本工具未使用SSH、设备调用、安装、trigger、chroot、服务或模块操作，现场apply继续禁用。旧host包、adoption和trigger目录未改。

父线以后取得新的明确窗口才可使用 `--collect-current-window <本次token>`。请求通过 `--request -` 从stdin输入私有JSON，或读取显式私有请求文件；必须同时满足本次token、15分钟内的expiry、原transport身份已确认、精确boot ID、原始guard原字节与当前boot一致、exact363、机型及当前manifest SHA。原guard路径从本次已审host身份交接取得，不新建一个文件绕过。R7/重启前的旧guard或manifest不能视作新窗口许可。

请求模板中的空值不是可运行handoff。`baseline`须放入本次私有 `E:/edk2-samurai-out/bluetooth-host-input-cache-20261023/baseline-363-modules.json` 的对象，固定SHA `b0b115f1061ff10b94e6fcce5f0f657c0ee688f1ebe3b07be89f44bbe0ba6530`。它从已验363完整模块归档生成，含778个相对路径/hash/长度，归档SHA `fca01dab22b0a3917f9ce5600059d00b29aa9685381c2cd2f2e4867b9fb8f73b`。未把完整归档发送到手机。

## 采集范围与一致性

实际DB/world、trigger登记、真实scripts.tar或scripts.tar.gz、全部顶层modules.*原字节、完整`.ko`相对路径/hash/长度清单均采集。原归档相同`.ko`只记清单，新增/变化者才保存overlay原字节；归档中已删除的模块单列。当前commit hooks全部平面原文件、模式和owner入缓存，未知文件类型或子目录拒绝。

ELF部分按父线允许的最小范围收敛：从当前真实DB登记的文件列表选择busybox/sh/kmod/depmod，以及musl/crypto/zstd/lzma/z库族和它们的symlink链。它不制造依赖、不执行ELF；没有宣称完整DT_NEEDED闭包或功能已验证，新依赖库族需后续离线审查。115原件验证选中13个登记路径，规范化为7个原文件、6条链接，共7363328字节。所有ELF相关原字节只会进入私有缓存。

已知usrmerge四条根alias必须精确匹配；其它中间路径拒绝symlink。选中ELF文件的末级symlink只有解析后仍在实际DB登记的相关文件集合才允许，保留原始link spelling；`../bin/kmod`这类原件在guest root内规范化，不可越界。模块树、DB、索引和commit hooks不跟随未知symlink。openat/O_NOFOLLOW读取，拒绝特殊文件和hardlink，读取前后metadata要相同。

前后各完整读取一次目标状态与模块hash，比较DB/world/索引、模块清单和字节hash、相关文件、链接、commit hooks；首尾再次核对身份和manifest。仅一致后才在内存生成tar.gz并写stdout；此前没有有效包输出。预算为90秒默认/最多120秒、单文件16MiB、全KO128MiB、私有payload64MiB、压缩包72MiB，另有目录/文件数和深度上限。压缩模块未支持，会明确拒绝，不静默漏项。

tar只有普通文件，原symlink和模式/owner以私有manifest记录，不在归档内放可逃逸link。所有实际原件经stdout送到**外部新的私有临时文件**，不写手机。父线使用已有审定host/guard传输，stderr也只入私有证据。工具不内置SSH入口，本轮不会运行现场路径。

`--verify-cache <私有临时.tar.gz>`离线核对完整gzip、路径、成员、字节hash、总量和双快照摘要；通过后才能由父线认定该缓存完整。保留失败或截断证据，不能把部分传输标成有效。该校验仅证明结构和字节完整性，不能替代受信host来源或窗口许可。两次一致观察不是APK排他锁，也不承诺采集结束后的事务状态，现场updater未在此实现。

## 本轮离线验证与边界

[offline-validation.json](offline-validation.json)覆盖已存363 baseline map、真实115登记文件/链接读取、临时文件的登记链接解析、未知链接/路径穿越拒绝和实际字节/metadata变化检测。没有运行native collect/identity，没有生成模拟设备缓存，没有验证完整采集/传输/gzip包的端到端路径；使用前仍需父线审查并在未来明确授权窗口验证。没有新测试矩阵，也没有模拟安装事务。

工具只缓存真实字节，不能补齐当前设备已失去窗口的状态。R7后当前guard/manifest、模块overlay及新增脚本变化都必须在新窗口重新读，不能用旧115或363归档假造当前DB/索引。不会安装、调用depmod或触发原脚本，也不改变服务、加载模块或修复文件。
