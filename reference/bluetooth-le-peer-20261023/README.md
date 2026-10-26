# 手机BlueZ GATT外设与Windows中央对端（2026-10-23）

交付 [phone-gatt-peer.py](phone-gatt-peer.py)，仅在主会话协调好设备窗口后运行。Windows GATT外设此前报告Aborted/ErrorSuccess，现改由手机广告、Windows中央主动访问。实机r2已完成上电、GATT及广告注册和恢复；Windows数据事务尚未执行，见[现场结果](../bluetooth-20261023/gatt-r2-validation.json)。

已按固定BlueZ5.87提交 `65d11edee469c24dcc8d075b8be9c040cebaaf98`审查官方example-gatt-server、example-advertisement和四份API；[来源与哈希](bluez-5.87-reference/manifest.json)、[固定文件获取器](fetch-fixed-sources.py)。注册依据是调用方连接ID+application path，不能用另一连接替它注销。因此脚本用独立private bus承载对象/注册，清理从同一连接显式注销并关闭该连接；另一控制连接才负责恢复adapter。

## 冻结的测试接口

| 项目 | 固定值 |
| --- | --- |
| Service UUID | `f0d19310-7a52-4d3f-9b14-0e4bb7f30001`，primary |
| RX UUID | `f0d19310-7a52-4d3f-9b14-0e4bb7f30002`，read/write，WriteWithResponse |
| TX UUID | `f0d19310-7a52-4d3f-9b14-0e4bb7f30003`，read/notify |
| TX初值 | ASCII `RMX1931-LE:READY`；RX初值为空 |
| 20B挑战 | ASCII `RMX1931-LE:`11B + uint32小端seq + bytes(0..4)5B |
| 47B挑战 | 同前缀/seq + bytes(0..31)32B |
| 默认Windows事务 | 20B seq1；仅MaxPduSize>=50再47B seq2；不默认多轮或超时重试 |
| 广告 | peripheral；只含该service UUID、LocalName `RMXLE`；legacy Flags+UUID+短名共28B |

中央先uncached读TX READY、订阅TX通知，再写RX。仅通过完整校验的Write触发TX Value信号，内容逐字回显该挑战；StartNotify只改变Notifying，不发送READY。中央必须按完整seq及47/20字节内容核对通知、RX read、TX read，不能把订阅事件或READY当写后通知。

ReadValue处理offset；offset==len返回空，offset>len报InvalidOffset。Write仅接受完整offset0、type=request；拒绝非0offset、prepare-authorize、reliable/command与其它长度。47B必须有BlueZ提供的显式mtu>=50，缺少mtu也拒绝；不假装支持ATT长写或在MTU23发送47B通知。20B在默认MTU23即可进行。

## 运行前提与命令

先由主会话确认设备身份/回退及本次手机窗口；BlueZ标准服务与本机DMS地址已经正常准备；不与另一会话操作重叠。手机需要Python3、dbus-python、PyGObject/GLibUnix；HCI捕获默认优先btmon，缺少时使用已有原生monitor socket路径。测试要求当前无发现、无既有蓝牙连接、ActiveInstances=0。脚本不自动启动BlueZ，不调用Pair/Trust/Agent，不连接任何Device，不修改固件/NVM/配对文件。

runtime还必须显式传入本次交接的`--boot-guard-file`绝对路径与`--charging-manifest-sha256`。原生事务在首次adapter改变前只读核对：`/proc/sys/kernel/random/boot_id`等于guard文件内容、release精确为`7.3.0-rc6-rmx1931-samurai-k363+`、DT compatible含`realme,samurai`、`/usr/share/samurai-charging/manifest.json`摘要等于交接值；退出再次读取核对并记录。guard未通过时不进行adapter恢复写入或peer Disconnect。旧guard匹配仅证明启动身份，不能替代本次健康/设备窗口确认；脚本不硬编码实际boot ID、对端地址或本次manifest摘要。

从Windows中央程序的私人probe JSON取得 `BluetoothAdapter.BluetoothAddress`，转换为冒号分隔地址供白名单。它是公开API返回的适配器标识，不保证等于隐私随机化后的空口LE地址；若BlueZ实际Device.Address不一致，应保留失败，不能自动放宽白名单或扫描/连接未知对端。

