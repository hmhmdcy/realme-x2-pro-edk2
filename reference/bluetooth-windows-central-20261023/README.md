# Windows BLE central：专用手机 GATT 对端

2026-10-23。独占目录，未操作手机或 SDK。真实 Windows C# 编译与不连接设备的 watcher probe 已通过；run 模式尚未执行，不能据此称手机 GATT、配对、连接或音频通过。

接口遵循[微软 GATT client 文档](https://learn.microsoft.com/en-us/windows/apps/develop/devices-sensors/gatt-client)。与手机 server 约定：

| 用途 | UUID / 值 |
| --- | --- |
| 专用服务 | `f0d19310-7a52-4d3f-9b14-0e4bb7f30001` |
| RX | 同前缀 `0002`，Read / WriteWithResponse |
| TX | 同前缀 `0003`，Read / Notify；初值 ASCII `RMX1931-LE:READY` |
| 默认短写 | ASCII `RMX1931-LE:` + uint32LE seq=1 + bytes 0..4，共 20 B |
| 默认扩展写 | 同前缀 + uint32LE seq=2 + bytes 0..31，共 47 B；仅 `GattSession.MaxPduSize >= 50` 时运行 |

run 必须从私有配置读取精确手机地址，匹配该地址和专用服务 UUID 后才创建 device；名称不作为识别条件，不连接其它设备。先 uncached 读取 READY，注册 TX 回调并成功写 CCCD Notify，再逐条向 RX WriteWithResponse，要求同 seq 的完整通知及 RX、TX 两次 uncached 读取均逐字匹配。默认仅两条，不自动重试、不配对、不请求 MaintainConnection。

手机 server 拒绝非 request、非零 offset、prepare/reliable/command 写入；47 B 在 server 的 MTU 未提供或小于 50 时也拒绝。双方不能据 Windows 的 PDU 能力位跳过实际 write/notify/read 验证。

## 编译与 probe

`build.ps1` 使用本机 `Framework64/v4.0.30319/csc.exe` 和 `Windows Kits/10/UnionMetadata/10.0.26100.0/Windows.winmd`，引用 System.Runtime、WindowsRuntime、System.Core、System.Web.Extensions，`/warn:4 /warnaserror+`。EXE 与原始记录仅输出到：

`E:/edk2-samurai-out/bluetooth-windows-central-20261023/`

```powershell
& './reference/bluetooth-windows-central-20261023/build.ps1'
& 'E:/edk2-samurai-out/bluetooth-windows-central-20261023/windows-gatt-central.exe' --probe 'E:/edk2-samurai-out/bluetooth-windows-central-20261023/new-probe-private.json'
```

probe 仅查询本地适配器并启动专用 UUID 过滤 watcher 约 1 秒，然后 Stop/移除事件；不会调用 FromBluetoothAddressAsync，不创建任何设备连接。真实 probe 的状态为 Started → Stopped，device_creation_calls=0、cleanup_errors 为空、未完成 WinRT 操作计数 0。附近地址/名称不会输出。

两份 probe 对应的源码/EXE SHA 单独保留；最终修订使用 Stopwatch 单调总预算，并保证非 Success service result 中已返回的 service 对象也进入统一释放路径。最终修订再次实际编译通过，按主线要求未重复 probe，不能把前一版本的 probe SHA 写成最终版本。[验证](validation.json)

初次编译缺少显式 System.Core 引用，第二次遇到 C# 5 不支持 await-finally；均为编译失败，没有执行设备操作。添加引用、改为所有异常进入同一 cleanup 后编译/probe 成功，初次日志保留在私有目录。

## 受控 run

手机窗口未知时不能 run。先由主线确认手机 server 就绪、获取其本次准确地址，并在私有输出根创建配置；[示例](config.example.json)故意不可直接使用。`expected_address` 要求 12 位十六进制、不含分隔符，`server_window_confirmed` 必须明确为 true。不得公开真实地址。

```powershell
& 'E:/edk2-samurai-out/bluetooth-windows-central-20261023/windows-gatt-central.exe' --run 'E:/edk2-samurai-out/bluetooth-windows-central-20261023/run-private.json' 'E:/edk2-samurai-out/bluetooth-windows-central-20261023/run-result-private.json'
```

结果文件必须为新路径；存在时拒绝覆盖。每项 WinRT 操作、广告等待、通知等待、watcher 停止及 CCCD 清理均有界；整体业务预算为 Stopwatch 单调时间，UTC 仅记日志。超时不重试，记录 Cancel 请求、释放时状态与未完成操作；WinRT 连接过程不能据 Cancel 认定结束，晚返回对象的释放只在进程仍存活时尽力执行。

cleanup 尝试 CCCD None、取消事件订阅，Dispose 所持 service/session/device，Stop watcher。日志明确区分“释放引用”与“物理断开”，始终不将 Dispose 计为已证实断链；必要断链证据由手机端独立记录。

本地适配器地址仅保存在私有 JSON 的 `local_adapter_address_private`，可供主线填写手机 server 的 peer 守卫；它是 Windows API 返回的适配器地址，不是本轮空口 LE 地址已证实。若 server 观察地址不同，保持严格拒绝并保存失败，不自行放宽匹配。
