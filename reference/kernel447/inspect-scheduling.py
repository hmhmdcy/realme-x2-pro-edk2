from pathlib import Path
import hashlib,json
import storage
HERE=Path(__file__).resolve().parent;b=storage.mount.mounted_build();config=b/'.config'
text=config.read_text();assert '# CONFIG_UCLAMP_TASK is not set' in text and 'CONFIG_CPU_FREQ_GOV_SCHEDUTIL=y' in text
doc=b.parent/'source354/Documentation/scheduler/sched-util-clamp.rst';assert doc.exists()
r=dict(stage=447,retained_shared_build_configuration_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),retained_build_uclamp_task=False,retained_build_schedutil=True,matching_linux_scheduler_documentation_available=True,running_kernel_config_requeried=False,phone_accessed=False,no_new_kernel_build_or_scheduler_policy_selected=True,next_requires_stream_lifetime_scoped_capacity_selection_and_restore=True,passed=True)
(HERE/'scheduling-options-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
