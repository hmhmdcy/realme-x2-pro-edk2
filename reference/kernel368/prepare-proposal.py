"""Prepare terminal SFR-error handling and a standard bounded devcoredump."""
from pathlib import Path
import difflib,hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'firmware-sfr-validation.json').read_text())['passed']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';relative='drivers/media/platform/qcom/camss/camss-icp-a5-boot.c'
parent=json.loads((HERE.parent/'kernel365/source-state.json').read_text())['commit']
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==parent
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
before=(source/relative).read_text();s=before
s=s.replace('#include <linux/delay.h>','#include <linux/delay.h>\n#include <linux/devcoredump.h>',1)
s=s.replace('#include <linux/unaligned.h>','#include <linux/unaligned.h>\n#include <linux/vmalloc.h>',1)
a=s.index('static int free_memory(');b=s.index('\n\tfor (i = 0; i < ARRAY_SIZE(memories);',a)
old=s[a:b]
assert 'memcpy(a5->sfr' in old
helpers='''/* Fixed little-endian diagnostic record; no image or tuning buffers. */
struct camss_a5_start_dump {
	char magic[8];
	__le32 version;
	__le32 init_response, fw_version;
	__le32 queue_state[6];
	__le32 interrupts, watchdogs, protocol_errors;
	char sfr[512];
};

static void capture_shared_state(struct camss_a5 *a5)
{
	u32 declared;
	size_t bytes;
	unsigned int i;

	if (!a5->shared.cpu || a5->table != a5->shared.cpu ||
	    a5->shared.bytes < sizeof(*a5->table))
		return;
	dma_rmb();
	for (i = 0; i < CAMSS_A5_QUEUE_COUNT; i++) {
		a5->queue_state[i * 2] = le32_to_cpu(READ_ONCE(a5->table->queues[i].read));
		a5->queue_state[i * 2 + 1] = le32_to_cpu(READ_ONCE(a5->table->queues[i].write));
	}
	memset(a5->sfr, 0, sizeof(a5->sfr));
	if (a5->shared.bytes <= SFR_OFFSET + sizeof(__le32))
		return;
	declared = get_unaligned_le32(a5->shared.cpu + SFR_OFFSET);
	if (declared <= sizeof(__le32))
		return;
	bytes = min_t(size_t, declared - sizeof(__le32), sizeof(a5->sfr) - 1);
	bytes = min_t(size_t, bytes, a5->shared.bytes - SFR_OFFSET - sizeof(__le32));
	memcpy(a5->sfr, a5->shared.cpu + SFR_OFFSET + sizeof(__le32), bytes);
}

static void publish_start_failure(struct camss_a5 *a5)
{
	struct camss_a5_start_dump *dump;
	unsigned int i;

	if (!a5->cpu_release_attempted)
		return;
	capture_shared_state(a5);
	dump = vzalloc(sizeof(*dump));
	if (!dump)
		return;
	memcpy(dump->magic, "CAMSSA5", sizeof(dump->magic));
	dump->version = cpu_to_le32(1);
	dump->init_response = cpu_to_le32(a5->init_response);
	dump->fw_version = cpu_to_le32(a5->fw_version);
	for (i = 0; i < ARRAY_SIZE(dump->queue_state); i++)
		dump->queue_state[i] = cpu_to_le32(a5->queue_state[i]);
	dump->interrupts = cpu_to_le32(READ_ONCE(a5->interrupts));
	dump->watchdogs = cpu_to_le32(READ_ONCE(a5->watchdogs));
	dump->protocol_errors = cpu_to_le32(READ_ONCE(a5->protocol_errors));
	memcpy(dump->sfr, a5->sfr, sizeof(dump->sfr));
	/* Publish before power-down or IOMMU teardown can lose the evidence. */
	dev_coredumpv(a5->dev, dump, sizeof(*dump), GFP_KERNEL);
}

static int free_memory(struct camss_a5 *a5)
{
	struct camss_a5_fw_memory *memories[] = { &a5->heap, &a5->shared, &a5->firmware };
	unsigned int i;
	int ret;

	if (a5->cpu_enabled)
		return -EBUSY;
	capture_shared_state(a5);'''
s=s[:a]+helpers+s[b:]
anchor='\tif (a5->power_held) {\n\t\tret = pm_runtime_put_sync_suspend(a5->dev);'
assert s.count(anchor)==1
s=s.replace(anchor,'\tcapture_shared_state(a5);\n'+anchor)
old='''	if (a5->power_held) {
		ret = pm_runtime_put_sync_suspend(a5->dev);
		a5->power_held = false;
		if (ret < 0)
			error = ret;
	}
	ret = free_memory(a5);
	return ret ? ret : error;'''
new='''	/* Retire all firmware DMA aliases while the supplier is still powered.
	 * A failed unmap keeps the PM reference and backing for a later retry.
	 */
	ret = free_memory(a5);
	if (ret)
		return ret;
	if (a5->power_held) {
		ret = pm_runtime_put_sync_suspend(a5->dev);
		a5->power_held = false;
		if (ret < 0)
			return ret;
	}
	return 0;'''
assert s.count(old)==1
s=s.replace(old,new).replace('int ret, error = 0;','int ret;',1)
old='value == 1 || value == 2 || READ_ONCE(a5->boot_expired),'
assert s.count(old)==1
s=s.replace(old,'value == 1 || value == 2 || value == 3 ||\n\t\t\t\t READ_ONCE(a5->boot_expired),')
a=s.index('\t/* The retained firmware entry writes 1 only');b=s.index('\n\tif (value != 1)',a)
s=s[:a]+'''\t/* The retained entry reports 1/2 for ready/initialization failure.
	 * SendSfrMessage publishes 3 after its error record, so it is terminal
	 * failure too. Never send SYS_INIT after a firmware SFR error.
	 */'''+s[b:]
anchor='fail:\n\ta5->cleanup_error = stop_locked(a5);';assert s.count(anchor)==1
s=s.replace(anchor,'fail:\n\tpublish_start_failure(a5);\n\ta5->cleanup_error = stop_locked(a5);')
(P/'boot-before-private.c').write_text(before);(P/'boot-proposed.c').write_text(s)
patch=''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative))
(HERE/'a5-terminal-sfr.patch').write_text(patch)
report=dict(stage=368,source=str(source),parent=parent,changed=[relative],applied=False,installed=False,
    proposed_sha256=hashlib.sha256(s.encode()).hexdigest(),terminal_error_response=3,
    standard_dev_coredump=True,bounded_record_bytes=568,contains_no_image_or_tuning_buffers=True,
    retire_dma_aliases_before_supplier_powerdown=True,unmap_failure_retains_pm_reference=True,
    watchdog_cause_not_yet_fixed_or_claimed=True,hardware_cpu_launch_prepared=False)
(HERE/'proposal-state.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
