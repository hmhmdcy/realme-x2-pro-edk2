# Phosh 原版回退与部署前事实

已取回手机实际安装的 `phosh`、`libphosh`、`phosh-schemas`、`phosh-portalsconf` 四个0.57.0-r3原包。真实apk-tools按既有Alpine公钥验证签名，并计算索引；P/V/A/C/c、依赖和provides与Image501 postboot04保留的实际APK数据库一致。原件仅在私有输出目录，无手机安装。

主包、lib和portalsconf来自官方edge/aarch64；schema该URL为404，随后从官方edge/x86_64取得同一noarch载荷，以实际 `apk index --rewrite-arch aarch64` 确认其C也与原aarch64索引完全相同。没有采用不同控制摘要的替代包。摘要见[verified-result.json](verified-result.json)。

部署前只读检查确认：同一已adopt的Image501、greetd/phoc/Phosh运行，四包72个普通文件的SHA256和mode均与原包完全一致；UPower中两项实际LINE_POWER均Online=yes，Display此时为fully-charged。没有修改包、服务、USB或充电策略，也没有采集拔插边沿。[检查结果](live-preflight-result.json)不代表新标记已部署。

用户已明确取消新增桌面提示路线；相关编译已正常停止，未产包或部署。以上原包与只读核对仅作为历史留存，不再据此准备桌面更新。后续只做USB、charger和gauge底层优化。

初次主机执行的root-only apk权限拒绝、schema404及元数据检查器误用缺省provides字段均留存；只修正执行身份和检查输入后核对原载荷。首个只读脚本因错误解析`/proc/version`在任何文件/服务读取前退出；改用实际`uname.version`后新的只读02检查通过，原01未覆写。没有因这些主机/只读错误重装或重启手机。
