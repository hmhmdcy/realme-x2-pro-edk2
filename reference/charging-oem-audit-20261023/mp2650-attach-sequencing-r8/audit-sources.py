"""Read retained sources only; hash and extract the reviewed sequencing evidence."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
SOURCE=REPO/'reference/charging-session-20261023/r8-source-integration'
KERNEL=SOURCE/'kernel-sources/drivers/power/supply'
OLD=REPO/'reference/charging-oem-audit-20261023/audit.json'
old=json.loads(OLD.read_bytes())
manifest=json.loads((SOURCE/'source-manifest.json').read_bytes())
build=REPO/'reference/charging-management-20261023/thermal-bands-build-result.json'
receipt=json.loads(build.read_bytes())
sha=lambda b:hashlib.sha256(b).hexdigest()
paths={name:KERNEL/name for name in ['samurai-mp2650.c','mp2650-core.h','gauge-i2c.h','oem-full-cycle.h','charge-cycle.h','charging-notify.h']}
paths.update(oem_mp2650=Path(old['files']['oem_mp2650']['path'].replace('E:\\','/mnt/e/').replace('\\','/')),
             oem_policy=Path(old['files']['oem_policy']['path'].replace('E:\\','/mnt/e/').replace('\\','/')))
files={}
texts={}
for name,path in paths.items():
    raw=path.read_bytes()
    digest=sha(raw)
    if name in ('oem_mp2650','oem_policy'):
        assert digest==old['files'][name]['sha256']
    else:
        assert digest==manifest['sources']['drivers/power/supply/'+name]['sha256']
        assert digest==receipt['sources'][name]
    files[name]={'path':str(path),'sha256':digest,'bytes':len(raw)}
    texts[name]=raw.decode().splitlines()

ranges={
    'samurai-mp2650.c':[(112,164),(176,198),(221,283),(286,352),(355,373),(412,439),(741,751)],
    'mp2650-core.h':[(159,195),(197,215),(217,281),(284,342)],
    'gauge-i2c.h':[(22,36)],
    'oem-full-cycle.h':[(14,19),(105,162),(173,237)],
    'charge-cycle.h':[(50,86)],
    'oem_mp2650':[(268,306),(504,524),(890,907),(951,1000),(1060,1094),(1635,1675),(1698,1754)],
    'oem_policy':[(3996,4024),(5328,5366),(7351,7378),(7389,7406)],
}
out=[]
for name,windows in ranges.items():
    out.append(f'### {name} SHA256 {files[name]["sha256"]}')
    for start,end in windows:
        out.append(f'--- retained source lines {start}-{end} ---')
        out.extend(f'{i}: {texts[name][i-1]}' for i in range(start,end+1))
(HERE/'source-excerpts.txt').write_text('\n'.join(out)+'\n')
result={
    'schema':'samurai-mp2650-r8-attach-sequencing-source-audit-v1',
    'scope':'static source sequencing and burst-counter semantics only; no code change or hardware measurement',
    'files':files,
    'source_manifest_sha256':sha((SOURCE/'source-manifest.json').read_bytes()),
    'actual_R8_build_receipt_sha256':sha(build.read_bytes()),
    'R8_charger_module_sha256':receipt['module_sha256'],
    'original_OEM_commit':old['commit'],
    'source_excerpts_sha256':sha((HERE/'source-excerpts.txt').read_bytes()),
    'findings':{
        'extra_whole_poll_before_first_safe_apply_found':False,
        'REG13_notification_read_is_after_apply':True,
        'REG13_STATUS_property_reads_hardware_in_getter':True,
        'input_or_protection_event_requeues_immediately':True,
        'fixed_driver_or_apply_sleep_found':False,
        'gauge_MAC_delay_us_range':[1000,1500],
        'normal_poll_delay_ms':1000,
        'ADC_read_does_not_gate_sm_collect_or_sm_apply':True,
        'software_full_recharge_tick_ns':5000000000,
        'full_counter_increments_per_due_step_max':1,
        'catchup_loop':False,
        'unobserved_gap_reset_ns':10000000000,
        'burst_calls_cannot_increase_software_counts_before_next_5s_tick':True,
        'charge_timeout_uses_boottime_delta_not_poll_count':True,
        'short_poll_code_added':False,
        'hardware_required_delay_shortened':False,
    },
    'limits':[
        'No fixed end-to-end latency or root-cause claim follows from source ordering.',
        'REG13 can physically change after the immediate post-apply read; a later normal poll can observe it.',
        'Sequential source/protection/gauge/REG reads and workqueue latency are not atomic or a hard time bound.',
        'Legacy source-manifest boot/USB100 text is historical; this audit uses its unchanged R8 charging-source mapping only.',
        'No claim about current USB IRQ or gauge/UPower latency work owned by the other agent.',
    ],
    'tests_or_builds_run':False,'phone_or_SSH_or_USB_or_SDK_or_Git_accessed':False,
    'production_or_frozen_candidate_bytes_modified':False,
    'audit_source_sha256':sha(Path(__file__).read_bytes()),
}
(HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'source_hashes_match_deployed_receipt':True,'result_sha256':sha((HERE/'result.json').read_bytes())}))
