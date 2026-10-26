# APSD：实际owner身份与最终传输边界

2026-10-25。沿已验证的DWC/PD5V/PHY接线，补齐原`rerun_once(ctx, epoch)`在最终1341命令前只有旧epoch、没有源/租约复核的缺口。当前运行的普通USB500路径保持；此目录未安装，实际路由授权缺口仍使所有生产APSD命令返回EOPNOTSUPP。

新接口携带原worker内嵌的attempt地址、原始新鲜sample和回调。实际owner检查精确地址、活跃worker阶段、bus上下文、once epoch/已消费状态/截止时间、实际PD lease对象及generation、实际PHY client/cookie/撤销状态、DWC HALT和电源引用；最后仍需路由入口成功和取消检查。字段副本不能替代原owner身份。回调在input锁下运行，禁止获取owner registry、join、恢复或重新获取租约；各supplier撤销先发布，再在其锁外join原worker。

backend先消费epoch，再在同一input锁下重新读取两份相等的七寄存器状态，与原请求的源字段、源/角色条件及新serial核对。最后调用上述真实owner验证，然后只做一次原厂`regmap_write_bits(0x1341, BIT(0), BIT(0))`。错误/未知也消费，不重试；provider重新注册保留原counter，DWC原physical history也不重置。

命令后再取两份新状态，保留独立write和post-read错误；真实断源、角色变化、QC或不稳定为失败/未知。APSD DONE/result正常变化允许，并立即把真实post-write clear交给原once core，避免在下轮poll前丢失；旧DONE仍不能完成。regmap访问之间的物理断源不具备原子性。最终验证之后的撤销属于在途操作，原join必须覆盖它，不能在join完成前释放supplier资源；这些检查不构成一项硬件原子事务。

[传输九组测试](transfer-test-result.json)执行真实backend/reader和已缓存并核hash的实际kernel forced-write inline，硬件/owner验证为模型。[owner十八组测试](owner-test-result.json)执行完整实际owner、PD5V、PHY provider及四个真实PHY窗口函数，复用十二组生命周期并增加真实attempt地址/PD代际/PHY撤销及post-clear处理；最后两组post-write样本为模型，未放开生产路由gate。ASan/UBSan/Werror均通过。初始fixture误要求所有post变化统一ESTALE，实际decoder保留ENODATA；另一次fixture未先结束手动打开的窗口即unbind触发保留状态，均修正测试前提，没有把失败改成硬件成功。增加编译配置门后只重跑受影响owner套件，原结果保留history。

[三个私有W1/Werror对象](build-result.json)均零诊断：当前TYPEC=m owner、仅命令视图builtin owner及input。原共享source/config/build和SDK保持；仅复用原284挂载器及原编译命令，不重建Image/ko。[四对象内部接口检查](interface-result.json)复用未变PD/PHY对象，十一内部API解析、无内部未决，patch fuzz0比对通过；仍有普通kernel imports，不是完整内核链接。

剩余工作是实际可信EUD-off路由supplier/撤销合同、与当前USB13f IRQ/PM源码整合、最终同Image builtin依赖和实际连接周期测试。此backend仍沿旧R7可选传输分支，不能覆盖安装中的新USB驱动。无真实路由能力时不得启用1341，不能把COM不存在或只读拓扑当成授权；完整Type-C/PD/快充继续在需求范围内。
