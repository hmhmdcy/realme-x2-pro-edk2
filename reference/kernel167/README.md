# 167：拒收166后回退kernel163

2026-10-14。使用失败166的新boot身份停止桌面、无线、ADSP，功放静音且未播放。退出时fbcon blank返回EBUSY，VT已解绑、无DRM用户态client，但CRTC仍active；单独记录失败退出状态，没有伪报CRTC正常关闭。原告警基线taint640/WARN1保留。

F2FS冻结、一次F1回执及真实bootloader核对后，只刷核验过的原字节logdump163，保持boot164、modules/software132和Mesa149。

新启动uname构建号163、taint0，但声卡仍缺失，旧驱动再次出现DMA prepare及QMI wait timeout。回退恢复了原镜像字节，并未恢复此次启动的音频。运行原件保存在私人kernel167目录，继续168生命周期候选。
