# 453：优先从本机保留vendor补取匹配AF配置库

**后续已执行：**当前HAL完整匹配，但配置库实际在ODM；库与它引用的唯一配置均已只读补取，见[实际结果](AF-CONFIG-ACQUIRED.md)。以下保留执行前步骤与当时未知项，不应再把vendor相对路径当作已证来源。

2026-10-23。**281的HAL确实直接读自当时手机vendor分区，不是从下载ROM提取。**下一串行窗口应先查询本机保留分区／挂载，再核当前HAL的完整SHA，仅在匹配后补取一个配置库。无需先下载整ROM、重建vendor镜像或重采EEPROM。

本轮仅审现存采集脚本和元数据，没有SSH、手机挂载／操作、WSL源码／build访问或SDK占用。当前手机由其它会话持有；本页不是现场连接、分区存在或格式验收。先前AF六文件、个体候选及正式配置保持原SHA。

## 已证入口与时序

| 来源 | 实际做过什么 | 不能由此推定什么 |
| --- | --- | --- |
| [115 sensor SO提取](../kernel115/extract-camera-sources.sh) | 核PARTNAME／容量后，`/dev/sda9`以ext4 `ro,noload,nosuid,nodev,noexec`挂载至 `/run/k115-camera-vendor-readonly`，只复制sensor SO；前后整分区SHA相同，随后卸载 | 115原vendor与后来的F.16相同；该目录当前仍挂载；115已保存配置库 |
| [115相机清单](../kernel115/list-camera-configs.sh) | 同设备临时挂载 `/run/k115-camera-config-list-readonly`，列 `etc/camera`及BIN文件，随后卸载 | 清单包含库原件，或能证明未知配置XML位置 |
| [251原厂身份](../kernel251/stock-validation.json)及实际私有capture脚本 | Android11／`RMX1931_11_F.16`；采集对象是GNSS，库锁为六份 `/vendor/lib64/libgnss／libloc／libqmi…`及GPS配置 | 251采过camera HAL或 `libhwconfigurationutil.so`；这些GNSS脚本可用于当前Linux只读提取 |
| [257返回Linux](../kernel257/README.md) | 恢复boot／logdump／vbmeta／DTBO及Linux userdata；记录未恢复整个固件集 | 当前vendor必然未变、必然已挂载或格式可直接沿用 |
| [281实际采集入口](../kernel281/collect-oem-isp.py) | 解析 `/dev/disk/by-partlabel/vendor`为 `sda9`，核 `PARTNAME=vendor`、容量3342336个512字节sector及未挂载；临时ext4只读、禁止journal replay挂载后读HAL | 当前仍叫sda9、仍为ext4、仍未挂载或完整HAL仍匹配 |

281临时挂载点为 `/run/k281-vendor-isp-static-ro`，读取的分区内相对路径是 **`lib64/hw/camera.qcom.so`**。旧脚本在读取后明确卸载并删除挂载点，[收据](../kernel281/oem-hal-source-validation.json)和[卸载确认](../kernel281/vendor-unmount-validation.json)均成立。它的手机端私有中间目录 `/var/lib/samurai/k281-oem-isp-static/`只存旧HAL压缩副本／采集收据，不是vendor挂载，也不包含本轮所缺配置库。

匹配权威为6087920字节的HAL，SHA256：

```text
e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde
```

281实际ELF导入 `libhwconfigurationutil.so`及相关配置查询函数，已知表名 `OemCamActuatorSettingMap`；**分区内 `lib64/libhwconfigurationutil.so`是下一待查询目标，其当前存在、是否链接、大小和真实来源尚未实读证明。**若该路径缺失，不能据此认定表为空，亦不能先指定XML文件名。

## 下一窗口第一步：只查元数据

仅由主线取得明确的新owner交回、原SSH key身份、完整boot／既有guard与充电基线后执行；USB恢复或旧交接不代替授权。不可变boot、现有guard和充电状态优先，不创建guard、不切换服务／模块／USB。

先读以下限定目标，不扫描全盘或全vendor：

