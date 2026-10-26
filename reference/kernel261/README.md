# 261：中文、应用商店与屏幕键盘检查

2026-10-17，通过 USB 和原 SSH 主机密钥检查实机，启动身份仍与260一致，958包。当前 `/etc/os-release` 标识 Nura edge，属于 postmarketOS 演进的 Alpine 用户态；Phosh0.57.0-r3、Phoc0.57.0-r1、Stevia0.57.0-r2。**存在日常桌面功能的安装与配置缺项。普通编辑焦点切换的键盘显隐通过；10月18日另已复现搜索捕获路径的误弹出与不收起，不能把普通窗口测试泛化成键盘没有问题。** 包数量或硬件验收不能代表日常系统功能完整。

本轮没有安装、升级软件、修改持久配置、刷新系统目录、重启或刷写。解锁后先后短暂显示GTK3、GTK4临时测试窗口，切换焦点并调用键盘显隐接口，随后关闭窗口。原始收据仅存 PC 私人目录 `E:/edk2-samurai-out/kernel261`；[脱敏结果](desktop-audit-validation.json)。

## 中文缺项

| 检查 | 实机结果 | 影响 |
| --- | --- | --- |
| 中文字体 | `fc-list :lang=zh` 无结果，仅安装 font-droid、font-terminus | 缺少 Fontconfig 可用中文字库 |
| 中文界面 | Phosh、Stevia、设置、GTK3/GTK4、商店的 zh_CN 翻译文件均不存在 | 单改界面语言不能补出翻译 |
| Locale | musl-locales 未安装；配置 en_US.UTF-8，实际桌面 C.UTF-8 | 语言资源与会话语言尚未配置完整 |
| 输入源 | 只有 `[('xkb', 'us')]` | 没有启用中文输入源 |
| 输入引擎 | UIM1.9.6已安装，登记了简体拼音 py、pyunihan、繁体拼音等；Stevia链接libuim | 不能把问题说成完全没有拼音引擎 |
| IBus | 框架已安装，未运行可连接的IBus会话，未安装ibus-libpinyin | GNOME设置中的引擎发现与Stevia内置UIM接入需要分别处理 |

