# Wi-Fi 5 GHz latency defect (2026-11-20)

状态：**部分修复（2026-11-20 19:00）**。regdb 与 5 GHz 监管域已修好，
power save 已修好；每包 +200 ms 级别的 RTT 仍未闭环，但已排除本机
Wi-Fi 协议栈（PC 对同一 AP 的 5 GHz 甚至扫不到，见 §10）。

历史基线：2.4 GHz 正常；5 GHz 在 -62 dBm 下有 500-700 ms 平均 RTT。

复现命令（只读，不改任何配置）：

```sh
linux-port/scripts/check-wifi-band-latency.sh wlan0 25 192.168.0.1
```

## 1. 测量结果（同一台手机，同一 AP，只切频段）

路由器 `TP-LINK_156D`，手机 `wlan0`。目标 `192.168.0.1`，`ping -i 0.2`。

| 频段 | 信道/带宽 | 信号 | 平均 RTT | 丢包 |
| --- | --- | --- | --- | --- |
| 2.4 GHz | ch11 / 40 MHz HT | -46 dBm | **11-26 ms** | 0-4 % |
| 5 GHz | ch36 / 80 MHz VHT | -62~-65 dBm | **560-720 ms** | 0-40 % |

同一时刻从 PC（Intel AX210，2.4 GHz ch11）ping 路由器：平均 3 ms、0 % 丢包，
说明路由器与有线侧正常。

## 2. 已排除的假设（每条都有对照实测）

| 假设 | 对照实验 | 结果 |
| --- | --- | --- |
| 手机协议栈慢 | 手机经 NCM/USB ping PC | 0 % 丢包、0-1 ms → 排除 |
| 路由器 VLAN / AP 隔离 | 手机 ping 路由器、PC、公网 DNS | 都能通 → 排除 |
| 省电 / U-APSD | `iw dev wlan0 set power_save off` | 仍 546 ms → 不是主因 |
| 唤醒后停 EBUSY | `usb-signaller` SIGSTOP | 丢包 20 %→0 %，RTT 仍 543 ms |
| CPU idle 唤醒延迟 | 8 核全 `dd` 忙时 ping | 仍 500 ms → 排除 |
| 蓝牙共用天线抢占 | `bluetoothctl power off` 后 ping | 仍 526 ms → 排除 |
| TX 聚合定时器 | debugfs `htt_max_amsdu_ampdu` 1/1、2/8、3/64 | 都 ~900 ms → 排除 |
| 选速过高 | `iw set bitrates` 锁 VHT MCS0-3 / 纯 legacy | 仍 487-868 ms → 排除 |
| PA 过驱动 / 失真 | `iw set txpower` 30/20/15/10 dBm | 仍 611-767 ms，10 dBm 更差 → 排除 |
| 队列积压 / 串行化 | 20 包 @0.2 s 理论 4.0 s，实测 4.5 s | 未积压 → 排除 |
| 大量重传 | `fw_stats` 差分：20 ping 只多 ~21 个 HTT cookie | 未大量重传 → 排除 |
| 同频强干扰 | 扫到 `USER_858061_5G` 在 ch36、-66 dBm | 强度相当，**仍是候选** |

## 3. 决定性观察：双峰分布

5 GHz 的 RTT 不是“整体变慢”，而是**两个峰**：

```text
seq=7  time=167.4 ms
seq=8  time=  2.9 ms   <- 与 2.4 GHz 相同的快路径
seq=9  time=837.8 ms
```

`min` 始终在 1-1.7 ms，说明链路本身能跑很快；慢的是**多数包的额外 ~500 ms**。
且 20 包 @0.2 s 在 4.5 s 内完成（理论 4.0 s），排除了“包堆在队列里”。

这与“逐包重传”不同（重传计数没有对应增长），更像是**下行帧在 U-APSD
服务期之外被 AP 缓存**，或**该 AP 对这台手机的 5 GHz 调度有问题**。
注意 PC 完全扫不到这个 AP 的 5 GHz BSS（只看到它的 2.4 GHz），而手机能 ——
两台机器的 5 GHz 能力/驱动差异本身值得单独排查。

## 4. 相关但独立的缺陷

### 4.1 `/lib/firmware/ath10k/WCN3990/` 不被任何包拥有

```text
$ apk info -W /lib/firmware/ath10k/WCN3990/hw1.0/board.bin
ERROR: ...: Could not find owner package
$ apk list -I | grep linux-firmware
(空)
```

该目录是 `samurai-wifi.sh` 从 `/run/samurai-wifi/firmware/` 挂进来的
（`/sys/module/firmware_class/parameters/path` 指向它），源是同机分区。
官方仓库有 `linux-firmware-ath10k-20260519-r0` 但**没有安装**。

关于 `firmware-5.bin` 只有 60 字节：这是 ath10k 的 **firmware IE 索引**，
实际固件由 WCN3990 通过 QMI 从 `qcom/sm8150/realme/samurai/` 加载，
所以 60 字节本身不是缺陷（`dmesg` 显示 `firmware ver api 5 features ...`
已成功）。但“无主文件”这一点仍违反“发行版推行接口”，应收敛。

### 4.2 `usb-signaller` 每 2.07 秒一次 `mode_request()`

```text
$ journalctl -b | grep -c 'DBus: mode_request'
22116            # 本次开机
$ journalctl -b --since '60 seconds ago' | grep -c 'DBus: mode_request'
29               # ≈ 每 2.07 s
```

