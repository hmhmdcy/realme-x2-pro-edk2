# TFTP207 单程序固化

第二轮已确认APK3的pre-install/pre-upgrade失败不阻止载荷/数据库提交。此包的检测脚本也仅为advisory，必须在执行APK前外部核对实际文件owner、机型、同字节及现场状态；不能直接依赖hook阻断安装。已签名包及其中历史文档不修改。

本包只采用当前已验证的 `/usr/sbin/samurai-tqftpserv`，SHA-256 `b3bb82b9d090a5d06e9ba2ca24e3373ab1c1e7cc2a5c6b603e2acb02715487a1`，922592字节，静态AArch64 ELF。包内其它文件仅为来源、补丁和许可证。安装/升级前只核对机型和现有文件同字节，不重启服务或modem，不写NV，不修改启动脚本/USB/充电/相机。

独立签名构建入口是仓库 `reference/package-hardening-20261023/build-tftp-apk.py`，不是203的旧GNSS包构建器。源码构建继续用 `linux-port/radio/build-tftp.py` 和 `source-lock.json` 的十份固定提交公共源；可用 `--source-cache` 复用已验证的原始下载缓存。缓存中的 `tqftpserv.c` 必须为补丁前原文件；已经打过补丁的构建目录不能冒充原始缓存。

示例源码重建：`python3 linux-port/radio/build-tftp.py --work-dir /new/private/build --source-cache /verified/source/cache`。需Python3、patch、AArch64 GNU编译器及静态目标库；该入口校验源文件、无fuzz应用完整补丁并以Werror编译。该目录还核对samurai-wifi和MCFG助手的完整锁；从仓库运行即可，随包的源码摘录不是整个工程替代品。

207已验证真实QRTR文件读写、范围、窗口/重复包和16位块号回绕，生产服务证据为 `reference/kernel207/tftp-deployment-validation.json`。同机173份原厂MCFG从只读分区复制到RAM属于已存在的启动助手，不随本包复制原厂数据。当前platform配方中的samurai-wifi和MCFG助手已经分别是854c9a8c…和d4c62be6…，没有遗漏这两项；此包补的是TFTP服务程序的包管理缺口。

尚未在当前设备查询文件所有者或安装。若该文件属于现有samurai-radio-tools，应确定精确替代关系或重包原所有者后模拟事务。本包未宣称新增GNSS定位、蜂窝业务、PM或长期TFTP可靠性验收。
