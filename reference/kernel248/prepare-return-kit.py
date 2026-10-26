"""Build a private index from already verified backup receipts; no phone writes."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel248')
validated=json.loads((R/'userdata-backup-validation.json').read_text());assert validated['phase']=='complete' and validated['restored_fsck_exit_code']==0
copy=json.loads((P/'userdata-clean-pc-copy-validation-private.json').read_text());assert copy['sha256']==validated['clean_compressed_sha256']
parts=json.loads((P/'poll-backup-server-private.json').read_text())['private']['manifest']
files={str(Path('linux-return-partitions')/name):record for name,record in parts.items()}
files['linux-return-partitions/logdump.img']=dict(bytes=67108864,sha256='e73754c7d327925acf031aed54e0e6d02069b7a112c32b187ac9bfb468da1358')
files['linux-userdata-clean-r6-private.pcl.zst']=dict(bytes=copy['bytes'],sha256=copy['sha256'])
for name in ['linux-return-gpt-private.tar.gz','rescue-tools-private.tar.gz']:
 p=P/name;files[name]=dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
for name,record in files.items():assert (P/name).is_file() and (P/name).stat().st_size==record['bytes']
index=dict(stage=248,private_do_not_publish=True,backup_and_pc_restore_checks_complete=True,actual_android_to_linux_handset_roundtrip_not_performed=True,userdata_logical_bytes=119033245696,rootfs_backup_format='zstd compressed standard partclone image, not an Android sparse image',files=files)
(P/'LINUX-RETURN-MANIFEST-248-private.json').write_text(json.dumps(index,indent=2)+'\n')
(P/'SHA256SUMS-LINUX-RETURN-248-private.txt').write_text(''.join(record['sha256']+'  '+name+'\n' for name,record in files.items()))
text='''# 当前 Linux 返回文件（248，私人保存）

boot/logdump原样备份和完整rootfs已经保存；rootfs通过源长度/SHA、zstd校验、partclone数据CRC、PC实际恢复与恢复后的F2FS dry-run检查。尚未执行实机Android→Linux往返，手机仍在RAM恢复环境，Android由用户手动刷入。

## 需要保留的文件

- linux-return-partitions/boot.img：当前boot235，包含UEFI与板级DTB。
- linux-return-partitions/logdump.img：当前Image183及内置USB/SSH RAM恢复环境。
- linux-userdata-clean-r6-private.pcl.zst：当前完整rootfs的标准partclone压缩镜像，4589045416字节；恢复目标原userdata大小119033245696字节。
- linux-return-partitions/内其余19个分区快照，以及GPT头尾归档：用于比对及按实际差异回退，不是要求全部回刷。
- rescue-tools-private.tar.gz：已实机运行的aarch64离线恢复工具；原始密钥与身份文件仅私人保留。
- LINUX-RETURN-MANIFEST-248-private.json与SHA256SUMS-LINUX-RETURN-248-private.txt：最终推荐文件清单与校验值。

rootfs SHA256：01fe9f0ba9bfb13ae14ed2e704152c7b3061be5193e70c3930d68be83668671e。
失败尝试及带库诊断前缀的原始流另行保留，返回时使用上面明确指定的clean标准镜像。

## 返回Linux的方法

1. Android测试后，重新确认实际手机、bootloader解锁状态和分区几何；与本次备份比对。保留Android之后的必要配置证据。
2. 根据当轮状态恢复匹配的boot235和logdump183。Android userdata没有Linux根标记时，Image183可进入已实测的RAM恢复环境，经严格原密钥USB/SSH连接；本机不支持fastboot boot，不能以临时启动作为唯一路线。
3. 从电脑加载rescue-tools至RAM，确认userdata完全卸载、目标尺寸匹配，再用partclone.restore接收解压后的标准镜像，恢复到确认无误的userdata。完成后检查F2FS、根标记与UUID，再受控重启进入Linux。
4. 核对boot/logdump、789项模块清单、958个包以及Mesa/libcamera/启动配置，再做硬件回归。Android前后modem配置可能变化，按差异处理。

这个.pcl.zst文件不能直接传给fastboot flash userdata。PC实际恢复得到的119GB逻辑稀疏raw文件另存于WSL的/home/cy122/x2pro-linux/gnss248-return-validation，可作额外恢复依据；如选择fastboot刷userdata，需要另行准备并验证合适的Android sparse文件。

不要批量恢复GPT、NV、persist和校准，也不要用旧rootfs132替换当前快照。返回命令需依据Android之后的新设备身份生成；不要重放本轮已执行的重启脚本。

这些文件包含系统身份、密钥或校准，不能上传GitHub。GitHub保存的是可公开的源码、补丁、配置模板和脱敏实测记录。
'''
(P/'LINUX-RETURN-248-private.md').write_text(text)
print(json.dumps(dict(private_return_kit_index_created=True,verified_partition_images=21,standard_rootfs_image_bytes=copy['bytes'],pc_restore_fsck_passed=True,no_phone_flash=True)))
