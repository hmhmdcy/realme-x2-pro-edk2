# NFC / NCI standard path

Updated: 2026-11-09.

The RMX1931 NFC controller is already represented by the mainline
`nxp,nxp-nci-i2c` binding and the in-tree `nxp-nci_i2c` driver. The OS
DTB node is:

```text
/soc@0/.../i2c@.../nfc@28
```

with the standard `interrupts`, `enable-gpios`, `firmware-gpios` and
legacy pinctrl properties. No vendor ioctl, Android NFC HAL or private
character device is needed.

## User-space baseline

The standard user-space owner is Alpine's `neard` package, not a board
driver. The audited recipe is:

| Item | Value |
| --- | --- |
| Alpine aports commit | `bd6dd5c256ded7726539c28a7dcd984237d82006` |
| `community/neard/APKBUILD` SHA-256 | `bd8c77a5bd87d6b1ec5addf79516ecb9cf08f6e09e5d5082827a6c4e2f9614af` |
| `community/neard/neard.initd` SHA-256 | `efee90c44b86fe93a25efb4a978cc71faba858d11fd340a83a03b57d64ed2755` |
| upstream release | `neard 0.20` |
| license | `GPL-2.0-only` |
| service dependency | `dbus`; OpenRC `after coldplug` |

The package's standard service is `/etc/init.d/neard`; the adapter is
exposed on the system bus as `org.neard`, with the first adapter normally
at `/org/neard/nfc0`. Standard methods include `GetProperties`,
`SetProperty`, `StartPollLoop` and `StopPollLoop`; `TagFound` is the
standard signal used to prove that a physical tag was seen.

## Board boundary

`samurai-platform` only adds `neard-openrc` to the package dependency and
puts the upstream `neard` service in the default OpenRC runlevel. It does
not start or restart a live daemon from the package transaction, and it
does not add a private NFC service, ioctl, netlink client or Android HAL
shim.

The standard neard configuration is left upstream-owned. A future power
policy may disable `DefaultPowered` or add a settings toggle, but that is
separate from controller adaptation and must be tested with the real
adapter.

## Installed runtime result

2026-11-09 已在手机上完成安装和普通重启验收：

- `neard-openrc 0.20-r0` 安装后只提供 `/etc/init.d/neard`，不会自动拉下
  守护进程本体；必须同时安装社区仓库的 `neard 0.20-r0`；
- 从 `dl-cdn.alpinelinux.org/alpine/edge/community/aarch64/neard-0.20-r0.apk`
  下载并由现有 Alpine 公钥验证，APK SHA-256
  `027df5f8637a1fd50f34abba456b9c96ec838af53d4f09cb8d7bf16168487069`；
- `samurai-platform 5-r22` 从本地签名包安装，`neard` 进入默认 runlevel；
- 普通重启 boot ID `3331ca80-078d-4dda-935a-902d271cbea1`，`neard`
  自动启动，`nfc0` 存在；
- 正确的属性 API 是 `org.freedesktop.DBus.Properties.GetAll/Set`，
  不是不存在的 `org.neard.Adapter.GetProperties`；
- `Powered` 可开/关，`StartPollLoop`/`StopPollLoop` 可启停并清理；
- 无实体标签，`tag_seen=false`，不声称 TagFound 或读卡；
- `--bluetooth-host` 777 模块完整 runtime gate 同时通过，`taint=0`。

一次前台 NCM 探针出现 `Connection reset`，同一时刻 Wi‑Fi SSH 仍正常；
随后 NCM/Wi‑Fi 都自行恢复，后台 NCM 探针完整通过，不能把它写成已解决
的 NFC 电源根因。

## Deployment order

When the handset is online:

1. Confirm the Alpine community repository can resolve `neard-openrc`
   and install both `neard-openrc` and the `neard` daemon package.
2. Verify `/usr/libexec/nfc/neard` exists before treating the service as
   deployable.
3. Add the candidate signer to `/etc/apk/keys/` only if it is not already
   trusted, then install `samurai-platform-5-r22.apk` with
   `--no-network` so the package transaction cannot silently replace
   unrelated repository packages.
4. Reboot or start `neard` explicitly, then run `test-nfc-neard.py`.

The package install hook only updates the default runlevel. It deliberately
does not start, stop or restart a live `neard` instance; the runtime probe
does that explicitly so the service boundary remains observable.

## Verification

Run the read-only/D-Bus probe on the handset:

```sh
ssh root@192.168.0.114 \
  'python3 - --watch-seconds 8' \
  < linux-port/scripts/test-nfc-neard.py
```

Without a physical tag the probe must report `nfc0`, the service status,
adapter properties and a clean `StopPollLoop`; it must not claim tag I/O.
With a tag attached, use:

```sh
python3 linux-port/scripts/test-nfc-neard.py --watch-seconds 15 --expect-tag
```

That path passes only when the standard `TagFound` signal appears. It
does not validate eSE, card emulation, secure-element provisioning or
Android NFC applications. The NFC controller binding alone is not a
read-card acceptance.