后续应补中文字体、主要应用的翻译和locale支持，明确界面语言与拼音输入的目标，再接入已有UIM拼音并实测触屏候选、选词、提交。无需仅为拼音再叠加多个输入框架。新版Stevia手册介绍的 `('ibus', 'uim:cn')` 可作接入线索，但本轮没有修改输入源，也没有证明0.57实机设置界面能直接发现或添加它，不能当作已验收修复。[上游发行手册](https://manpages.debian.org/unstable/phosh-osk-stevia/phosh-osk-stevia.1.en.html)

## 商店目录与网络

GNOME Software51、APK2插件、apk-polkit后台和alpine-appstream-downloader已安装；这不是单纯少装商店程序。`/var/lib/swcatalog` 没有Alpine仓库目录，AppStream仅识别28个软件组件，主要来自已安装应用和系统附带列表，不能覆盖仓库里的可安装应用。

本轮手机对AppStream的main/community/testing三个aarch64目录HEAD均在8秒请求窗口内超时；GET复查main/community以及Alpine官方CDN的APKINDEX同样超时，postmarketOS镜像的APKINDEX则HTTP200。系统chrony已同步。可以确认目录缺失且当前访问相关源受阻；尚未区分网络路径、站点响应和连接环境的具体原因，不能称作服务器永久不可用或手机完全断网。

Flatpak只有依赖库，没有命令行工具和GNOME Software Flatpak插件，所以当前商店也没有接入Flathub。是否需要增加Flathub是后续软件来源选择；恢复原生APK商店首先要解决目录下载与网络可达性。目录机制见[维护者说明](https://blogs.gnome.org/pabloyoyoista/2023/03/05/gs-and-pmos-a-bumpy-road/)。本轮没有执行商店安装或界面搜索验收。

## 键盘自动收起

初始锁屏阶段只读检查；用户回复已解锁后分别执行约13秒的GTK3、GTK4原生Wayland窗口测试。GTK3的 `GTK_IM_MODULE=wayland` 仅作用于测试子进程；GTK4使用默认输入模块，没有设置GTK_IM_MODULE，两者均未修改桌面全局环境。持续运行的键盘是Stevia，未发现POS_DEBUG强制显示覆盖，相关GSettings为普通默认配置。

| 测试步骤 | GTK3 / Wayland IM | GTK4 / 默认IM |
| --- | --- | --- |
| 输入框获得焦点 | 自动展开，3秒采样true | 自动展开，3秒采样true |
| 焦点移到普通按钮 | 约4.133秒收到false，6秒采样false | 约4.160秒收到false，6秒采样false |
| 手动显示 | 成功，9秒采样true | 成功，9秒采样true |
| 手动隐藏 | 成功，12秒采样false | 成功，12秒采样false |
| 关闭测试窗口、恢复之前应用 | Visible再次为true | Visible再次为true |

这证明本机GTK3、GTK4原生Wayland → Phoc → Stevia的基础自动显隐链路可用。GTK4 Entry内部GtkText持有输入焦点，外层Entry.has_focus=false不否定输入激活；本轮以键盘事件和稳定显隐采样为判据。恢复前一应用时再次展开，提示应继续确认具体应用是否重新请求输入或保留输入焦点；尚不能把这一推断当作用户原问题的完整根因。点空白区域不一定导致应用释放焦点，应用退出搜索、失去窗口焦点和仅点空白需要区分。具体应用、浏览器、Qt及XWayland尚未分别复测。

本轮结论是用户层资源与配置需要补齐，不能据此建议重刷系统。中文触屏输入、商店搜索安装、具体应用键盘交互仍需各自验收。

## 2026-10-18：设置或商店退出搜索的补充线索

用户明确问题出现在“设置或商店退出搜索”。上一轮原生窗口通过的是输入框到按钮的焦点切换，不能替代关闭搜索栏的路径验收。

再次通过严格原SSH密钥连接，同260启动身份；设置51.0与商店51.0的公开上游源码均使用GtkSearchBar。GTK4.24.1的 `gtk_search_bar_set_search_mode(false)` 关闭内部revealer；与显式把焦点移到普通按钮的测试是不同路径。源码只能说明应检查搜索栏隐藏后的输入焦点/输入协议状态，尚不能确定本机故障发生于GTK、应用还是键盘。

当前手机锁屏，OSK Visible=false；已请求解锁。已准备搜索栏关闭与stop-search的临时窗口测试，锁屏检查使本轮执行跳过，没有打开测试窗口或绕过锁屏。已读取设置和商店的D-Bus接口与设置可访问性树，仅用于准备后续复测。没有安装软件、修改持久配置或替换进程。

后续先在解锁状态运行搜索栏测试，再复测实际设置与商店的搜索开关；只有拿到搜索模式、焦点/可见性和OSK状态的对应证据后才能归因。相关私人记录 `search-initial.result-private.json`、`search-tree.result-private.json`、`searchbar-test.result-private.json` 均在PC261目录。原261测试收据及其结论保持。

源码：[设置51.0](https://github.com/GNOME/gnome-control-center/blob/51.0/shell/cc-window.c)、[商店51.0](https://github.com/GNOME/gnome-software/blob/51.0/src/gs-shell.ui)、[GTK4.24.1搜索栏](https://github.com/GNOME/gtk/blob/4.24.1/gtk/gtksearchbar.c)。

## 2026-10-18：解锁后复现与输入捕获对照

用户解锁并补充“未点击输入框的时候就会弹出”。本轮已复现：**GTK4搜索栏的输入捕获会在非输入控件获得焦点时激活Wayland文本输入，当前Phosh/Stevia组合随之展开键盘；搜索关闭时文本输入可能刚disable就再次enable。** 这条搜索捕获路径与此前正常通过的普通编辑焦点路径不同。[完整脱敏收据](search-keyboard-validation.json)

测试使用实机GTK4.24.1和现有Phoc/Stevia，窗口每个稳定采样均 `window_active=true`。没有键盘输入或触屏点击测试输入框；仅由定时器打开、关闭搜索和切换临时窗口的输入捕获，搜索内容保持空白。

| 对照条件 | 实测 |
| --- | --- |
| 窗口刚激活，尚未执行打开搜索 | 约0.126秒已收到键盘Visible=true；首次打开搜索在约1.086秒 |
| 保留窗口级输入捕获，关闭搜索 | 6秒搜索模式false、焦点Button，键盘仍true |
| 保留捕获，执行stop-search | 14秒搜索模式false、焦点Button，键盘仍true |
| 移除捕获后再打开、关闭搜索 | 14秒稳定采样键盘false，同样为Button焦点、活动窗口 |

`WAYLAND_DEBUG=client` 仅用于空白临时测试子进程。日志显示搜索关闭阶段先发 `zwp_text_input_v3.disable/commit`，随后马上再次 `enable/commit`，与普通按钮焦点下的键盘持续展开对应。移除捕获本身没有立即focus-out；通过一次新的打开/关闭生命周期后才验证了正常收起，所以不能把临时detach操作宣传为完成了通用修复。

源码链条与观测一致：GtkSearchBar把窗口设置为输入捕获控件；GtkText为此添加绑定同一IM上下文的key controller；GtkEventControllerKey在焦点进入该窗口下的非Text/TextView控件时调用IM focus-in。该机制用于直接打字开始搜索，在本机组合下也激活软键盘。定位到的是GTK搜索输入捕获与Phosh输入法联动的兼容问题，没有证明问题属于手机硬件或缺少某个语言包。[GtkText4.24.1](https://github.com/GNOME/gtk/blob/4.24.1/gtk/gtktext.c)、[key controller4.24.1](https://github.com/GNOME/gtk/blob/4.24.1/gtk/gtkeventcontrollerkey.c)

设置、商店实际搜索开关也做了可访问性点击检查：关闭后搜索entry已离开可访问性树，焦点为普通按钮或应用卡片，但仍读到键盘展开，手动隐藏有效。这轮实际应用收据没有记录活动窗口状态，不单独用于证明全局输入焦点；针对活动窗口的复核后来因自动锁屏跳过。上述因果结论依据明确记录活动状态的GTK4临时窗口及单因素对照，不冒充完整触屏验收。

所有临时窗口均已关闭，没有安装包、修改持久配置、替换Stevia或部署永久补丁。修复方向是区分搜索捕获和真正编辑输入的软键盘激活策略；不能以全局禁用软键盘、屏蔽设置/商店全部自动激活或重刷作为这次已验收的修复。后续补丁仍需在实际设置、商店中回归触屏搜索、退出搜索、重新输入及窗口切换。

## 2026-10-18：上游已有Phoc0.58兼容方案

**上游已发布与本机症状对应的兼容处理，优先采用Phoc0.58.0及其配套wlroots协议支持。** 前述禁用搜索捕获只是因果定位实验，不是需要维护的正式解决方案。本次仅查阅公开源码和官方GitLab API，没有连接、升级或重启手机。[核验结果](upstream-compatibility-validation.json)

GTK上游[8349](https://gitlab.gnome.org/GNOME/gtk/-/work_items/8349)描述了新GTK在点击非输入控件时发出text_input.enable、造成Phosh键盘频繁展开，并指出旧GTK4.22.4没有此现象。核查时该GTK问题仍为opened，不能说GTK端问题已关闭。另一个已关闭的8355只是捕获空格导致按钮不能用空格激活，与本机OSK缺陷不同。

Phoc的[MR813](https://gitlab.gnome.org/World/Phosh/phoc/-/merge_requests/813)于2026-09-19合并，明确用于处理show/hide_input_panel并减少反复显隐。[提交832125ad](https://gitlab.gnome.org/World/Phosh/phoc/-/commit/832125ad3d208ce8b0b81c13f9d5f4d3c9c817b1)及Phoc0.58.0标签源码已核对，官方[10月4日发布说明](https://phosh.mobi/releases/rel-0.58.0/)确认加入text-input-v3接口版本2以适配GTK4.24。

本机GTK4.24.1已经改用窗口级输入捕获，但Phoc仍为0.57.0；空白测试的Wayland日志确认其text-input-manager-v3只宣告接口版本1。旧路径将enable直接转换为键盘激活。Phoc0.58对接口版本2客户端把文本输入启用与显式显示/隐藏面板区分开来，避免输入捕获被等同于弹键盘；旧版本1客户端继续沿用原兼容行为。这里的“版本2”是text-input-v3接口版本，不是换成另一个text-input-v2协议。

GTK4.24.1另已包含[8409](https://gitlab.gnome.org/GNOME/gtk/-/work_items/8409)对应的搜索按钮显式唤起OSK处理，正好补上新协议下点击搜索按钮的正常唤起需求。因此不能仅把GTK最新搜索改动当成应删掉的错误，也不应仅升级Stevia期待修好该路径。Stevia0.57→0.58比较中没有输入方法核心的对应修改；关键兼容处理位于Phoc转发层。

Phoc上游提交包含配套四个wlroots text-input-v3版本2回移补丁，发行构建须实际包含这些支持；只看Phoc版本字符串不足以验收。下一步核对可用APK的来源、依赖和协议支持，采用上游构建或最小回移后，复测不触摸输入框、搜索按钮唤起、退出搜索收起、再次输入和窗口切换。目前未安装该修复，不能把源码核验当作实机通过。
