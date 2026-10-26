# 当前 PM 取证候选：revision2独立薄审

限定新增范围未见剩余阻断。作者最终delivery `8b49ee7a…30c84` 的34个文件/历史原件已独立核完整SHA与长度；只读取源码、差异和收据，没有导入作者模块、执行作者新旧测试、入口、trace、PM、设备、构建或Git。

R1的returned事实缺口已闭合。R2实际worker `ac9436c6…9a738` 相对完整保留的R1只有一处表达式变化：`functional_facts.returned`取原始mem_returned。严格功能门仍要求outcome returned，RTC cleanup失败仍使本地功能检查失败，但不会抹掉已经返回及实际时长。新增收据 `b09f7ae1…17f03b` 直接调用实际classify，覆盖原primitive可产生的RTC清理失败终态、未返回和正常返回三向量；审阅者没有重跑。原10方法透明复用，旧27/29/126未重跑。

prepare、trace及primitive均与R1逐字相同。primitive还与原fd3fd4完整文件一致，healthy/services/configuration_preserved/audit_trace四函数与原worker源码相同。新绑定要求真实502七原件、collector审计、adopt request/result、原payload、同child真实rc0、严格回复、current pointer及新endpoint；不会沿旧r5 boot或PID门推造身份。

本次具体核了：缺pm_wakeup_irq保存errno与null；RTC只用实时唯一IRQ；实时format/精确filter/有界stacktrigger先核后enable，sync/count后arm前再核；失败或预算耗尽不arm；部分write可能生效时也只清理其新独占instance与尝试项，不碰global trace。10..20秒功能门、原始返回事实、独立原因证据和根整机接受分开。无USB恢复、桌面、充电策略或DWC修改。

README已补根实际操作的detached owned supervisor/Popen、stdin DEVNULL、独立普通私有日志、PID/startticks/argv/request hash、同child wait和未知只观察约束。该合同尚不是已实现或已运行的host dispatcher。根仍需协调当前窗口，并独立整合实际Windows NCM及原严格key数据恢复；本审查不能批准实机PM或认定唯一RTC唤醒原因。

机器收据：`review-result.json`，SHA `2452aa1fd61da3b6eabc8bf2b85a77eb516b8e1132d24d89168402ef446340cb`。R1发现原文保留在`review-r1.md`，不抹掉修订历史。
