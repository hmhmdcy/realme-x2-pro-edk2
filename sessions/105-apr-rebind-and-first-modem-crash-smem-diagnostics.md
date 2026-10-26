# 阶段105：APR重绑登记恢复，首次MPSS无崩溃原因项

2026-10-11，Linux #104真实部署；全硬件目标继续，尚未完成。

手机已部署Linux #104（阶段105），本轮仅刷logdump；DTB、整个boot分区、原CPIO/模块/无线/显示源码保留。
APR服务登记移至每次driver probe，解绑先移除登记并等待在途APR回调；修正包头长度边界。core查询使用非零事务token，只接受匹配回复，合法版本成功才缓存，未知basic错误不当unsupported，超时明确返回。首次原生回复AFE API7/ASM API2；一次正常core重绑后收到合法回复，第一次100ms查询仍超时，EUD读取期间一次有界复测通过，超时原件保留。
首次MPSS约40秒fatal仍未修复：SMEM421全局/调制解调器私有区均返回-ENOENT，崩溃原因项不存在。首轮没有来自modem的TFTP/RMTFS读写请求，原worker1与失败完整保留；唯一手动恢复后，同一组RAM COW服务收到真实请求，5GHz认证/DHCP/DNS/HTTP/网关3/3通过。
2秒-48.16dBFS有限播放回归退出0、双功放start1/stop1/failed0；DMIC0回归5.04秒/241920帧，非零230051，稳态208265非零/80种值/0削波，偏置和MCLK正常关闭；历史三路DMIC采样保留，实际声音和拾音质量仍无人确认。蓝牙保持停止、不配对连接；振动standby/starts0，无新脉冲，机械确认暂缓。
149文件检查点/八原包及全部SHA、新80块备份、完整分区读回与实际FDT/NV/persist/stock DTBO保留通过。检查点uptime444.61、恢复MPSS连续约279.8秒，双DSP running、taint0，历史首轮MPSS fatal1/ADSP0、显示超时4、BT phase2错误1。
下一轮优先首次MPSS启动的QRTR/GLINK/原生PD mapper请求链，检查core诊断日志与100ms时限相互影响，随后继续15组硬件。保留Android/data/GPT/NV/persist/SSH/rootfs01/F2FS/旧显示，固件/日志/身份/凭据/音频/镜像留本机，不提交推送；全硬件goal active。

## 源码与验证

修改仅drivers/soc/qcom/apr.c、drivers/remoteproc/qcom_q6v5.c和sound/soc/qcom/qdsp6/q6core.c；三个对象W=1零警告。APR登记原本只在device创建时发生，driver remove删除后probe不回填。本轮改为probe登记、严格ID/同指针冲突检查及失败回收；APR路径使用SRCU等待在途回调后释放，长度验证包含可选头边界。GPR动态端口生命周期未作完整验收，不宣称其它平台已测试。

core命令/事务token匹配，basic EOK只作ack，显式EUNSUPPORTED才fallback；其它错误返回EIO，合法版本表才缓存，超时ETIMEDOUT，不再假成功。新boot首次FWK回复116字节，token1；正常重绑后登记和回复恢复，第一次sysfs查询超时，一次EUD读取期间复测返回API7/API2。日志输出导致响应处理超过100ms是待证解释，本轮没有用永久延长delay掩盖问题，未重启ADSP。

真实fatal IRQ只读SMEM，记录返回值/长度及ready/handover状态，字符串最多4096字节且不写SMEM。全局和modem-host1的421都ENOENT，不能将其解释为已取得DSP错误。原厂同机[remoteproc源码](https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2Pro-kernel-source/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/remoteproc/qcom_q6v5_pil.c)也使用全局项；本轮只增加有限读取诊断。

[上游tqftpserv](https://github.com/linux-msm/tqftpserv)支持临时readwrite探测；本机既有server_check RAM支持及SM8150原生PD mapper映射已存在。首轮失败没有modem文件请求，恢复后同一组服务收到server_check、wlanmdsp及RMTFS请求，尚无证据支持改NV或扩大持久写权限。

Image SHA `01d777dff25a16185cfdbb3c68f2dca59604d2024f6ee0067fc25e641bfb4193`；DTB/CPIO分别`2a9e3cac62e7f6b8eb767230b630ddbeee546535acf9eec225bf3591dd623cbb`/`71f0fac2cb4251214ba33c86bf332e2367cbaf676f877c4030d1228e71c64ae7`，字节保持。候选logdump SHA `f42f219c2bc52ecb53e4b32f8e7a3b51524987a23bec3c911590d72fa3d880d1`；完整boot保持 `d1f81ebc4dc9687b705cffe38ecde93b8c4cd60a4c37463901b7cf7b900e1278`。DTB没有变化，因此复用阶段104已校验的真实嵌入DTB，未重建或刷boot。仅logdump一次写入，F1后独立fastboot确认身份/大小/候选SHA；NV/persist/stock DTBO不变。

八原包包含初始runtime、一次core重绑、有界core复测、有限播放/DMIC0、首轮失败、一次恢复及5GHz测试。检查点 SHA `f14b32a972043f32cb6d80e1b608581441dceaa78945a5cb3da8126ec17211f5`，149文件/全部嵌套SHA及原包逐字节匹配。早期SSH未就绪与候选首次运行时备份尚未拼接的失败均未触发刷机；原失败记录保留。SRCU错误退出路径已在刷机前静态修正并重新构建。

## 后续

首次MPSS自up 46.025205至fatal诊断85.874033，约40秒，auto1保留。下一轮按优先级采集原生PD mapper请求/回复与QRTR/GLINK启动事件，比较失败和唯一恢复，不能无界重启DSP、强制crash或猜测NV内容。检查core诊断输出在事务完成前阻塞的可能性。2.4GHz reason7、删除等待、显示超时、BT传输、冷启动/休眠等仍在待办。

用户无需补充振动物理反馈；蓝牙不配对连接，NFC无标签仅控制器。音频实际声音/质量、耳机/DSM/校准未确认。充电收尾，不重放OEM充电/OTP/unseal/FET/OTG/MCU/GPIO/I2C_FORCE探针。保留rootfs01/F2FS和Android全部数据，不提交推送。详见[15组状态](../linux-port/docs/HARDWARE-STATUS.md)和[下一轮](../reference/kernel105/next-session.md)。