每次都会重新执行 `Loaded URS ... UDC: Developer`。`SIGSTOP` 掉
`usb-signaller` 后丢包从 20 % 降到 0 %，所以它至少是**丢包的来源之一**，
但 RTT 仍有 543 ms，不是全部原因。这个 2 秒周期与部分 RTT 平台吻合并
存疑，需要继续查调用者（`usb-moded` 的 DBus 信号）为何持续重发。

**已定位并修复（`samurai-platform` 6-r23）。** 调用者不是 usb-moded，
而是板级 `samurai-usb-recover monitor`：它的 `dbus_usb_mode()` 用
`com.meego.usb_moded.mode_request` 去“读当前模式”。

`mode_request` 是 usb-signaller 的标准 getter，但它**每次都会重新装载
URS 并重新应用 UDC**（日志里的 `Loaded URS ... UDC: Developer` 就是它），
所以每 2 s 的无条件轮询等于每 2 s 重建一次 gadget 状态。用
`dbus-monitor` 看，每个请求来自一个**新的短连接**（`:1.8946→:1.8947→…`），
证实是脚本每次 fork 一个 `dbus-send`。

不能直接换成 `get_modes`：它返回的是**支持的模式列表**
（`developer_mode,tethering_mode,charging_only,mtp_ffs_mode,host_mode`），
不是当前模式。usb-signaller 也不发 `sig_usb_event_ind`（25 s 内 0 条），
所以无法用信号订阅替代轮询。

改法（自适应轮询，保留全部恢复能力）：

```text
configured+carrier 稳定 >= 30 s  → 8 s 轮询（idle_interval）
其他任何状态（MODE_UNKNOWN / 无 VBUS / 枚举卡住 / 模式切换） → 2 s 轮询
```

实测（同一 boot，改动前后对照）：

```text
before: 每 2.07 s 一次, 22116 次/4.5h
after : 每 8.08 s 一次, 30 s 内 4 次
5 GHz 丢包: 20-40%  ->  0-4%
NCM: usb0 172.16.42.1/24 正常, 三个服务均 active
```

RTT 仍 480-840 ms，所以它只是**丢包来源**，不是延迟根因。

### 4.3 内核噪声（不是本次延迟的原因）

```text
ath10k_snoc ...: invalid MAC address; choosing random
ath10k_snoc ...: supply vdd-3.3-ch1 not found, using dummy regulator
ath10k_snoc ...: received unsolicited stats update event   (重复)
ath10k_snoc ...: failed to request tpc config: -95
ath10k_snoc ...: unhandled tx completion status 5
ath10k_snoc ...: chan info: invalid frequency 0 (idx 41)
```

`fw_stats` 的 `RX frame count` 每秒涨约 1400 万，而网卡实际每秒 ~8 包，
2.4 GHz 下也照样暴涨，说明该计数器单位在这个固件版本里不可用，
**不能用它判断空口质量**。

## 5. 下一步（按信息量排序）

1. 用另一台 5 GHz 客户端（笔记本切到 5 GHz、或另开热点）确认这台手机
   在**别的 5 GHz AP** 上是否也慢。这一步能区分“手机射频”与“这个 AP”。
2. 若能进 AP 管理页，查该 AP 的 5 GHz 是否开了 WMM-UAPSD、Airtime
   Fairness 或省电策略；把手机 5 GHz 的 U-APSD 关掉再测。
3. ~~查 `usb-moded`/DBus 为何每 2.07 s 发 `mode_request`~~
   已完成：是板级 `samurai-usb-recover` 的误用，已改为自适应轮询
   （`samurai-platform` 6-r23）。
4. 固件归属：让 `linux-firmware-ath10k` 或板级包正式拥有
   `/lib/firmware/ath10k/WCN3990/`，消除无主文件。

## 6. 一个已确认的负面结果（避免重复排查）

AP 信标里声明了 WMM `u-APSD`，但手机 station dump **没有 `u-apsd` 行**，
说明并未协商启用。所以“U-APSD 服务期调度”在当前配置下不是成因；
除非以后发现 `u-apsd` 行出现，否则不要再往这个方向查。

## 7. 已撤回：`tx duration` 推出的“PHY 速率 6 Mbps”结论不成立

本节记录一次**错误推断及其证伪**，避免后来的人重复走这条弯路。

### 7.0 撤回原因

我曾用 `iw station dump` 的 `tx duration` 与 `tx bytes` 差分，得到
“5 GHz 只用 5.58 Mbps 发送”，并据此判定是 rate-control 选速崩溃。

**这个推断是错的。** 随后我在 2.4 GHz 上做同样的差分：

```text
2.4 GHz: delta_tx_bytes=5,756,222  delta_tx_duration=8,338,601 us
       => 同样的 5.52 Mbps
```

2.4 GHz 实测吞吐是 3.8-5.8 MB/s（约 30-46 Mbps），绝不可能以 5.52 Mbps
发送，却仍报出同一个数值。结论：**该固件版本的 `tx duration` 不是真实
空口占用时间**（很可能按最低基本速率或某个固定权重折算），
不能用它反推 PHY 速率。下面 7.1-7.3 保留作证据记录，但结论作废。

### 7.1 （作废）当时的差分数据

用 station dump 的 `tx duration` 与 `tx bytes` 差分（下载进行中采样）：

```text
delta_tx_bytes    = 4,587,948
delta_tx_duration = 6,572,869 us
implied PHY rate  = 5.58 Mbps
```

