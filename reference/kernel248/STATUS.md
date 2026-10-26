# 248：当前Linux完整返回文件（备份与PC恢复验收完成）

用户改为自行手动刷Android；本轮只准备和验证Linux返回文件，不自动刷Android。完整userdata与21分区/GPT已保存，PC实际恢复和F2FS检查通过；未做实机Android→Linux往返。[修复分布、GitHub情况和返回路线](RESTORE-NOTES.md)。

当前已验证Image183内置RAM恢复环境，仍boot235/Image183，Android未刷、userdata未格式化。guard为`/run/k248-rescue-boot-id-private.txt`，247及更早失效。使用[rescue-host.py](rescue-host.py)严格固定从真实Image183提取的内置密钥。原Linux根标记已恢复；userdata卸载、块设备RO，工具完全位于RAM。已通过源F2FS全量dry-run检查，没有修复写入。

21个启动/相关分区原样镜像已核长度/SHA（[20项](partition-backup-validation.json)及[logdump](logdump-backup-validation.json)），六个UFS LUN的GPT头尾也[核验通过](gpt-backup-validation.json)。私人目录`E:/edk2-samurai-out/kernel248`，旧工厂备份未覆盖。当前boot和logdump可直接按原样恢复，不必先重新编译。

**完整userdata已分段收齐，标准镜像及PC实际恢复检查通过。** 分区119033245696字节，使用约17.5GB；按已用块采集并zstd压缩。两个源进程均退出0，两次独立采集均4589104762字节/SHA b0880cbc…；r6在独立5GiB上限tmpfs保留完整压缩镜像，16MiB范围请求及逐段SHA续传成功，PC完整长度/SHA匹配。PC全量恢复改用WSL ext4稀疏普通文件；NTFS兼容性另有128MiB实际恢复检查。[主机验证脚本](validate-userdata-host.py)仅允许新建本轮拥有的普通文件，不能用于写手机。

原Alpine partclone0.3.40在超级块扇区512→4096的更新路径撞到设备RO保护。独立工具将`c.dry_run=1`、`c.no_kernel_check=1`设在`c.ro=1`后，保留源设备RO。官方tag0.3.40已原生aarch64构建成功，未修改生产内核。[模拟同类差异](partclone-ro-fixture-validation.json)：RO循环设备备份、源SHA不变、chkimg、恢复、恢复后fsck全部通过；另在PC NTFS稀疏文件实际恢复128MiB逻辑/约16MiB分配并fsck通过。[手机RAM工具核验](partclone-ro-deployment-validation.json)。

失败尝试如实保留私人记录：r1误用不支持的fsck `-n`；r2源检查通过但旧partclone写入被RO阻止，56字节流无效；r3元数据扫描超过下载器20秒低速时限，客户端提前退出，已按当前boot/进程启动身份终止其专有进程组；首次收尾脚本解析含空格的proc stat失败，未发送kill，已改为验证独立进程组；r4因r3仍占端口而bind失败，未生成流。r5虽然源成功退出，但curl0只收到4316528640字节，少272576122字节，超过4MiB尾缓存，不能采用。r6完整RAM镜像与r5原始完整SHA一致，先核对PC已有前缀SHA再复制前缀，补齐17段并核对完整SHA。不能使用失败文件，也不能重放历史重启请求。

[初次GitHub核对](github-publication-validation.json)时两个远端停在10月14日。用户随后明确要求推送全部后续修复；内核四组31文件已推送并读回04d4d4f9，配套源码/记录发布见[发布记录](../publication-2026-10-17/README.md)。源码/补丁与当前完整系统快照分别保存，不能只靠旧GitHub远端或rootfs132认定最新修复可原样还原。

partclone镜像格式检查发现F2FS库将57字节`update_superblock`诊断输出到stdout，位于标准partclone头之前；这是只读dry-run的诊断文字，不代表源写入。原始压缩文件不改；主机只移除精确匹配的57字节前缀，保留所有partclone字节，边重压缩边chkimg验证，再以标准镜像做实际恢复。最终标准镜像4589045416字节/SHA `01fe9f0ba9bfb13ae14ed2e704152c7b3061be5193e70c3930d68be83668671e`，zstd/chkimg/restore均0；恢复119033245696字节逻辑F2FS，dry-run全检查0。

最终[userdata验收](userdata-backup-validation.json)、[RAM现场](final-ram-state-validation.json)已保存；两个备份worker干净退出，完整RAM临时镜像在PC双份校验/恢复通过后释放。手机仍在RAM、userdata卸载且RO，原Linux根标记已恢复，未刷Android。推荐返回文件及校验清单在私人目录`LINUX-RETURN-248-private.md`/`LINUX-RETURN-MANIFEST-248-private.json`；恢复使用`linux-userdata-clean-r6-private.pcl.zst`，不是失败尝试或含诊断前缀的原始流。
