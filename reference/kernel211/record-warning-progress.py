from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel211')
plan=json.loads((private/'current-work-private.json').read_text());plan.update(state='211 quiesce halted on MCLK stuck-off WARN during driver-core runtime resume before IMX471 removal. No reboot sent. GUI/GNSS watcher stopped,SLPI offline,ADSP/MPSS running. Normal drivers reloaded successfully with patched crop; libcamera crop/allocator errors absent. Sensor-first rmmod refused due aggregator module ref; explicit sensor unbind while CAMSS present also hit same MCLK WARN. Current warning count2/taint512; IMX471 module loaded but sensor UNBOUND, other5 camera modules loaded.',next='Inspect real CAMCC/MMCX/TITAN_TOP dependencies and old193 runtime-holder source; finish harmless unloaded cleanup for unbound sensor. Fix actual missing power dependency, then resume211 quiesce from known partial state with exact warning audit. Do not rerun original scripts or send transition yet.',transition_pending=False)
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
text=(repo/'NEXT-SESSION.md').read_text();marker='## 当前部署与已验证状态\n';assert marker in text
addition='\n- 211当前现场：停用流程因IMX471移除前自动runtime_resume触发MCLK stuck-off WARN而停止，尚未发重启。对照重载新驱动后CROP/allocator错误消失；先rmmod sensor因CAMSS持有模块引用被拒，保持CAMSS绑定时显式解绑sensor仍触发同类警告。当前WARN2/taint512，sensor已解绑但模块还在，其余五个相机模块已重载；GUI/GNSS watcher已停，SLPI offline、ADSP/MPSS running。继续先定位时钟/供电域依赖，不重跑原脚本，不使用taint0假设。私人211/current-work为实时记录。\n'
text=text.replace(marker,marker+addition,1);(repo/'NEXT-SESSION.md').write_text(text)
print('Partial quiesce and both clock warnings recorded; no reboot or flash submitted.')
