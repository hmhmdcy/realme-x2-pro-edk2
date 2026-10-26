# 2026-10-18：APK索引刷新与版本约束核对

通过USB及原SSH主机密钥核对，同260启动。手机实际执行 `apk --timeout 10 update` 成功；四个在线源及两个本地适配源全部加载，共37,249个不同包。pmOS旧域名正常跳转至mirror.nura.eco。本次访问成功不代表此前网络超时已长期解决。

当前仍958包。仓库文件、repositories.d、world及已安装数据库的前后SHA256全部一致；没有安装、升级、卸载包，没有添加nightly源、密钥或修改版本约束，也没有重启。

## Phoc结论

- 本机及当前常规仓库均为 `phoc/phoc-schemas 0.57.0-r1`。
- 当前pmOS/Nura与Alpine edge main/community/testing索引中没有Phoc 0.58。在线条件下的 `apk add --simulate 'phoc>=0.58' 'phoc-schemas>=0.58'` 失败，只能找到0.57。
- world没有Phoc版本或校验和锁定；已安装反向依赖Phosh及phosh-portalsconf只依赖无版本限定的phoc。当前阻碍是常规仓库没有新版，不是本机锁住Phoc。
- 另外从PC实时下载Phosh nightly的aarch64索引，列出 `phoc/phoc-schemas 0.58.0_git20261004-r0`、`phosh 99990.58.0_git20261012-r0`、`stevia/stevia-schemas 0.58.0_git20261007-r0`。它是额外nightly来源，手机当前未启用。
- nightly索引来自 `https://nightly.postmarketos.org/phosh-nightly/aarch64/APKINDEX.tar.gz`，重定向至nightly.nura.eco，Last-Modified为2026-10-16 07:02:33 GMT。归档存在签名条目；本轮未导入密钥或验签、未测试该二进制的安装依赖及协议支持，不能视为可直接部署或已修复。

## 新版与约束

55个已安装包有更高版本。允许访问网络的普通 `apk upgrade --simulate` 成功：54个升级、3个新增依赖、0删除，模拟总数961。新增依赖是uim-gtk4、postmarketos-base-ui-udev及postmarketos-base-ui-gnome-mobile-udev。此为依赖求解结果，不是实机升级或功能验收。

stevia-schemas是55项中唯一未被普通模拟升级选中的包：world持有其当前包校验和约束。`--latest`模拟明确报该约束阻止r3；仅在模拟中改成r3版本约束时，stevia和schemas两包可共同更新。本轮没有修改真实world。普通模拟允许stevia本体从r2升r3、保留旧schemas。

相机stack精确依赖libcamera r15及config-r10；GNSS stack精确依赖ModemManager r1及helper 2-r1。它们是适配约束，与Phoc版本无关。当前正规MM源只有r0，本机定制r1更高，不应将其标成落后。

普通模拟通过；强制 `--latest` 的另一次模拟同时出现polkit提供者、OpenRC用户支持与软键盘提供者冲突，不能将其当成普通升级结果或强制执行依据。

最初用 `--network=no` 模拟会屏蔽未缓存的APK，仅供诊断，不能代表完整可升级事务；上述54+3结论来自保留网络访问、使用已刷新索引的模拟。所有命令均带simulate，installed数据库哈希复核保持。

## 全部55项

| 软件包 | 已安装 | 常规仓库新版 |
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

GTK4 4.24.1-r0、Phosh 0.57.0-r3、设置及商店51.0-r0、Mesa 26.2.4-r1与当前常规索引一致。本表只比较已安装包与已配置常规仓库，不以nightly替代其候选集合。

[结构化收据](validation.json)。完整原始输出及脚本仅存私人目录 E:/edk2-samurai-out/repository-audit-20261018。
