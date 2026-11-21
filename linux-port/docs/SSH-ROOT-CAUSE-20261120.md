# SSH 连接失败：根因分层（2026-11-20）

设备：RMX1931 `samurai`，内核 `7.3.1-rmx1931-samurai-v731-usbwake-otg`，
镜像 `postMarketOS v26.06`（Alpine v3.24 基线）。

## 一、结论：sshd 一直是好的，坏在“地址 + 主机代理”两层

| # | 现象 | 根因 | 状态 |
|---|---|---|---|
| 1 | `192.168.0.106:22` 连不上 | 手机实际拿到的是 **`192.168.0.105`**（DHCP 动态地址），`.106` 是历史记录 | 已证实 |
| 2 | `Test-NetConnection 172.16.42.1 -Port 22` 报 True，`ssh` 却 0 字节断开 | Clash Verge (mihomo) 的 TUN + fake-IP 把目标劫持到 `198.18.0.1` | 已证实 |
| 3 | NCM `169.254.42.1` 无 ARP 应答 | 僵尸 ARP 条目 + 主机侧没有 `169.254` 对端地址绑定 | 已证实 |
| 4 | 镜像里的 sshd | **正常**：chroot 内可发 banner、可做 PAM 交互 | 已证实 |

## 二、证据

### 2.1 真实地址是 .105

```
$ ip -o -4 addr show          # 实机
2: usb0  inet 169.254.42.1/16 scope global usb0
2: usb0  inet 172.16.42.1/24  scope global usb0
4: wlan0 inet 192.168.0.105/24 brd 192.168.0.255 scope global dynamic
```

`192.168.0.105` 上 SSH 立即可用：

```
$ ssh -i ~/.ssh/samurai_id_ed25519 user@192.168.0.105 'hostname; uname -r'
samurai
7.3.1-rmx1931-samurai-v731-usbwake-otg
```

> `.106` 来自早前一次 DHCP 租约，写进了多个脚本默认值。
> **不要再把 `.106` 当作事实**；先扫一遍再用：

```powershell
python linux-port/scripts/ssh-path-diag.py --scan 192.168.0.104
```

### 2.2 fake-IP 劫持

原始 socket 连 `172.16.42.1:22`：

```
connect OK, peer=('172.16.42.1', 22)  local=('198.18.0.1', 63363)
recv: b''
```

`local` 落在 mihomo 的 `fake-ip-range: 198.18.0.1/16` 里，说明报文没有
经过物理网卡。配置（`AppData/Roaming/io.github.clash-verge-rev.clash-verge-rev/clash-verge.yaml`）：

```yaml
tun:
  enable: true
  auto-route: true
  route-exclude-address: []
dns:
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16
```

路由：

```
0.0.0.0/0 -> 198.18.0.2 if 198.18.0.1  metric 0    <- TUN 抢走默认路由
0.0.0.0/0 -> 192.168.0.1 if 192.168.0.104 metric 30
```

规则里虽有 `IP-CIDR,172.16.0.0/12,DIRECT,no-resolve`，但没有进
`route-exclude-address`，报文仍先落到 TUN；gvisor 栈对不可达目标直接
关闭连接 → 表现为“TCP 成功、0 字节”。

**这不是 sshd 的问题。** 关掉 TUN 后同一目标立刻变成 `timed out`
（真实路径），结论完全不同。

建议（任一）：

- Clash Verge → 设置 → TUN：`route-exclude-address` 加
  `172.16.0.0/12`、`192.168.0.0/16`、`169.254.0.0/16`；
- 或调试 SSH 时临时关 TUN；
- 或改用 NCM 并显式绑定源地址（见下）。

### 2.3 NCM 的 169.254 侧

实机 `usb0` 同时持有 `169.254.42.1/16` 与 `172.16.42.1/24`，
`samurai-usb-network`、`usb-signaller`、`unudhcpd@usb0` 全部 `active`，
carrier=1、operstate=up —— 设备侧配置是对的。

主机侧 `以太网 10`（`UsbNcm Host Device #5`）却只有 APIPA
`169.254.115.197/16`，ARP 表里没有 `169.254.42.1`。主机需要自己发
DHCP 或静态设地址；Windows 的 APIPA 不会主动去探测对端。

排查顺序（主机侧先，别先怀疑 sshd）：

```powershell
Get-NetIPAddress -InterfaceIndex 6
arp -a | Select-String 169.254
python linux-port/scripts/ssh-path-diag.py 169.254.42.1 22 --bind 169.254.115.197
```

## 三、镜像 sshd 的实测（排除镜像因素）

把交付镜像整树 `cp -a` 到 WSL 本地 ext4（**不能**用 tar，会丢空目录），
chroot 内跑：

```
ssh-keygen -A                       # 首次开机由 sshdgenkeys.service 做
sshd.pam -t                         # rc=0
sshd.pam -D -p 2222 -e              # 起服务
ssh -p 2222 user@127.0.0.1 true
  -> Warning: Permanently added ... (ED25519)
  -> Postponed keyboard-interactive for user ...
```

banner、KEX、host key、PAM 全部走通。所以设备上“0 字节断开”
**不可能是 sshd 拒绝**，只能是没收到连接。

镜像状态（已核对）：

| 项 | 值 |
|---|---|
| `/usr/lib/ssh/sshd-auth(.pam)`、`sshd-session(.pam)` | 存在，`0755 root:root` |
| `/var/empty` | 存在，`0555 root:root` |
| `/etc/ssh/sshd_config.d/99-samurai.conf` | 交付镜像中**不存在** |
| host key | 不预置，首启生成（避免固定主机身份） |
| `/var/log/journal` | 存在 |

> 早前 `Missing privilege separation directory: /var/empty` 是抽取树
> 用 tar 丢了空目录造成的**假阳性**。

## 四、可复用脚本

| 脚本 | 用途 |
|---|---|
| `linux-port/scripts/ssh-path-diag.py` | 打印 socket 的 `local` 地址，判定是否被 fake-IP 劫持；`--scan` 扫同一网段里真正开着 22 端口的主机 |
| `linux-port/scripts/_wsl-samurai/extract-image-tree.sh` | 从 `.simg` 抽整树，保留空目录 |
| `linux-port/scripts/_wsl-samurai/repro-sshd-in-chroot.sh` | 在本地树里验证镜像 sshd，并在结束后删除临时 host key |

## 五、判定口诀

1. 先看 `local` 地址是不是 `198.18.x.x` —— 是就走代理，结论作废；
2. 再扫网段找真实 IP —— 不假设旧地址；
3. 最后才看 sshd —— 只有拿到 banner 之后的问题才归 sshd。