以下命令仅是待执行示例，PEER地址通过本次私有参数传入，不写进公开报告；`--output`必须是**不存在的新目录**且父目录已存在：

```sh
umask 077
python3 /var/lib/samurai/tools/phone-gatt-peer.py \
  --adapter /org/bluez/hci0 \
  --peer-address "$WINDOWS_ADAPTER_ADDRESS_PRIVATE" \
  --boot-guard-file "$CURRENT_BOOT_GUARD_FILE_PRIVATE" \
  --charging-manifest-sha256 "$CURRENT_CHARGING_MANIFEST_SHA256" \
  --capture-backend auto \
  --seconds 60 \
  --output /var/lib/samurai/bt-le-current/new-server-run
```

脚本注册成功才打印 `ready:true` 与剩余秒数。Windows必须等该ready并在同一截止时间内执行；当前phone广告地址由主会话私下核对后传中央，不能靠RMXLE名称推断身份。默认测试20B一次、条件满足再47B一次，中央未执行的47B应记录未跑而不是通过。

## 有界生命周期与恢复

- 一个monotonic deadline覆盖setup、注册和服务窗口；注册异步执行以允许BlueZ回调GetManagedObjects。每次D-Bus调用固定显式timeout且限制在剩余窗口，不自动重试。
- 所有BlueZ代理固定第一次GetNameOwner的**unique owner**，`introspect=False`；well-known名仅用于只读owner查询/监视。daemon消失或替换就异常退出，不访问新owner、不隐式激活BlueZ。
- 开始前只读保存Powered/Pairable/Discoverable及两个timeout属性；临时Powered=true、Pairable=false、Discoverable=false。LE广告独立声明Discoverable；其余adapter属性不写。
- 每次Read/Write要求BlueZ options.device属于当前adapter且Device.Address严格匹配指定Windows地址；缺失device或其它peer均NotAuthorized。StartNotify没有device参数，只有公共测试值可被通知；敏感资料从不进入特征。
- 捕获先于adapter写和注册启动；默认`--capture-backend auto`优先btmon，仅找不到该命令时选择native-monitor。显式`btmon`缺失即失败；btmon运行中失败不会偷偷换后端。ready/summary明确输出backend和format，不能把原生JSONL称为btsnoop。
- btmon输出私有btsnoop/text，子进程设置parent-death SIGINT，普通结束SIGINT等待3秒；异常才终止子进程并记录失败。原生后端复用[kernel130 open_channel(2)](../kernel130/bt_mgmt.py)的sockaddr_hci只读monitor绑定和[kernel185 record_hci](../kernel185/test-bluez-scan-preserve-pairs.py)的`monotonic`+`packet.hex()`私有JSONL，不发送HCI/MGMT命令。该格式包含6B monitor header，可供已有缓存SCO解析器读取；绑定HCI_DEV_NONE，保留本机monitor事件，原件始终私存。
- 原生读取线程使用0.25秒recv timeout；停止时设置event、关闭socket FD、最多1秒join并核对线程结束。线程异常保留在summary并使本轮失败；GLib每200ms检查捕获健康，每次adapter写/注册及数据请求也检查，失败就停止试验。cleanup继续完成已拥有状态的恢复后关闭捕获，不因捕获故障放弃恢复。
- 到期、SIGINT/SIGTERM、注册失败、advertisement Release或BlueZ owner消失均停止接受请求。显式UnregisterAdvertisement/Application，撤除本进程对象并关闭私有注册连接；关闭连接也使晚到注册回包失效。
- 仅对已指定Windows peer且本轮仍Connected时调用Disconnect，随后核对；不对未知Device发操作。恢复本轮尝试改变的三个adapter属性，并核对原超时属性及广告ActiveInstances=0。
- 配对key段与本地identity在RAM计算摘要，前后必须相等；只写脱敏摘要至私人事务目录。脚本不改keys，也不在差异时盲目覆盖合法密钥。任何差异使本轮失败，不能写“keys已恢复”。

