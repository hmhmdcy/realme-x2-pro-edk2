# F.10 system与工程模式：充电资料定向补查

2026-10-24。在[同一OTA的vendor检查](../gauge-2719-vendor-name-index/README.md)后，补齐system分区和内嵌工程镜像的文件名范围，再静态检查相关文件。原厂文件、完整目录索引、APK/DEX内容均私存；未运行提取出的任何程序，也没有手机、SDK、挂载或生产策略操作。

## 实际提取与目录范围

[extract-system.py](extract-system.py)只增加固定system输入封套，直接复用原已审查的transfer解析、CRC/EOF成员复制、Brotli解码器及镜像重建函数；原vendor源码和13项小样本结果保持，不重跑旧矩阵。system transfer为v4，new/zero/erase完整覆盖，header的1047991是new+zero块数，镜像范围为1095680块，不能把header当分区大小。

原执行79585及其Python206860、Node220352均终态0：压缩成员2196143558B、CRC `1d70832f`与EOF核对，解码4219551744B，完整重建4487905280B镜像 `f7a3c832…1e0728f`。输入容器stat、小元数据与工具/源码前后保持；未认证整个OTA的SHA、签名或电池包身份。

[index-system.py](index-system.py)复用原debugfs目录解析器，原执行59344终态0。606目录、5333唯一路径（605目录、4436普通文件、292链接）与606个原debugfs调用闭合，全部终态0；只读、不跟随链接。索引前复用刚完成的producer镜像SHA，前后stat保持，不重读大镜像重复计算SHA。四个描述后缀 `.bqz/.bqfs/.df.fs/.srec` 没有文件名命中；这不证明嵌入、压缩、改名内容或其它OTA中不存在描述数据。

从该索引选取工程模式APK、电池异常XML、工程镜像、64位充电HAL库及system build.prop五个普通文件，以[read-files.py](read-files.py)只读取得，五个原子进程均终态0。内嵌 `my_engineering.img` 仅348160B，另只读列完五个目录、七个普通文件，都是build/权限/功能/NOTICE类名字；没有读取其文件内容或挂载。

## 本轮结论

工程模式、异常电池检测配置和HIDL接口只能按各自静态证据使用，不能替代本机MP2650/电量计的寄存器、保护或协商协议。具体内容检查范围、SHA及结果列在[result.json](result.json)。system build.prop为通用qti/qssi、Android11/2021-03-05补丁，未由此认证精确机型、电池包或2719固件。

| 检查输入 | 确认的范围与限制 |
| --- | --- |
| `OppoEngineerMode.apk` | 1221个ZIP成员名及64个assets名字；只完整读取5414232B的classes.dex，检查34688个string项。2719、完整固件指纹、bq27541/bq28z610和三个新MAC名称无命中；有PSY/proc工程测试接口。不检查所有assets内容、不认证APK签名、不作DEX完整校验或指令控制流证明 |
| `sys_bad_battery_config.xml` | 标签／注释提示异常电池检测，consumer、单位和双电芯缩放未确认，且CV时长注释和值不一致；不将其数值移植为内核停充或保护规则 |
| `vendor.oplus.hardware.charger@1.0.so` | 完整145360B的ASCII字符串／符号检查，见ICharger的Battery/USB查询等HIDL封装；接口名不证明后端实现或当前Linux策略 |

目前仍未取得匹配DeviceType2719与完整11字节固件指纹的命令/位说明。本轮没有扩MAC白名单、改TCA/Full分类、照搬工程停充值或解除保护，也未更改桌面。生产接入顺序保持：先实际验证既有prepared502外供通知修正，其它USB中断和PM配套另建窗口。
