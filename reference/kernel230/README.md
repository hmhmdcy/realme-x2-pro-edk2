# 230：树内FastRPC新启动与真实传感器验收通过

2026-10-16。228正式树内构建的FastRPC `2abde0ea…`/50192B现已在手机新启动230实际加载，build-id与根文件系统一致、intree=Y，**taint=0**。不再运行外建7ca5/O4096。没有刷写分区，boot219镜像/Image183、相机e49/fae1及r13/r8保持。[自动启动收据](runtime-validation.json)

自动服务取得70条加速度、10条光线测量，三DSP running、SensorProxy三Has真。随后五路标准SSC取流各67/44/9/10/1条（加速度/陀螺仪/磁力计/光线/接近），均正常disable；真实ADSP open使refcount1→2，close后回1。实际active seat0 Wayland UID10000三项Claim/Release通过，原daemon身份保持、Polkit策略未改。[原生测试](native-sensors-validation.json)、[可读原生源码](native-sensors.py)

重启清理曾被两处脚本前置校验拦住：生成器把电源轨num_users应为0误写4096，发生在相机卸载前；旧显示脚本仍要求taint0，发生在任何模式切换前。各次失败、原脚本与worker均保留，核验准确阶段后分别仅继续剩余步骤。最终相机六模块、GUI/DRM、三个DSP、Wi-Fi及音频均清理通过；冻结前再次核对实际上传路径/散列及当前身份，FastRPC refcount已为0。仅一次Linux→bootloader、fresh fastboot身份核验后一次reboot，无flash。末尾USB回执丢失，未重发；由fresh fastboot及新Linux身份闭合。[恢复与切换收据](preboot-recovery-validation.json)

[最终健康](final-health-validation.json)：无WARN/Oops/GPU/DSP fatal/BT重组故障，taint0；772ko/786相关文件与此前228暂存清单一致，944包数据库、程序配置、NV/persist、boot/logdump保持。相机和CCI/CAMSS休眠，前摄双轨关/用户0，16MP实验N；Wi-Fi连接、chrony Normal，BT关/无连接；GPS0/Signalsfalse/rate30，watch空闲、UTC自动准备、data worker0。没有手工搜星或注入，226的168h XTRA仍是旧启动证据。无SIM时MM failed/原因2/Power1，不视为真实入网验收。

完整源码/补丁和当前产物锁在[SSC内核目录](../../linux-port/ssc/kernel/README.md)，canonical after228保持；树内与已测外建19540字节.text逐字一致。原189模块88553与外建7ca5回退都保留；本次没有热换活跃模块。私人原生归档116成员逐项核对，包含两次前置失败、修正流程、新启动及原生测试，指纹未公开。[归档收据](evidence-validation.json)

前摄白天32帧已有真实颜色信息，未保存场景照片，[229记录](../kernel229/README.md)保持。本阶段没有重拍，也没有据统计宣称颜色准确。SSR/invoke/put_work/DMA排空、reclaim−22、新模块PM/物理精度、后摄四路、GNSS正CNR/fix、BT phase5及整机长稳仍未完成。完整外设goal继续active。
