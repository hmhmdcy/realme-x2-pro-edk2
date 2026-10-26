# RAM地址缓存错误传播候选

仅保存修复后 `usr_sbin_samurai-radio-address` 和相对旧helper的 `radio-address-error-propagation.patch`。旧 `linux-port/packages/samurai-platform`、旧source锁和签名包均未修改；没有构建/签名新包或访问手机。候选SHA256：`33749acb96586d77046f0a47bf1bbf0920e3c6f6fc27f3f627386f60beffd0a7`；旧helper：`3421ee681da7714678f4c64e62d060997e585e93857ae02d8fd5d050e417ef0d`。

旧 `load()` 中的 `refresh || return` 会使refresh内部不能依赖errexit。隔离运行旧完整helper已复现query mktemp失败后仍写chroot根路径、调用DMS、发布坏指针并打印 `RADIO_ADDRESS_QUERY_VERIFIED`。

候选显式处理query mktemp与空/异常返回值、boot-id写入和私有mode检查、MPSS读取与DMS状态、pointer mktemp/私有mode/写入/读回/mv错误；任何失败立即向load和调用入口返回，不执行后续地址应用。发布前拒绝目录目的地，发布后以原cache检查重新核对pointer、当前boot、私有mode和6字节数据，再发成功回执。cache中的boot文件读取也单独判错，防止两个读取都失败而空字符串相等。原只读DMS流程、同启动比较、0700/0600校验及两radio独立锁保留。

[验证报告](radio-validation.json)使用真实完整旧/新脚本文本，路径未替换。最小私有chroot提供命令故障stub和明确模拟的proc/sys/DMS字节；通过在OR-list中source完整脚本使errexit不可依赖。

- 8类失败：query mktemp失败/成功但空返回、boot-id重定向失败、DMS非零/非私有mode、pointer创建/printf写/mv发布失败。全部非零、无后续BT地址调用、无根路径哨兵变化、无current指针发布或成功回执；保留另一radio锁，释放本次锁。
- 成功及同boot cache命中通过；命中不重跑DMS。缓存boot读取错误不会被当作命中。WLAN独立refresh/指针和另一radio锁也通过。
- 失败query和未发布临时pointer保留在私有fixture中，便于诊断，不进行自动删改或失败后假成功。

原始执行日志与patch应用核对只保存在 `/home/cy122/x2pro-linux/radio-static-fixes20261023-fixture1` 及新私有输出。原生BusyBox shell、硬件DMS、真实地址应用、并发崩溃/断电尚未验证；这轮没有SSH、WinRT、设备、服务、模块或新rootfs构建。WLAN地址应用的其它逻辑保持原样，本轮只修缓存错误向调用入口传播。

待主线整合到下一平台修订，更新相应recipe checksum、pkgrel及新的来源锁；旧5-r2交付继续作为历史原件保留。当前是离线候选，不是已部署结果。
