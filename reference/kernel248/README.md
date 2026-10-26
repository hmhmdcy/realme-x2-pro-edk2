# 248：保存当前Linux并验证PC恢复

用户改为自行手动刷Android，要求保留返回当前Linux的能力；随后明确要求把全部后续硬件适配源码推送GitHub。本轮未刷Android，未格式化userdata，GNSS零CNR仍未修复。

当前rootfs标准partclone压缩镜像已完整保存：4589045416字节，SHA256 `01fe9f0ba9bfb13ae14ed2e704152c7b3061be5193e70c3930d68be83668671e`。两次只读采集一致，源长度/SHA、逐段SHA、zstd帧和partclone数据校验通过。主机实际恢复为119033245696字节逻辑稀疏普通文件，恢复后的F2FS全量dry-run检查通过。[userdata验收](userdata-backup-validation.json)

另有[20分区快照](partition-backup-validation.json)加[logdump](logdump-backup-validation.json)，共21项，以及[六个UFS LUN的GPT头尾](gpt-backup-validation.json)。boot235、logdump/Image183均为现机原样备份，旧工厂备份未覆盖。rootfs保留当前包、模块、固件和配置，不以旧rootfs132代替，也不承诺仅编译源码就能还原全部现机状态。

已实际进入Image183内置RAM恢复环境并通过严格原密钥USB/SSH访问。源userdata卸载且块设备RO，临时改名的Linux根标记在备份前已恢复。最终worker退出、RAM临时镜像释放，手机仍在RAM且Android未刷。[最终现场](final-ram-state-validation.json)

备份期间的旧工具兼容性、客户端提前退出、分段续传和57字节库诊断前缀处理，均在[详细状态](STATUS.md)保留，没有把失败文件标为成功。官方partclone源码只读补丁通过4096/512扇区差异模拟、源SHA不变、备份/恢复/检查；标准镜像经过独立实际恢复验收。

私人文件在`E:/edk2-samurai-out/kernel248`，推荐入口`LINUX-RETURN-248-private.md`及清单。完整系统镜像、NV/校准和密钥不上传GitHub。[修复分布与返回路线](RESTORE-NOTES.md)说明boot/logdump/rootfs必须配套；本轮证明PC镜像可恢复，尚未执行实机Android→Linux往返。

源码发布见[10月17日发布记录](../publication-2026-10-17/README.md)。内核31文件/四组提交与canonical逐项一致，配套源码和实测记录另存EDK2仓库；原开发树和未核生成DTB未被重置。