1. 当次 `/proc/sys/kernel/random/boot_id`与交接指定的既有guard，实读逐字节相等；当前最后已证guard为 `/var/lib/samurai/k449-adopted/boot-id-private.txt`，不能据旧记录自行采用新boot。
2. `/dev/disk/by-partlabel/vendor`的实际链接、解析后节点的块设备类型与major:minor；对应 `/sys/dev/block/<major>:<minor>/uevent`、`size`、`ro`。旧sda9／3342336 sector仅为对照，不作为缺失时的盲目fallback。
3. `/proc/self/mountinfo`中该major:minor的全部记录：文件系统、挂载root、挂载点、VFS及superblock选项。不能因为 `/vendor`或旧 `/run/k281-…`目录存在就当成正确原分区。
4. 仅对已核实的该块设备做已安装工具的只读格式probe，例如 `blkid -p -o export <已核块节点>`。先确认真实格式；没有格式证据不能直接 `mount -t ext4`或交给debugfs。不运行无目标blkid／fsck／修复／格式化。

这一步只形成PC私有元数据收据。节点不存在、标签／major:minor矛盾、格式未知或发现rw挂载时，先报告实际状态；不改挂载选项、不卸载他会话挂载、不用旧sda9假定填空。

## 第二步：仅核HAL指纹，再取单库

按第一步现场结果选择一个路径，不在脚本中预先固化当前挂载状态：

- **已有安全只读挂载：**确认来源major:minor相同、挂载root能正确映射分区根、文件系统实际只读且未启用journal replay。使用这个实际挂载点的 `lib64/hw/camera.qcom.so`；拒绝未核的bind子目录、符号链接跨来源或rw superblock上的表面ro路径。不remount、不动他owner挂载。
- **已证ext4且未挂载：**若手机已有debugfs，优先用默认只读debugfs的 `stat`／`cat`针对两个准确路径读取；禁止 `-w`及任何修改命令。可先对 `cat /lib64/hw/camera.qcom.so`的完整字节计算SHA，只回传指纹，无需再缓存或传回整份HAL。debugfs报错、输出不完整或SHA不匹配均拒绝接受。
- **无可用只读文件读取器：**只有在主线下一窗口已核节点、格式、未挂载和明确采用该步骤后，才考虑沿用281的临时挂载方式 `ro,noload,nosuid,nodev,noexec`，事后仅卸载自己创建的挂载并清除自有空挂载点。此分支属于显式有状态步骤，本页未执行；不使用单独 `ro`去允许ext4 journal replay。

先核当前HAL完整SHA与上述281权威**精确相等**。不等则停止接受该版本的库／配置；不能因F.16标签、文件名或相近字节数套用。记录版本不匹配即可，不再扩展提取。

匹配后，只读取同一已证来源的 `lib64/libhwconfigurationutil.so`：核普通文件／解析来源、ELF64／AArch64身份、实际长度和完整SHA，原始字节直接经严格SSH流传回PC私有 `E:/edk2-samurai-out/kernel453/af-config-source/`的新唯一文件。若分段传输，限定为这个单库，逐段长度及最终完整SHA核对；不覆盖旧原件，不在手机写库缓存，不执行OEM ELF／dlopen或启动Android服务。

若只读访问中的HAL／库或挂载身份前后发生变化，输出只能算未接受原件；重新核现场来源后再处理，不用半份文件推导配置。关闭时复核同一boot、guard、原挂载状态和充电稳定字段；不重启、不刷写或修改充电。

## 获取后的离线边界

库原件匹配后，先从它自己的初始化／解析逻辑定位实际配置路径、加载顺序、locale及查找失败语义；下一次仅取它确实引用的必要配置。当前仍没有依据断言具体XML路径、键数或override分支。完整库／配置／数值私存，公开只记来源、SHA和已核语义。

该步骤补的是[AF来源报告](AF-CONFIG-SOURCE.md)中尚缺的外部配置权威，不重新读取326 EEPROM，不改变[条件个体步表](AF-INDIVIDUAL-NEXT.md)、checksum认证、供应商和物理搜索安全边界。当前只交付可复用步骤，没有自动live提取程序；实际节点／挂载／格式未知，先由主线读回限定元数据再具体化，避免把旧入口中的276 guard、手机写缓存和挂载动作直接重放。

本轮复核的281采集脚本SHA为 `9491327d31cfc78dfbbfaa7ff4e79a7b97097de1dbc92823b40afb3b7bb56b2b`；对应完整HAL及卸载收据直接链接于上文。251私有 `capture-stock.sh` SHA `06987d1cb20bac4ae452ea4fd76cb2e99f57a97c150a9ce56e0177ee9ad83ec0`、`capture-root.sh` SHA `106235f6d13a66ebb7bd6ae7fd65042724abbde1805a66c48c5cc093d93a62b5`与当时采集清单一致；它们包含GNSS追踪／服务动作，未执行、未复用。