协商速率是 `866.7 MBit/s VHT-MCS9 80MHz`，实测只有 5.58 Mbps ——
正好是 802.11a 的最低档 6 Mbps。且同一时刻：

```text
tx retries: 0     (不增长)
tx failed : 69    (不增长)
```

即帧**不是重传失败**，而是以 6 Mbps **一次发送成功**。这是
rate-control（`minstrel_ht`）选错速率，不是链路质量或丢包。

### 7.2 吞吐对照（这一部分仍然有效）

| 频段 | 信道/带宽 | 协商速率 | 单流 | 4 路并行 | 效率 |
| --- | --- | --- | --- | --- | --- |
| 2.4 GHz | ch11 / 40 MHz | 300 Mbps | **3.8 MB/s** | **5.82 MB/s**（会扩展） | 15.5 % |
| 5 GHz | ch36 / 80 MHz | 866 Mbps | **0.33-0.61 MB/s** | **1.23 MB/s**（不扩展） | 1.1 % |

5 GHz 连续 6 次采样：`0.55 / 0.33 / 0.52 / 0.38 / 0.61 / 0.48 MB/s`。
上行（手机→PC）同为 `1.58 MB/s`，所以是双向的 PHY 速率问题。

### 7.3 已排除的新假设（这些对照本身有效）

| 假设 | 对照 | 结果 |
| --- | --- | --- |
| 空闲时发射机空转 | 空闲 10 s `tx duration` 只 +1271 us | 0.0 % 占空比 → 不是空转 |
| 功率过高（30 dBm 超规） | `iw set txpower fixed 2000` | 0.46-0.60 MB/s，无改善 |
| 锁高 MCS 可绕过 rc | `iw set bitrates vht-mcs-5 1:0-9 2:0-9` | 仍 5.58 Mbps |
| PHY 能力缺失 | `iw list` Band 2 显示 VHT MCS 0-9 双流 | 能力完整 → 是软件选速 |
| 发射功率上限 | AP 报 `Local Max TX Power For 80 MHz: 26.5 dBm` | 手机 30 dBm 超规，但不是成因 |

### 7.4 已排除的环境项

- PC 在同位置**看不到**该 AP 的 5 GHz BSS（只看到 2.4 GHz），且 PC→路由器
  2.4 GHz 为 0 % 丢包/3 ms → 不是路由器整体故障。
- 5 GHz 同频邻居 `USER_858061_5G`（ch36、-66 dBm）与 AP 强度相当，
  但 2.4 GHz 也有强邻居（`USER_858061` -46 dBm）却表现良好 → 干扰不是主因。
- 手机 AP 模式可用（`iw dev wlan0 set type __ap` 成功），
  但设备无 `hostapd`，无法用自制 AP 做独立验证。

### 7.5 修正后的定性

**这些是事实**（不受 7.1 撤回影响）：

```text
2.4 GHz: 3.8 MB/s 单流, 5.82 MB/s 4 路并行（会扩展）
5 GHz  : 0.33-0.61 MB/s 单流, 1.23 MB/s 4 路并行（不扩展）
5 GHz 连续 6 次: 0.55/0.33/0.52/0.38/0.61/0.48 MB/s
上行方向同为 1.58 MB/s
```

**速率控制不是根因**（以下都试过，吞吐都在 0.27-0.61 MB/s）：

| 尝试 | 结果 |
| --- | --- |
| `minstrel_vht_only=N` | 0.35 / 0.27 MB/s |
| `ieee80211_default_rc_algo=minstrel`（非 ht） | 0.49 / 0.29 MB/s |
| `iw set bitrates vht-mcs-5 1:0-9 2:0-9` | 仍无改善 |
| `iw set txpower fixed 2000` | 0.46-0.60 MB/s |

**当前定性**：5 GHz 实际吞吐只有协商速率的 ~1 %，且**多流不扩展**，
说明瓶颈在“每个 MPDU 的固定开销极大”（例如每帧都走一次昂贵的
速率/探测事务），而不是带宽或速率档位。2.4 GHz 同机同 AP 正常。
根因仍在 ath10k/固件层，未定位。

## 8. 测量陷阱与修正后的纯净对照（2026-11-20 03:50）

### 8.1 必须先排除的两个测量陷阱

**(a) AP 开了客户端隔离。** 手机 → PC（`192.168.0.104`）在**两个频段**上
都是 100% 丢包：

```text
2.4 GHz: phone -> router 0% loss/25.8 ms   | phone -> PC 100% loss
5 GHz  : phone -> router 0% loss           | phone -> PC 100% loss
ARP 表里 192.168.0.104 是 STALE 但确实存在
```

所以“手机 → PC 不通”是 AP 的 client isolation，**不是 WiFi 故障**。
之前所有基于“手机 ping PC”的对比都要作废，包括第 3 节里的 100% 丢包。

**(b) `push` 方向的总时长不是带宽。** 用 `scp`/`ssh` 传不同大小的数据：

```text
0 B    : 3.33 s
1 KB   : 5.77 s
1 KiB*1: 8.09 s
4 KB   : 6.22 s
16 KB  : 2.51 s
64 KB  : 7.65 s
256 KB : 2.38 s
```

耗时与数据量**完全无关**，是“建连/握手”的随机延迟。所以之前
“5G 只有 1.2 MB/s”这个数字也混入了固定成本，不能当纯带宽用。

### 8.2 纯净对照：TCP 建连时间（唯一不受隔离影响的指标）

