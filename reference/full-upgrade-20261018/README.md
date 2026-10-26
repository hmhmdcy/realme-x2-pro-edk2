# 2026-10-18：现有软件源全量升级完成

用户要求full upgrade。通过USB、原SSH主机密钥及260同boot守卫检查，刷新现有四个在线仓库及两个本地适配仓库后，实际执行原生 `apk upgrade` 成功，退出码0。55个已有包升级、3个新增依赖、0删除，已安装包数从958变为961。

## 事务与验证

- 再次 `apk version -l '<'` 没有剩余新版；`apk upgrade --simulate` 无待执行事务。
- 将world中stevia-schemas的旧包校验和约束改成无版本限定的 `stevia-schemas`，是本轮唯一world改动。Stevia和schemas均为0.57.0-r3，UIM及其GTK3/Anthy配套为1.9.9-r0，并新增uim-gtk4。
- 另外新增postmarketos-base-ui-udev62-r0和postmarketos-base-ui-gnome-mobile-udev2-r0。
- Phoc保持0.57.0-r1，现有正规源仍未提供0.58；没有启用nightly、添加密钥或引入nightly包。本轮不构成键盘搜索兼容问题修复。
- 相机、GNSS配套包版本约束保持。Phoc、ModemManager、libcamera和本机修复的libvulkan_freedreno.so前后SHA256一致。
- 同260启动，未重启/刷写。mkinitfs触发器正常识别缺少其管理用deviceinfo而跳过生成；/boot为空，本轮没有升级内核包。
- 原Phosh/Phoc进程及USB SSH保持，Wi-Fi仍connected；桌面与GNSS/SSC服务处于started，内核taint0。仅是运行及连接检查，没有将其扩展成完整硬件或冷启动验收。
- 新 `/usr/bin/phosh-osk-stevia` 的动态依赖全部解析成功。现有键盘PID3802继续持有旧可执行文件，D-Bus仍可查询；重登或重启后加载新键盘及会话库。手机检查时锁屏，未绕过锁屏或强制结束桌面。
- 没有待合并的.apk-new。`apk audit --system`仅保留升级前已有的libvulkan_freedreno.so修改项，内容哈希未变。
- 发行版post-upgrade钩子将wpa_supplicant和routewrangler加入default；二者未启动，保持当前NetworkManager通信。未手工启动或撤销发行版钩子的配置。

## 回退与范围

升级前保存系统配置与APK数据库、55包所拥有的833个现存文件/目录/链接及独立内容、权限、所有者和xattr清单。配置和文件快照均在手机与PC各留一份，导出SHA256一致。另外保存33个旧APK，其中25个通过当前信任密钥验签；缺失或旧签名不受信任的包由已安装文件快照覆盖。未将这些历史包作为不验签安装输入。

私人PC路径 `E:/edk2-samurai-out/full-upgrade-20261018`；手机 `/var/lib/samurai/full-upgrade-20261018`（0700）。这是本轮配置/文件回退材料，不是新制作的完整userdata镜像，也没有声称已实测完整回退。升级worker已退出，勿重放launch或worker脚本。

最初备份准备因缺旧缓存、旧签名不在当前信任库及APK3脚本归档文件名差异停止，均发生于实际安装前；完善文件快照和归档检查后才启动唯一一次真实升级。完整过程与失败收据只保存在私人目录。

## 实际升级清单

