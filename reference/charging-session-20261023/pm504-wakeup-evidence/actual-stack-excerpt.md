# PM03实际首栈节选

原始完整trace及SHA见actual-evidence-result.json，时间为boot时钟秒。

```text
2945.379580: suspend_resume: dpm_suspend[2] begin
         python3-11789   [004] d..3.  2945.386880: wakeup_source_activate: samurai-usb-input state=0xa30001
         python3-11789   [004] d..3.  2945.386884: <stack trace>
 => trace_event_raw_event_wakeup_source
 => __traceiter_wakeup_source_activate
 => wakeup_source_activate
 => __pm_stay_awake.part.0
 => pm_stay_awake
 => power_supply_changed
 => samurai_usb_set_property
 => power_supply_set_property
 => dwc3_vbus_budget_close
 => dwc3_plat_suspend
 => platform_pm_suspend
 => dpm_run_callback
 => device_suspend
 => dpm_suspend
 => dpm_suspend_start
 => suspend_devices_and_enter
 => pm_suspend
 => state_store
 => kobj_attr_store
 => sysfs_kf_write
 => kernfs_fop_write_iter
 => vfs_write
 => ksys_write
 => __arm64_sys_write
 => invoke_syscall.constprop.0
 => el0_svc_common.constprop.0
 => do_el0_svc
 => el0_svc
 => el0t_64_sync
```