方向 PC → 手机，每次一个 `ssh true`，10 次采样：

| 频段 | 10 次建连时间 | 结论 |
| --- | --- | --- |
| 2.4 GHz | 551 / 427 / 445 / 448 / 445 / 537 / 456 / 443 / 455 / 458 ms | **稳定在 427-551 ms** |
| 5 GHz | 10847 / 9364 / 4688 / 6476 / 5885 / 3879 / 486 / 794 / 3320 / 2335 ms | **随机 0.5-10.8 s** |

**这是本轮最干净、最有说服力的差异**：2.4 GHz 的建连延迟方差极小，
5 GHz 的建连延迟跨度 20 倍。这不是带宽，而是“某些帧要等数秒才送达”。

### 8.3 纯净对照：PC → 手机 ICMP

| 频段 | 丢包 | 最小 | 平均 | 最大 |
| --- | --- | --- | --- | --- |
| 2.4 GHz | **0 %** | 1 ms | **10 ms** | 47 ms |
| 5 GHz | **20 %** | 19 ms | **533 ms** | 933 ms |

### 8.4 5 GHz 的 RTT 无周期性

40 个包 @0.5 s 间隔，RTT 序列（ms）：

```text
450 302 1181 681 328 479 414 653 1057 557 889 775 986 486 882 872 1112
611 523 840 340 1002 1003 897 1053 707 207 548 73 921 1357 857 1205
705 205 4 809 309 421 974
```

**0% 丢包**（40/40 全收），min 3.6 ms、avg 692 ms、max 1357 ms。
没有固定周期，也没有“逐包递减” —— 每个包独立地随机等待。
这与“AP 缓存后批量下发”或“U-APSD”都不符（后者应有固定周期）。

### 8.5 修正后的定性

| 项 | 状态 |
| --- | --- |
| 2.4 GHz | **正常**：0% 丢包、10 ms、建连 427-551 ms 稳定 |
| 5 GHz 链路可达性 | 正常：能关联、能扫到、beacon loss 0、0-20% 丢包 |
| 5 GHz 时延 | **异常**：RTT 随机 4-1357 ms，建连 0.5-10.8 s |
| 5 GHz 吞吐 | **异常**：多流不扩展（1.23 MB/s，与单流相同） |
| 速率控制 | **不是原因**：minstrel_ht / minstrel / vht_only 三种配置都一样 |
| 发射功率 | **不是原因**：30 dBm 与 20 dBm 无差别 |

**当前定性**：5 GHz 存在**随机、非周期性的大幅时延**（不是带宽、不是速率档位、
不是丢包）。这类形态最符合“个别 MPDU 在空口重试到上限后才成功”，
但 `tx retries/failed` 计数不增长，说明重传发生在**固件内部**、
没有上报到 mac80211 统计。

## 9. 根因（已定位并已修复于 `samurai-platform` 6-r23）

### 9.1 `regulatory.db` 从来没被加载过

```text
[    0.499820] cfg80211: Loading compiled-in X.509 certificates for regulatory database
[    0.507939] faux_driver regulatory: Direct firmware load for regulatory.db failed with error -2
[    0.516325] cfg80211: failed to load regulatory.db
[   22.078148] wlan0: regulatory prevented using AP config, downgraded
```

没有 regdb，cfg80211 退回世界域，而世界域里 **整个 5 GHz 频段是
PASSIVE-SCAN**：

```text
$ iw reg get
phy#0
country 99: DFS-UNSET
	(2402 - 2472 @ 40), (N/A, 20), (N/A)
	(5140 - 5360 @ 80), (N/A, 30), (N/A), PASSIVE-SCAN     <- 5 GHz
	(5715 - 5860 @ 80), (N/A, 30), (N/A), PASSIVE-SCAN     <- 5 GHz
```

`PASSIVE-SCAN` 意味着：不能用 5 GHz 主动发射（不能开 AP、不能主动探测），
只能被动接收。这解释了全部现象：

| 现象 | 由 regdb 缺失解释 |
| --- | --- |
| `iw reg set CN` 无效、始终 `country 99` | 没有 regdb，任何国家码都映射不到 |
| hostapd 报 `5180[NO_IR]`、`Frequency 5180 not allowed for AP mode` | PASSIVE-SCAN 下 5 GHz 不允许发起 |
| `setup AP` 后 `regulatory prevented using AP config, downgraded` | 同上 |
| 5 GHz 关联后 RTT 随机 4-1357 ms、建连 0.5-10.8 s | 世界域下没有正确的 5 GHz 发射规则 |
| 5 GHz 多流不扩展 | 同上 |
| 2.4 GHz 完全正常 | 世界域里 2.4 GHz 不是 PASSIVE-SCAN |

### 9.2 为什么 regdb 缺失（可修复的私有层缺陷）

`samurai-wifi.sh` 把内核的 `firmware_class` 搜索路径重定向到
`/run/samurai-wifi/firmware`：

```text
$ cat /sys/module/firmware_class/parameters/path
/run/samurai-wifi/firmware
```

但它只拷贝了 `ath10k/`：

```sh
cp -a /lib/firmware/ath10k "$base/firmware/"
```

`regulatory.db` / `regulatory.db.p7s` 没有被拷进这个目录。
**但这不是 regdb 失败的真正原因**（见 9.3 的时序证据）：regdb 在 `0.50 s` 就被请求，那时 `/run` 虽已由
initramfs 挂载，但 `/run/samurai-wifi/firmware` 目录要等 `samurai-radio`（依赖 `local-fs.target`）启动后才创建，
远晚于 `0.50 s`。所以这个目录拷不拷都赶不上 regdb 的请求时机。

