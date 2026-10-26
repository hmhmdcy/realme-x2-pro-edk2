# 166—169：原生音频服务生命周期修复与两个独立启动

2026-10-14。当前操作边界保持。用户要求继续修复原生Linux音频，并回复“暂时不方便，先完成软件验证”。本轮未做现场听音/耳机插拔，录音、日志、身份与镜像留私人输出目录。

重新解析164旧档案：首次失败先唤醒失败，随后NGD DOWN/QMI handle1/TX channel0，917次DMA prepare与WCD efuse WARN。没有休眠拒绝日志，不能据此归因于QMI拒绝休眠。本轮旧163正常ADSP停止又新增70次prepare失败，诊断同样DOWN/channel0。

166先修PM/DMA回收及WCD错误处理，39项宿主检查通过，但实机首启无声卡，TX timeout1、WCD回调Oops及IDA重复释放WARN1、taint640；明确拒收。166停机fbcon blank返回EBUSY且扫描输出仍激活，按已记录失败boot退出，没有伪报正常关屏。167只刷回原字节logdump163、taint0，但音频仍缺失，旧DMA/QMI等待故障复现。[拒收166](../reference/kernel166/README.md)、[回退167](../reference/kernel167/README.md)

168进一步修复master worker在注册前通知客户端、DOWN与UP并发DMA释放、重复控制器注册/注销及被消费的服务器completion。设备删除前排空master work，所有SSR清理在同一锁内，DMA退出再等tx_lock；保留139的未提交槽位/TID回收。错误按链传递，WCD遇到初始化/efuse/版本读错误停止初始化。修改限于3个音频源文件，boot164、DTB、显示、software/modules132和Mesa149保持。[最终补丁](../reference/kernel168/audio-lifecycle.patch)

W=1对象及checkpatch通过；完整构建有继承的1条EUD unused-function警告。宿主39项与100轮DMA/100轮UP-DOWN均通过，负对照能拒绝旧错误；不将桩测试称为真实并发。770模块除两处build-id外字节一致；实际FAT/分区读回匹配，163回退保留。

168首启和169第二次同镜像独立启动均声卡存在、WCD0x411、taint0，DMA prepare/TX timeout/queue full/resume failure/WARN均0。每boot各3次2秒低幅原生播放、三路DMIC各3秒/144000帧、一次桌面播放通过，关流后双功放关闭静音；采样后2.5秒均非零且无满幅削波。初次桌面测试文件权限错误已保存，标准输入补验通过。首次168正常ADSP停止时prepare仍0，改善了旧163同流程70次失败。[168首轮](../reference/kernel168/README.md)、[169复测](../reference/kernel169/README.md)

这些结果支持本轮已测初始化/停止及有限PCM回归，未证明164每个时序因素的唯一根因，也未验收实际声音、已知声源/录音质量、启动瞬态、耳机、断电冷启动、休眠及长稳。后续保持音频目标继续，勿混用不同boot的稳态和显示测量。
