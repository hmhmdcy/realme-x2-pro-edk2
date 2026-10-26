# 联动目录和播放状态修复

[run-gatt-window.py](../../bluetooth-20261023/run-gatt-window.py)现在在读取基线、启动SSH/手机服务之前，要求输出位于`bluetooth-windows-central-20261023`专用私有子目录，与未修改的Windows中央程序一致。配置和结果都由该输出目录产生，不再等到手机注册后才遇到Windows路径拒绝。

[low-volume-speaker.py](../../bluetooth-speaker-20261023/low-volume-speaker.py)解除静音后立即读回`mute=False`，播放期间核对同一sink的index/name、低音量上限和静音状态。还按本次paplay PID及application.name识别唯一音频流，拒绝流被移动或静音，成功必须实际观察到流在目标sink未静音且uncorked。轮次私有记录保存播放期观测；采样观测不等于连续硬件状态或实际发声验收。

请求仍为10%、PCM峰值0.10FS、2秒和50ms渐变；硬件取整读回上限15%，没有自动提高音量。GATT服务与共享guard/capture的固定摘要已一起更新到清理修复后的`a1f7c44c8e863bf1fcec9e9e507c4e9d621b0410b17e38b9750f76cae33c9004`。原r3/r4源码已按旧SHA私存，旧实机报告不改写为新版本结果。

[validate-host.py](validate-host.py)直接执行实际路径门禁、播放状态方法和`play_quiet()`；模拟PA/子进程，用本地pipe消费PCM，没有调用paplay、pactl、音频设备、BlueZ、SSH或WinRT。九项定向用例覆盖路径契约与提前拒绝、sink静音/未知静音、stream静音/移走、正常播放、播放中途静音、无本次音频流。所有用例通过，失败仍重设静音。结果见[validation.json](validation.json)。

流身份依据固定PA17上游实现：[pacat.c](https://github.com/pulseaudio/pulseaudio/blob/1f020889c9aa44ea0f63d7222e8c2b62c3f45f68/src/utils/pacat.c)、[context.c](https://github.com/pulseaudio/pulseaudio/blob/1f020889c9aa44ea0f63d7222e8c2b62c3f45f68/src/pulse/context.c)、[proplist-util.c](https://github.com/pulseaudio/pulseaudio/blob/1f020889c9aa44ea0f63d7222e8c2b62c3f45f68/src/pulsecore/proplist-util.c)及[sink-input.c](https://github.com/pulseaudio/pulseaudio/blob/1f020889c9aa44ea0f63d7222e8c2b62c3f45f68/src/pulsecore/sink-input.c)；相关原文段落和来源见[pa-stream-identity-source.json](pa-stream-identity-source.json)。

## 两处最小工具内去重

本轮仅让联动器的`eligible`、远端READY计算和`--seconds`参数共用既有`SECONDS=60`。45秒门禁、Windows总预算30秒、SSH/进程/清理超时保持。speaker单文件新增`pulse_client_context()`，pactl与paplay共用UID10000、账户GID、HOME、PULSE_SERVER、XDG_RUNTIME_DIR、USER、LOGNAME和空extra_groups；不新增公共模块。配对逻辑、10%请求、15%取整上限、波形和2秒长度保持，phone源码仍为`a1f7c44c…33c9004`。

本轮前两个工具原字节、旧验证器和九例结果保存在私有`bluetooth-static-fixes-20261023/host/before-convergence`新目录，未覆盖上轮before。旧[validation.json](validation.json)继续对应旧源码。新[convergence-validation.json](convergence-validation.json)为本轮实际执行结果：原九例及两项新增用例共11项，一次通过；没有重跑phone29例或内核验证。

发布检查发现新增时长用例的合成地址会被脱敏器替换，已改用保留的合成地址，仅补验该实际`duration_case()`通过。其它十例未重跑，两工具源码摘要不变；最终验证器摘要及这次补验记录在新报告中。

新增用例直接执行实际`Window.audio()`与`play_quiet()`，由模拟pactl/pipe播放器记录并比较完整客户端环境及credentials；实际`run()`使用明确模拟的SSH/进程/调度回调，将测试值67送到三处时长使用点，核对45/30和原超时不变。没有真实SSH、pactl、paplay、音频设备、BlueZ或WinRT调用。

当前工具SHA256：

- run-gatt-window：`5d31c333629cd591493b9b957a005b3741c818b5bef9bb6646d1c27dfaef3906`
- low-volume-speaker：`b9c6dbcb27e16efdbf4c5edac0385be1ca25f8d76ed4567350b69c8d2d9dc7a1`

本轮已运行命令（结果文件保留，不原路径重放）：

```powershell
wsl -d Ubuntu -u root -- python3 -B '/mnt/e/RealmeX2Pro edk2/reference/bluetooth-static-fixes-20261023/host/validate-host.py' --output /mnt/e/edk2-samurai-out/bluetooth-static-fixes-20261023/host/convergence-validation-private.json
```