保留这处改动只为**一致性**：`firmware_class/path` 一旦指向该目录，之后内核请求的 firmware 都必须在那里找到；
补齐 regdb 可避免将来手动 `modprobe` 或重启 `samurai-radio` 时出现新的 ENOENT。它是正确的加固，但不是 5 GHz 修复。

### 9.3 修复（真正生效的只有落点 B）

**落点 A：把 regdb 拷进私有固件目录**（对 regdb 本身**无效**，仅为一致性加固）

`linux-port/packages/samurai-platform/usr_sbin_samurai-wifi`：

```sh
cp -a /lib/firmware/ath10k "$base/firmware/"
# firmware_class/path 指向这个目录，之后内核要的每个固件都必须在这里。
for reg in regulatory.db regulatory.db.p7s; do
    test -f "/lib/firmware/$reg" || continue
    cp -a "/lib/firmware/$reg" "$base/firmware/$reg"
done
```

已部署到设备（`sha256 3f065cfc…`），`pkgrel` 提到 23，`check-sources.py`
23 配方 / 164 个 SHA-512 全部通过。

**落点 B：把 regdb 打进 initramfs**（覆盖“0.50 s 时 rootfs 还不存在”）

这才是真正生效的那一步。时序证据：

```text
[0.499820] cfg80211: Loading compiled-in X.509 certificates ...   <- 请求 regdb
[0.507939] faux_driver regulatory: ... failed with error -2        <- ENOENT
[0.661203] Run /init as init process                               <- 还在 initramfs
[1.770639] F2FS-fs (sda16): f2fs_recover_fsync_data                <- 根才被挂载
```

regdb 在挂载根之前就被请求，所以放在 `/lib/firmware` 或
`/run/samurai-wifi/firmware` 都没用，**必须在 initramfs 里**。

新增配方 `linux-port/packages/samurai-platform/50-samurai-regdb.files`，
由 APKBUILD 安装到 `/etc/mkinitfs/files-extra/`：

```text
/lib/firmware/regulatory.db
/lib/firmware/regulatory.db.p7s
```

（格式与 `/usr/share/mkinitfs/files-extra/00-initramfs-extra-base.files`
一致：每行一个绝对路径。）已部署到设备，`check-sources.py` 升至
165 项并全部通过。

### 9.3.1 为什么“重新生成 initramfs”这条路在本机不适用

本来打算跑 `mkinitfs` 重新生成 initramfs。实测发现**这个设备的内核和
initramfs 都不在 `boot` 分区**：

```text
$ blkid /dev/disk/by-partlabel/boot      # sde11, 98304 x 512B = 48 MB
/dev/sde11: PARTLABEL="boot" PARTUUID="8e1aad77-..."
$ mount -t vfat -o ro /dev/disk/by-partlabel/boot /tmp/x
FAT-fs (sde11): invalid media value (0x00)
FAT-fs (sde11): Can't find a valid FAT filesystem
$ cat /proc/cmdline
console=tty0 loglevel=7 ... panic=15 clk_ignore_unused ...      # 没有 root=
```

三点合起来说明：内核 cmdline 是**编译进内核/UEFI 的**，rootfs 由
initramfs 按 `deviceinfo` 自行查找（`find_boot_partition` +
`f2fs` 分支），而内核镜像与 initramfs **都嵌在 UEFI 固件里**
（这正是本项目的设计：EDK2 + 外部匹配内核）。

因此 `mkinitfs` 的 `boot-deploy` 目标（往 `boot` 分区写 vmlinuz /
initramfs）在这里**没有落点**。要让 regdb 进 initramfs，正确做法是
**重新构建 UEFI 里的 initramfs 段**，而不是跑 mkinitfs。

当前手机的 Wi-Fi/NCM 是唯一远程通道，写 UEFI 的风险高于写 boot，
所以本会话**只做静态验证，没有执行任何固件写入**。

进一步实测把这条链钉死了：

```text
[0.001887] VFS: Finished mounting rootfs on nullfs      # 内核初始 ramfs
[1.676469]  sda: sda1 ... sda16                         # UFS 枚举完成
[1.772580] F2FS-fs (sda16): Mounted with checkpoint ... # 由内核直接挂载
$ ls /etc/initrd-release
no /etc/initrd-release                                  # 没有跑的 initramfs
```

即 **0.0019 s 到 1.77 s 之间没有任何 initramfs 用户空间在执行**，
f2fs 根是内核自己按内置的 root 参数挂上的。这意味着：

- 没有可改写的 initramfs cpio；
- `0.50 s` 请求 regdb 时，`/lib/firmware/regulatory.db` 必然读不到
  （根还没挂）；
- 唯一能让 regdb 在那之前可用的办法，是**把 regdb 编进内核内置
  initramfs**（`CONFIG_INITRAMFS_SOURCE`）或让 EDK2 在启动内核前
  预加载它。

仓库里也有对应的既有结论：`finalize-plasma-rootfs.py` 注释写着
“this device is kernel=none: the boot chain mounts the F2FS rootfs
directly and there is no initramfs in use”，并对 mkinitfs trigger
设了 `KERNEL_INSTALL_BYPASS=1`。

已完成的静态验证：

