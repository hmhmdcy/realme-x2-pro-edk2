# USB 软件通知修正：已装入并通过单次待机

2026-10-24。[实际结果](../../charging-management-20261023/native-pm-notify-r2-result.json)：Image504保持，只冷更USB模块ebfcb和manifest94a659，未写boot/logdump。新boot启动、待机前后均通过原12项检查。单次RTC窗口实际驻留14.874秒，success+1、fail不变、无新增故障；原key/NCM自动恢复，native及硬件输入仍500mA。

对照原PM03，prepare至machine_resume期间没有USB PSY唤醒。真实调用栈显示延后的通知在samurai_usb_complete中发布。8CPU trace无溢出/丢失，独立复核、同子进程wait、alarm与trace清理完成，当前采用指针及新guard已更新。物理USB插拔唤醒、长待机功耗和完整电源管理尚未验收。

host.py只派生旧安全stage的当前504身份、两文件包、采用guard和实际缓存绑定；原Full/保护检查、INHIBIT、atomic fsync、两文件恢复保留，不热卸native provider。restart.py沿原设备停机顺序及已验证EUD-off重启尾部进入bootloader，再仅执行fastboot reboot。postboot.py复用原12项原始数据审计，仅绑定实际模块更新。pm.py复用原27例RTC/计数握手primitive、监督器和受限trace；review.py重审前后原始数据、源码、终态和trace，再CAS发布当前采用指针。

失败保留：第一次restart inspect仍要求EUD驱动存在，在提交前拒绝；已确认无claim后改用当前实际EUD-off分支，仅提交一次重启。首次postboot采集早于保护驱动自动启动，未通过；稍后独立只读采集全部通过。未篡改旧失败。初次本地相机路径错误在采集前修正。各工具只供新事务派生参考；本次namespace已经终态，禁止重放。

精确回退是当前Image504下的d046/34ead两文件逆向包及一次冷启动；完整旧PM组合7cb/18e8/ace2为另一范围。原厂和私人载荷、过程原件保留在私有输出目录。
