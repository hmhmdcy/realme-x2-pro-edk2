# 温控候选接入片段

独占候选 [mp2650-core.h](thermal-candidate/mp2650-core.h) 与 [thermal-core.patch](thermal-core.patch) 基于本轮生产核心 SHA `672995298c17f95954b25d31352e38be046176ec246a5b243fcc134878907147`。只有头文件候选，没有改根会话 `samurai-mp2650.c`；请与周期支线按 hunk 合并，勿覆盖彼此实现。

`struct sm_charger` 增加：

```c
struct sm_thermal_state thermal;
enum sm_policy_reason policy_reason;
```

在 `sm_collect()` 原本两个来源一致判定的真实断开分支，可与原 `c->session=false; c->latched=false;` 一起清除 `c->thermal`。不能在临时零额度、USB复位、源类型未决或采集失败时清历史。

`sm_step_locked()` 核心建议如下（原有控制模式、暂停验证、IO错误处理原样保留）：

```c
enum sm_policy_reason reason = SM_POLICY_REASON_NONE;
bool thermal_reason;
int held, ret, collect_error;

ret = sm_collect(c, &c->sample);
collect_error = ret;
c->sampled_at = ktime_get_boottime();
if (!ret)
        ret = sm_policy_with_reason(&c->sample, c->cell_ceiling_uv,
                                    c->current_cap_ua, c->input_cap_ua,
                                    &target, &reason);

/* First evaluate the complete policy so heat cannot mask a hard error.
 * A fresh thermal-only reject is allowed to enter/update the hold state.
 */
held = sm_thermal_gate(&c->thermal, c->sample.temp_decic,
        !collect_error && c->sample.valid && c->sample.online &&
        c->sample.protection_ok &&
        (!ret || sm_policy_reason_is_thermal(reason)));
if (!ret && c->sample.online && held) {
        ret = -ERANGE;
        reason = SM_POLICY_REASON_TEMPERATURE;
        target.enable = 0;
}
thermal_reason = sm_policy_reason_is_thermal(reason);
c->policy_reason = reason;
c->latched = sm_sample_latch(c->latched, ret,
                c->source_inhibit || thermal_reason, c->sample.fault);
```

关键点：

- 热迟滞只在 `ret==0` 的在线样本上补充暂停，不能覆盖真实的 `-EIO/-ETIME/-ENODATA` 等错误；离线样本不能被旧热迟滞改成错误。
- `c->latched` 继续作为 OR 输入，温控恢复绝不清已有故障；`sm_stop` 失败仍由原控制分支锁存。
- 正确热／band-OVP reason 只是允许后续重新评估，不是许可直接充电；每次仍采集所有保护、预算、电芯和故障，并应用实际温区CV／OVP。
- `sm_policy_with_reason` 保留原错误码便于现有日志；判断是否可恢复必须看 reason，不能单看裸错误码。
- 普通 sysfs telemetry 可增加 `policy_reason` 和 `thermal_hold`，便于区分可恢复抑制和电气锁存；温控暂停期现有 target.enable 必须为0。

原厂内部温区防抖没有全部迁移，本候选只补外部冷热恢复2℃迟滞；全局温区边界和各温区CV／OVP完全不提高。软件验证只覆盖纯核心及模拟状态顺序，不构成实机高／低温激励验收。