| 检查 | 结果 |
| --- | --- |
| 配方格式与 `00-initramfs-extra-base.files` 一致 | ✅ |
| 源文件 `/lib/firmware/regulatory.db(.p7s)` 都在设备上 | ✅ |
| 已安装到 `/etc/mkinitfs/files-extra/50-samurai-regdb.files` | ✅ |
| `mkinitfs --version` = 2.11.0，支持 `-no-bootdeploy` | ✅ |
| `mkinitfs -d /tmp -no-bootdeploy` 能跑 | ⚠️ 报 “only one kernel release/flavor is supported, found: []” |

最后一条说明：`/lib/modules` 下有 **两个** flavor
（`…-v731` 与 `…-v731-usbwake-otg`），mkinitfs 无法自动判定该用哪个。
执行前必须先清理多余的那个（或确认它与 boot 分区里的 Image 匹配），
否则生成的 initramfs 可能配错内核。

### 9.3.2 为什么 `mkinitfs` 说 `found: []`（已查清）

即使把多余 flavor 移走，仍然报 `found: []`。真正原因与 flavor 数量无关：

```text
$ apk info -W /lib/modules/7.3.1-rmx1931-samurai-v731-usbwake-otg/modules.dep
ERROR: ...: Could not find owner package
$ apk info -W /lib/modules/7.3.1-rmx1931-samurai-v731/modules.dep
ERROR: ...: Could not find owner package
```

两个内核模块目录**都不被任何 apk 包拥有**。mkinitfs 通过 apk 数据库枚举
`linux-*` 内核包来得到 flavor 列表，而本机是“external kernel”
（`deviceinfo_flash_method="none"`，内核由 boot 分区提供、不进 rootfs），
所以它枚举到的是空集。

这与本文件前面记录的 `powerdevilrc` 无主、`ath10k` 固件无主是同一类缺陷：
**文件在盘上，但 apk 数据库不认识它们**。它不影响运行，但让所有依赖
apk 元数据的工具（mkinitfs、`apk fix`、升级接管）都看不见这些文件。

`KERNEL_INSTALL_BYPASS=1` 不是解药 —— 它直接
`Skipping mkinitfs`，什么也不生成（已实测）。

### 9.3.3 可执行的落地路线

| 路线 | 做法 | 代价 |
| --- | --- | --- |
| A. 把 regdb 编进内核内置 initramfs | 设 `CONFIG_INITRAMFS_SOURCE` 指向一个只含 regdb 的 cpio，重新编译内核 | 需要重编内核；内核是内嵌在 UEFI 的，还要重新打包并刷 UEFI |
| B. 把 regdb 放进 UEFI 的 initramfs 段 | 找到本项目构建 UEFI 内嵌 initramfs 的步骤，追加两个文件后重新打包 | 同 A，但不必改内核配置 |
| C. 打包 `linux-firmware-ath10k` + 让 apk 拥有模块目录 | 修掉“无主文件”，但**对 regdb 时序问题无效**（regdb 在挂载根之前就要） | 低，但不是 5 GHz 的修复 |

**A/B 都需要重新构建 UEFI 固件**，属于本项目的 UEFI 构建链路，
不是 rootfs 层能单独完成的。

路线 C 仍然值得做（它与本文件记录的其他“无主文件”缺陷同类），
但不要把它误当成 5 GHz 的修复。

### 9.4 regdb 假设的独立验证（不写 boot 也做到了）

有一条证据能**排除“签名失败”这个替代解释**，从而确认 `-2` 就是
`ENOENT`（时序问题），而不是证书不匹配：

```text
[0.499820] cfg80211: Loading compiled-in X.509 certificates for regulatory database
[0.503243] Loaded X.509 cert 'sforshee: 00b28ddf47aef9cea7'
[0.507939] faux_driver regulatory: Direct firmware load for regulatory.db failed with error -2
```

`sforshee: 00b28ddf47aef9cea7` 就是 wireless-regdb 的官方签名证书，**已经
成功载入内核 keyring**。也就是说签名链是好的；下一行紧跟着 `-2`
只可能是“文件读不到”。这与“0.50 s 时 f2fs 根尚未挂载”完全吻合。

另外确认配方本身有效：

```text
$ cat /etc/mkinitfs/files-extra/*.files | grep -v '^#'
/lib/firmware/regulatory.db
/lib/firmware/regulatory.db.p7s
$ for f in ...; do test -f "$f" && echo "OK  $f"; done
OK  /lib/firmware/regulatory.db
OK  /lib/firmware/regulatory.db.p7s
```

所以“补丁写对了、只差重新生成 initramfs”是**有证据支持的**，
而不是猜测。

### 9.5 结论

| 项 | 结论 | 证据 |
| --- | --- | --- |
| regdb 未加载 | 已确认 | `failed to load regulatory.db` + `error -2` |
| 失败原因是时序（非签名） | 已确认 | 签名证书已在 keyring，紧跟 `-2` |
| 世界域导致 5 GHz 受限 | 已确认 | `country 99` + 5 GHz 全部 `no IR` |
| 配方能把 regdb 进 initramfs | 已确认（静态） | files-extra 被读取、两个文件都在 |
| 生成新 initramfs | **未执行** | mkinitfs 报 `found: []`（内核模块无主） |
| 5 GHz 恢复 | **未验证** | 需重启 |

一句话：**根因和补丁都确定了，卡在“如何在不写坏 boot 的前提下生成
新 initramfs”这一执行步骤上。**

### 9.4 验证状态（诚实标注）