| 包 | 升级前 | 升级后 |
| --- | --- | --- |
| avahi | 0.9_rc5-r0 | 0.9_rc5-r1 |
| avahi-glib | 0.9_rc5-r0 | 0.9_rc5-r1 |
| avahi-libs | 0.9_rc5-r0 | 0.9_rc5-r1 |
| avahi-openrc | 0.9_rc5-r0 | 0.9_rc5-r1 |
| blake3-libs | 1.8.7-r0 | 1.8.7-r1 |
| bubblewrap | 0.13.0-r0 | 0.13.1-r0 |
| curl | 8.22.0-r0 | 8.23.0-r0 |
| libarchive | 3.8.9-r0 | 3.8.10-r0 |
| libcap2 | 2.78-r0 | 2.78-r1 |
| libcurl | 8.22.0-r0 | 8.23.0-r0 |
| libedit | 20260508.3.1-r1 | 20260512.3.1-r0 |
| libheif | 1.23.4-r1 | 1.23.6-r0 |
| libheif-aom | 1.23.4-r1 | 1.23.6-r0 |
| libheif-dav1d | 1.23.4-r1 | 1.23.6-r0 |
| libheif-ffmpeg | 1.23.4-r1 | 1.23.6-r0 |
| libheif-jpeg | 1.23.4-r1 | 1.23.6-r0 |
| libheif-libde265 | 1.23.4-r1 | 1.23.6-r0 |
| libheif-openh264 | 1.23.4-r1 | 1.23.6-r0 |
| libheif-openjpeg | 1.23.4-r1 | 1.23.6-r0 |
| libheif-rav1e | 1.23.4-r1 | 1.23.6-r0 |
| libheif-svtenc | 1.23.4-r1 | 1.23.6-r0 |
| libheif-x264 | 1.23.4-r1 | 1.23.6-r0 |
| libheif-x265 | 1.23.4-r1 | 1.23.6-r0 |
| libhwy | 1.4.0-r0 | 1.4.0-r1 |
| libjxl | 0.11.2-r2 | 0.11.2-r4 |
| libx11 | 1.8.13-r0 | 1.8.14-r0 |
| libxi | 1.8.3-r0 | 1.8.4-r0 |
| libxrender | 0.9.12-r0 | 0.9.13-r0 |
| libxtst | 1.2.5-r0 | 1.2.6-r0 |
| pkgconf | 3.0.8-r0 | 3.0.9-r0 |
| postmarketos-base-ui | 61-r0 | 62-r0 |
| postmarketos-base-ui-alsa-utils | 61-r0 | 62-r0 |
| postmarketos-base-ui-audio | 61-r0 | 62-r0 |
| postmarketos-base-ui-audio-backend-pulseaudio | 61-r0 | 62-r0 |
| postmarketos-base-ui-bluez-openrc | 61-r0 | 62-r0 |
| postmarketos-base-ui-elogind | 61-r0 | 62-r0 |
| postmarketos-base-ui-gnome-mobile | 1-r3 | 2-r0 |
| postmarketos-base-ui-modemmanager | 61-r0 | 62-r0 |
| postmarketos-base-ui-modemmanager-openrc | 61-r0 | 62-r0 |
| postmarketos-base-ui-networkmanager | 61-r0 | 62-r0 |
| postmarketos-base-ui-openrc | 61-r0 | 62-r0 |
| postmarketos-base-ui-openrc-settingsd | 61-r0 | 62-r0 |
| postmarketos-base-ui-qt-tweaks | 61-r0 | 62-r0 |
| postmarketos-base-ui-qt-wayland | 61-r0 | 62-r0 |
| postmarketos-base-ui-wifi-wpa_supplicant | 61-r0 | 62-r0 |
| postmarketos-base-ui-wifi-wpa_supplicant-openrc | 61-r0 | 62-r0 |
| postmarketos-mkinitfs | 2.11.1-r0 | 2.12.0-r1 |
| sqlite-libs | 3.53.4-r0 | 3.54.1-r0 |
| stevia | 0.57.0-r2 | 0.57.0-r3 |
| stevia-schemas | 0.57.0-r2 | 0.57.0-r3 |
| uim | 1.9.6-r4 | 1.9.9-r0 |
| uim-anthy | 1.9.6-r4 | 1.9.9-r0 |
| uim-gtk3 | 1.9.6-r4 | 1.9.9-r0 |
| xfsprogs | 7.1.1-r1 | 7.2.0-r0 |
| xfsprogs-extra | 7.1.1-r1 | 7.2.0-r0 |

[结构化验证](validation.json)。硬件验收边界仍按260/261及硬件清单解释；原958包收据是升级前历史状态。