正常清理共用30秒D-Bus截止时间、每次调用最多3秒，捕获器结束另最多5秒（原生线程最多1秒），不重试。某次注销、指定peer断开或属性恢复失败时仍尝试其余恢复步骤，并保留失败结果；清理仅允许当前adapter下匹配白名单的peer。不要用SIGKILL结束服务：任何用户态进程在被硬杀/整机掉电后都无法保证恢复adapter属性；D-Bus owner丢失能回收注册对象，状态仍需主会话只读核对。脚本没有后台启动或持久安装项。

私人输出包括events、adapter前态、key摘要、btmon和summary。summary只报告本机回调、发出了多少Value信号和清理结果；**不把本地信号发出等同于Windows实际收到，不声明完整LE硬件通过**。需与Windows完整挑战回执、HCI记录和实际服务/链路结果关联后由主会话判断。

## 已完成的离线验证

[offline-api-check.py](offline-api-check.py)在WSL启动全新的私人session dbus-daemon，导出真实service对象并从另一进程通过D-Bus实际调用。未接system bus/BlueZ/手机/无线。

九项覆盖：ObjectManager与flags；真实introspection signatures；Read offset/边界/peer gate；订阅不发READY；20B信号与RX/TX读回；拒绝偏移/prepare/reliable/command/坏载荷及47B小MTU/无MTU；47B MTU50逐字回显；StopNotify后写拒绝；SIGTERM撤对象和owner。

第一轮r1在功能调用后因严格stderr检查发现旧GLib signal API弃用告警而失败，原件私存；改用GLibUnix.signal_add后完整通过。脱敏结果见[offline-api-validation.json](offline-api-validation.json)。后续增加runtime身份guard、参数约束和异常清理独立继续/共同截止时间，offline-export明确不读取那些设备路径；保留原9项结果及当时源摘要，没有把它改成新runtime已验证。新增语法/参数检查见[runtime-guard-validation.json](runtime-guard-validation.json)。这不验证真实BlueZ注册、身份guard现场读取、HCI、控制器广播、Windows连通或实际恢复；这些仍待协调设备窗口。

新增原生monitor fallback后运行[offline-capture-check.py](offline-capture-check.py)的7项定向生命周期检查，见[capture-lifecycle-validation.json](capture-lifecycle-validation.json)：AF_UNIX注入包保持原JSONL格式、idle关闭、日志打开失败关闭FD、mock channel2 bind失败、接收故障触发停止、FD/线程/log收尾及参数隔离。该离线检查没有打开真实HCI socket或连接system bus，也没有重跑原9接口案例；旧报告中的source hash仍对应旧证据。其后实机r2实际打开并关闭原生monitor、收取443包，记录单独保存在现场结果，未冒称这些包证明GATT数据成功。

实机r1发现禁用introspection后，`Properties.Set`的Boolean参数被推断为`ssb`，BlueZ拒绝，尚未改变Powered。仅将该参数改为`dbus.Boolean(value, variant_level=1)`，使实际签名为`ssv`。[offline-set-variant-check.py](offline-set-variant-check.py)在新的私有session bus上使用GIO/GDBus严格接收端：旧调用被InvalidArgs拒绝且未进入处理函数，新调用收到v容器中的b；[单项验证](set-variant-validation.json)保留前后源摘要。当时未重复九项接口验证，该历史版本SHA256为`096d01f85bac9900ab5be3b9b2ad773070b0c7d2d68348344ae321112f8694ff`。

该修正的实机r2在约1.46秒注册成功，服务窗口结束后注销和恢复均通过、accepted_write为0。人工分步确认就绪时剩余17.83秒，小于35秒启动门禁，因此Windows没有运行；不能将其写为数据通过或数据失败。

后续静态修复已将日志、摘要和各资源关闭异常隔离，分离stopping/cleanup_in_progress/cleanup_complete，保留原门禁及共享30秒预算。[29项离线回归](../bluetooth-static-fixes-20261023/gatt/README.md)通过；当前脚本SHA256为`a1f7c44c8e863bf1fcec9e9e507c4e9d621b0410b17e38b9750f76cae33c9004`，联动器和音响工具同时更新固定摘要。原ssv/9API/实机报告不改写为新源码验证；相关未变方法摘要另已核对。用户暂不做蓝牙实测，当前只交付离线修复。

公开镜像仅本目录脚本/README、脱敏validation、固定官方参考与manifest；私有输出 `E:/edk2-samurai-out/bluetooth-le-peer-20261023`不镜像。
