from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2')
for name in ['README.md','FLYWHEEL.md','linux-port/docs/HARDWARE-STATUS.md']:
    p=root/name; text=p.read_text()
    text=text.replace('55秒GNSS start/stop窗口没有位置/卫星/NMEA事件，停止回执已取得，定位未验收。','独立CLI的55秒窗口无事件；随后同一LOC客户端取得55个position-report、55个NMEA、54个卫星信息事件，全部位置状态in-progress，实际定位未验收；停止回执已取得。')
    text=text.replace('完整构建进行中，未上机。','完整Image/模块/DTB构建通过，未上机。')
    text=text.replace('LOC三项只读查询、start/stop回执通过；55秒窗口无位置/卫星/NMEA事件','LOC控制与同客户端连续报告/NMEA/SV事件通过；55次位置报告均in-progress，start/stop回执通过')
    p.write_text(text)
p=root/'NEXT-SESSION.md'; text=p.read_text()
text=text.replace('原生QMI DMS/UIM/NAS查询通过，LOC控制查询/start/stop通过，但55秒无定位/SV/NMEA事件；停止回执已取得。','原生QMI DMS/UIM/NAS、LOC控制查询通过。CLI分进程55秒无事件；同LOC客户端v3取得55个position-report、55个NMEA、54个SV事件，55个位置状态均in-progress，未定位成功；session117停止回执已取得。v1/v2在引擎启动前因GI信号/枚举错误失败，保留档案。')
text=text.replace('完整Image/modules/DTB构建日志在kernel114/kernel-full-build.log；若有活动构建先检查进程/产物，不重复启动。','完整Image/modules/DTB构建通过，见reference/kernel114/kernel-build-validation.json。ZRAM与ZSMALLOC均为模块，需成套安装新模块。kernel114/kernel-full-build.log保留过程；没有剩余构建进程。')
text=text.replace('下一步完成并记录构建，再核对','下一步核对')
p.write_text(text)
p=root/'sessions/114-complete-rootfs-and-qmi-ipa-foundation.md'; text=p.read_text()
text=text.replace('完整内核/模块构建仍在进行，未部署。','完整Image/全部modules/DTB构建通过；ZRAM和ZSMALLOC均为模块，SYN_COOKIES启用。离线核验曾把ZSMALLOC误假定为builtin、把两条banner误假定为唯一条，已按实际配置和完整UTS_VERSION筛选修正核验，没有为此重编。见[构建核验](../reference/kernel114/kernel-build-validation.json)。未部署。')
text=text.replace('接下来：完成并记录#114离线构建；核对','接下来：核对')
text+='''

## GNSS 同一客户端闭环

确认目标已有Qmi/Qrtr GI后，编写单LOC客户端流程：发现QRTR0、open EXPECT_INDICATIONS、注册事件、periodic start、55秒监听、同客户端stop。v1在start前因未实现fix-session-state信号退出；v2在start前因PERIODIC枚举名错误退出，均保留档案/补充stop请求。GI的get_result在成功时返回None而在失败时抛异常，不能用bool(None)判失败。v3使用PERIODIC_FIXES及正确GI结果处理。

v3注册/start/stop都通过、Python错误0；收到engine-state1、position-report55、NMEA55、gnss-sv-info54。55个position-report状态均IN_PROGRESS，没有有效位置fix。这个闭环证明真实连续事件通道可以使用，也表明先前分进程CLI无事件不足以判断硬件不工作；GNSS实际定位与桌面集成仍未完成。NV6/source4保持，session117停止回执取得。[同客户端核验](../reference/kernel114/gnss-single-client-validation.json)。不因室内短窗口未fix要求用户人工搬动手机，也不反复等待，继续IPA/其它项。
'''
p.write_text(text)
print('STAGE114_KERNEL_AND_GNSS_FINAL_EVIDENCE_RECONCILED')