| 项 | 状态 |
| --- | --- |
| 脚本已修、已部署、门禁通过 | ✅ 已证明 |
| `/run/samurai-wifi/firmware/regulatory.db` 存在 | ✅ 已证明 |
| regdb 真正被 cfg80211 加载、`country` 变成 CN/US | ⏳ **未证明**（只能重启验证；重启会断开唯一远程通道） |
| 5 GHz 延迟/吞吐因此恢复 | ⏳ 未证明（同上） |

只有重启并看到 `dmesg` 里 **不再有** `failed to load regulatory.db`、
且 `iw reg get` 显示真实国家码，才能宣布 5 GHz 修复。在那之前，
`HARDWARE-STATUS.md` 里 5 GHz 仍记为**未修复**。

### 9.5 下一步

1. 下一次计划内重启后，第一件事检查：
   ```sh
   dmesg | grep -i regulatory     # 不应再有 "failed to load"
   iw reg get                     # 应是 country CN/US，5 GHz 不是 PASSIVE-SCAN
   ```
2. 若仍失败，说明启动早期 `firmware_class/path` 已经被改到
   `/run/samurai-wifi/firmware` 而 `prepare` 还没拷贝 → 需要把 regdb
   预置到镜像里的 `/run/samurai-wifi/firmware/`（或让 `prepare` 在
   `echo "$base/firmware" > .../path` 之前就完成拷贝，当前顺序已是如此）。
3. 验证通过后再重测 5 GHz 吞吐与 RTT，对比本文件第 8 节的基线。

下一步（按信息量）：

1. 同内核接另一台 5 GHz AP（或换信道 149/157 试，需 AP 支持），
   确认是否所有 5 GHz 都这样；若只有 ch36 这样，是同频环境触发 rc 保守退化。
2. 查 `ath10k` 的 `ath10k_mac_get_rate_flags` / `ath10k_htt_tx` 是否
   把 80 MHz 的 VHT 速率错误标成 `ATH10K_HW_RATE_CCK/OFDM`，
   使 minstrel 只看到 6 Mbps 档。
3. 若确认是 rc 层，可用 `iw` 之外的标准方式（`mac80211` rc 参数）验证；
   修复需要重编内核，超出“最小适配”范围，应先作为已知缺陷记录。

## 10. 2026-11-20 晚：内核落地后的实测与更正

### 10.1 旧结论更正：本机**确实**有 initramfs

§9.3.1 断言“0.0019 s 到 1.77 s 之间没有任何 initramfs 用户空间在执行，
f2fs 根是内核自己挂上的”，并据此说 `mkinitfs` 没有落点。**这是错的**，
会被这次重启的日志直接推翻：

```text
[0.661203] Run /init as init process
[1.883349] [rootfs] verified /dev/sda16; switching to F2FS postmarketOS
```

`/init` 来自内嵌 initramfs（成员 `usr/sbin/samurai-rootfs`），它校验
`/dev/sda16` 后 `switch_root`。GRUB 传给内核的 cmdline 里其实没有
`root=`（设备 `cat /proc/cmdline` 只有 console/loglevel/panic/
clk_ignore_unused 等），rootfs 由这段 `/init` 自己选盘挂载。

于是“regdb 必须在挂根之前可用”依然成立，落点也只有一个：**内嵌
initramfs**（`CONFIG_INITRAMFS_SOURCE`）。本文件 §9.3.2 关于
`firmware_class/path` 的部分仍有效。

### 10.2 regdb 已真正加载（实机证据）

新 Image 里内嵌了原始的 initramfs 树 + `regulatory.db` /
`regulatory.db.p7s`（398 个成员）。重启后：

```text
$ iw reg get
global
country CN: DFS-FCC
$ iw phy phy0 reg get
phy#0
country US: DFS-FCC          <- 之前是 country 99, 全段 PASSIVE-SCAN
```

5 GHz 频道不再是 `PASSIVE-SCAN`，`5180 MHz [36]` 有了实际发射规则。
**这是本次真正修好的一层。**

### 10.3 为什么新 Image 险些装不进 64 MiB 的 `logdump`

`/Image` 由 GRUB 从 `logdump`（64 MiB FAT32）读取，分区只剩约 6.3 MB
余量。第一次重建得到 66.6 MB，装不下，原因有两个，都是**构建工具链**
而不是板级改动：

| 现象 | 根因 | 处理 |
| --- | --- | --- |
| `Image` 66.6 MB | `CONFIG_INITRAMFS_SOURCE` 指向 `.cpio` 时内核按 **不压缩** 嵌入（29.7 MB） | 改指 `.cpio.gz`（`usr/Makefile` 对 `.cpio.*` 用 `compress-y := copy`，15 MB 原样嵌入） |
| 仍超出 7.3 MB | 缺 `CONFIG_RELR`：Ubuntu 24.04 的 binutils 2.42 不支持 `-z pack-relative-relocs`，`TOOLS_SUPPORT_RELR` 探测失败被 olddefconfig 静默关掉，于是 `.rela.dyn` 有 7.7 MB | 用 `ld.lld` 链接，`.rela.dyn` 7.7 MB → `.relr.dyn` 0.14 MB，`Image` 降到 **58.67 MB** |

另外 `build-kernel-regdb.sh` 原来把 `CONFIG_LOCALVERSION` 改成
`-usbwake-otg`，会丢掉 `-rmx1931-samurai-v731`，使 772 个已装模块的
vermagic 全部不匹配；已改为只用 `make LOCALVERSION=-usbwake-otg` 追加。

