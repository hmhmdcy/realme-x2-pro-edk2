# kernel103：正确MAX98937/原生声卡与PCM回归

Linux #102已真实部署，双ID43/原生声卡/有限48k stereo播放和关闭归零通过；两次5.04秒录音DMA正常但全零，数字mic电源/路由仍待修；版本查询和一次core重绑仍失败。5GHz连接及网络通过，BT停止无配对，振动确认暂缓。

见[session103](../../sessions/103-native-max98937-card-pcm-and-zero-microphone.md)、[下一轮](next-session.md)。240文件checkpoint `c97b8765c3c5e704ef29e845e4b3f1ec2bbc3aca9a8c8ca80f409b0506057826`，原包/nested清单/读回/FDT/NV/persist通过。这里只含自写源/脚本/补丁和脱敏说明；所有录音、原日志、原厂XML/库/固件、凭据/身份、镜像/二进制留私人目录。

guard及失败原脚本保留，实际完整runtime是retry1、checkpoint是retry2。不得盲目重放已存在目录。正确功放驱动已拥有GPIO37/148，旧kernel102 ID-only工具现在不适用。新源码/设备树已应用到WSL真实树，linux-port/dts旧镜像保持。15组硬件goal active。
