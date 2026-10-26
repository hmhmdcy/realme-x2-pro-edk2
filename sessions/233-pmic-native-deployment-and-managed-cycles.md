# 233：后摄 PM8008 依赖部署与原生循环

232的两个树内模块及DT-only boot已受控部署：P/Q/provider绑定、P身份读取和无P供电子设备通过。Q暖重绑保留七路状态/电压，provider冷重绑经GPIO事件核对P/Q顺序并完成一次8→4迁址；前摄RAW/RGB各6帧回归、恢复通过，taint/fault0。

只刷boot，旧模块/元数据/boot219回退均保存，未修改NV或logdump。原子安装异常路径经三故障验证，现有195驱动保留到重启。后摄尚未出图，未知VIN和真实sensor供电/模式继续推进；前摄纯色参照按用户延期，完整目标active。

[原生收据、代码与具体边界](../reference/kernel233/README.md)。