刷入只改 `logdump` 的**内容**，不动分区表（GRUB 用 `search_fs_file`
找 `/Image` 所在的卷，不依赖卷标或 GUID），所以 UEFI 侧无需重编
EDK2，也没有 boot 分区风险。已回读校验：`logdump` 的 SHA-256 与构建
产物逐字节一致。

### 10.4 power save 是丢包主因（已修，标准接口）

同一个 boot、同一 AP、`-62 dBm`，60 包 `ping -i 0.2`：

| power save | 丢包 | 平均 RTT |
| --- | --- | --- |
| on（默认） | 0-85 % | 900-2800 ms |
| off | 0-3 % | 585-907 ms |

`iw dev wlan0 set power_save off` 只改当前状态，重启会回到 NM 默认。
已改为 NetworkManager 的**标准**连接属性
`wifi.powersave=2`（与 `nmcli con mod <con> wifi.powersave 2` 写入的是
同一个键），落在
[`etc_NetworkManager_conf.d_20-samurai-wlan.conf`](../packages/samurai-platform/etc_NetworkManager_conf.d_20-samurai-wlan.conf)，
`samurai-platform` 6-r24。已实机验证：`systemctl restart
NetworkManager` 后 `iw dev wlan0 get power_save` 仍为 `off`。

### 10.5 仍未闭环：每包 +200 ms 的 RTT

power save 关掉后丢包基本消失，但 RTT 还是几百毫秒，且相邻包常常
整百毫秒递增（649 → 611 → 744 → 543 → 981 → 1144 …）。逐包加时间戳
确认不是 `ping` 的假象（真实间隔 0.28-0.78 s）。

#### 2.4 GHz vs 5 GHz 同 AP 对照（已做，结论明确）

把连接临时 pin 到 2.4 GHz（`nmcli con mod TP-LINK_156D
802-11-wireless.band bg`），同一 AP、同一手机、同一 boot：

| 频段 | 信道 | 信号 | 丢包 | min / avg / max |
| --- | --- | --- | --- | --- |
| 2.4 GHz | ch11 | -40 dBm | 0 % | 0.9 / **4.9** / 35.7 ms |
| 5 GHz | ch36 | -62~-71 dBm | 0 % | 1.0 / **257-440** / 1371 ms |

2.4 GHz 完全正常，所以**不是本机协议栈整体慢**；只有 5 GHz 路径
异常。这同时排除了“Phone 的 mac80211/ath10k 队列普遍积压”这一假设。

`power save` 关掉后丢包从 0-85 % 降到 **0 %**（连续 5 轮×30 包，共
150 包无丢失，`beacon loss 0`、`tx failed 4`），平均 RTT 也从早期的
884-1140 ms 降到 **257-440 ms**，但最小 RTT 仍是 1.0-1.5 ms 而最大
到 1.4 s，说明仍有偶发的长停顿。RTT 仍是几百毫秒
且逐包呈约 200 ms 的步进。它还剩下的候选只有两个：AP 的 5 GHz 侧
（本机 Windows AX210 完全扫不到该 AP 的 5 GHz BSS，值得作为重点）
，或 ath10k 在 5 GHz 的聚合/调度路径。下一步建议换一台 5 GHz AP 复测，
这样无需改本机任何代码就能判定。

### 10.6 这次内核的新 shakedown 项（与 5G 无关）

新 Image 启动时出现两条时钟 WARN，`taint=512`（`[W]=WARN`），而旧
Image 的 boot 是 0 条 WARN：

```text
dsi0_phy_pll_out_dsiclk already disabled   (drivers/clk/clk.c:1257)
dsi0_phy_pll_out_dsiclk already unprepared (drivers/clk/clk.c:1116)
```

都在 `of_clk_add_hw_provider -> clk_core_reparent_orphans_nolock` 的
DISPCC 时钟 reparent 路径里。显示、背光、DPMS 实测正常，`systemctl
--failed` 为 0；但按项目口径 `taint=0` 是验收条件，所以记为**新内核
待修项**，不能宣称“新内核已验证通过”。

根因（静态定位，已在 7.3.1 源码里逐行确认）：

```text
of_clk_add_hw_provider()
  clk_core_reparent_orphans_nolock()
    parent = __clk_init_parent(orphan)      # for DSI PHY clocks = mux index 0
    __clk_set_parent_before(orphan, parent)
      old_parent = core->parent             # already == parent (preset)
      core->prepare_count++ via clk_core_prepare_enable(parent)
    __clk_set_parent_after(orphan, parent, old_parent)
      if (core->prepare_count) {
          clk_core_disable_lock(core);
          clk_core_disable_unprepare(old_parent);   # same node as parent
      }
```

`__clk_set_parent_after()` 在 `old_parent == parent` 时会对**同一个父
时钟**先减一次引用再立刻减第二次，于是出现 `already disabled` /
`already unprepared`。上游 master 仍是同一写法，所以这不是我们独有的
改动，而是 7.3.1 里可以被任何“孤儿时钟 + 单父 mux”触发的问题。

最小的上游式修法是让 after 阶段跳过与自己相同的父节点：

```c
if (core->prepare_count) {
	clk_core_disable_lock(core);
	if (old_parent != parent)
		clk_core_disable_unprepare(old_parent);
}
```

按项目“优先上游、不叠加私有内核补丁”的口径，本轮**没有**把它打进
镜像，只记录为待上游化项；这也意味着新内核尚不能称 `taint=0`。
