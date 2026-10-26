"""Offline R8 provider-only diagnostic derivation; never loads or queries it."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
BASE=REF/'charging-session-20261023/r8-source-integration/kernel-sources/drivers/power/supply'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected={'gauge-protocol.h':'0903f3fa9740f8645dfc8fb5c16f9a35ded63c4ea06f5c9c93475e37bc375f0f',
 'gauge-i2c.h':'897a961d765f794af2358205b46998ac4889f4ad9e91db2265d99cd70d701e77',
 'samurai-gauge-protection.c':'5d77236d555f13fae56adf4a5fcbbb719a9fab9745ae04c02aa558edf39a45b6'}
for n,h in expected.items():assert sha(BASE/n)==h
def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
protocol=(BASE/'gauge-protocol.h').read_text()
protocol=replace(protocol,'static inline int sm_mac_validate(const unsigned char *p, unsigned int bytes,\n\t\t\t\t  unsigned int command)', '''/* Diagnostic-only extension; normal MAC callers retain their six commands. */
static inline int sm_mac_observe_data_size(unsigned int command)
{
	switch (command) {
	case 0x0050: case 0x0052: case 0x0056: return 4;
	default: return sm_mac_data_size(command);
	}
}

static inline int sm_mac_validate_sized(const unsigned char *p, unsigned int bytes,
				       unsigned int command, int size)''')
protocol=replace(protocol,'\tint size = sm_mac_data_size(command);\n','')
protocol=replace(protocol,'/* A valid protocol response is not a claim', '''static inline int sm_mac_validate(const unsigned char *p, unsigned int bytes,
				  unsigned int command)
{
	return sm_mac_validate_sized(p, bytes, command, sm_mac_data_size(command));
}

/* A valid protocol response is not a claim''')
(HERE/'gauge-protocol.h').write_text(protocol)
i2c=(BASE/'gauge-i2c.h').read_text()
i2c=replace(i2c,'#include <linux/i2c.h>','#include <linux/i2c.h>\n#include <linux/ktime.h>')
start=i2c.index('static inline int sm_gauge_mac_locked(')
i2c=i2c[:start]+'''/* Times and return values are observations, not pack-specific bit semantics.
 * raw[] is a complete wire frame only when full_read is true. Incomplete
 * transfers cannot provide a valid 36-byte frame, even if the buffer changed.
 */
struct sm_mac_receipt {
	unsigned int command;
	int expected_size, select_rc, read_rc, validate_rc;
	bool attempted, select_attempted, read_attempted, full_read, validate_attempted;
	u64 started_ns, select_end_ns, read_end_ns, ended_ns;
	unsigned char raw[36];
};

static inline int sm_gauge_mac_transfer_locked(struct i2c_client *g,
	unsigned int command, unsigned char *packet, int size,
	struct sm_mac_receipt *receipt)
{
	unsigned char start = 0x3e;
	struct i2c_msg messages[] = {
		{ .addr = g->addr, .len = 1, .buf = &start },
		{ .addr = g->addr, .flags = I2C_M_RD, .len = 36, .buf = packet },
	};
	int ret;

	if (receipt) {
		receipt->attempted = true;
		receipt->started_ns = ktime_get_boottime_ns();
	}
	if (size < 0) { ret = size; goto out; }
	if (receipt) receipt->select_attempted = true;
	ret = sm_gauge_word_locked(g, 0x3e, true, command);
	if (receipt) {
		receipt->select_rc = ret;
		receipt->select_end_ns = ktime_get_boottime_ns();
	}
	if (ret) goto out;
	usleep_range(1000, 1500); /* unchanged OEM query delay */
	if (receipt) receipt->read_attempted = true;
	ret = __i2c_transfer(g->adapter, messages, ARRAY_SIZE(messages));
	if (receipt) {
		receipt->read_rc = ret;
		receipt->read_end_ns = ktime_get_boottime_ns();
	}
	if (ret != ARRAY_SIZE(messages)) { ret = ret < 0 ? ret : -EIO; goto out; }
	if (receipt) receipt->full_read = receipt->validate_attempted = true;
	ret = sm_mac_validate_sized(packet, 36, command, size);
	if (receipt) receipt->validate_rc = ret;
out:
	if (receipt) receipt->ended_ns = ktime_get_boottime_ns();
	return ret;
}

/* Existing API retains its exact six-command allowlist and error policy. */
static inline int sm_gauge_mac_locked(struct i2c_client *g, unsigned int command,
				      unsigned char *packet)
{
	return sm_gauge_mac_transfer_locked(g, command, packet,
					   sm_mac_data_size(command), NULL);
}

/* Caller holds the same I2C_LOCK_SEGMENT as normal MAC clients. */
static inline int sm_gauge_mac_observe_locked(struct i2c_client *g,
	unsigned int command, struct sm_mac_receipt *receipt)
{
	if (!receipt) return -EINVAL;
	*receipt = (struct sm_mac_receipt){ .command = command,
		.expected_size = sm_mac_observe_data_size(command) };
	return sm_gauge_mac_transfer_locked(g, command, receipt->raw,
					   receipt->expected_size, receipt);
}
#endif
'''
(HERE/'gauge-i2c.h').write_text(i2c)
provider=(BASE/'samurai-gauge-protection.c').read_text()
provider=replace(provider,'struct sm_protection {', '''/* Fixed observation recipe, never a user-supplied MAC selector. */
static const unsigned int sm_evidence_commands[] = {
	0x0001, 0x0051, 0x0053, 0x0054, 0x0057, 0x0050, 0x0052, 0x0056,
};
enum sm_evidence_stage {
	SM_EVIDENCE_NONE, SM_EVIDENCE_ID_FRAME, SM_EVIDENCE_ID_VALUE,
	SM_EVIDENCE_BATTERY_BEFORE, SM_EVIDENCE_STATUS_FRAME,
	SM_EVIDENCE_BATTERY_AFTER, SM_EVIDENCE_COMPLETE,
};
struct sm_mac_evidence {
	bool attempted, terminal;
	unsigned int stage, frames_attempted;
	int error, battery_before, battery_after;
	bool battery_before_valid, battery_after_valid;
	u64 started_ns, battery_before_ns, battery_after_ns, ended_ns;
	struct sm_mac_receipt frames[ARRAY_SIZE(sm_evidence_commands)];
};

struct sm_protection {''')
provider=replace(provider,'\tint last_error;','\tint last_error;\n\tstruct sm_mac_evidence evidence;')
at=provider.index('static int sm_protection_get(')
extra='''/* Caller holds p->lock. One attempt, including failure, per bound instance.
 * Do not change normal health values/last_error, policy, latch or timer here.
 */
static int sm_protection_capture_locked(struct sm_protection *p)
{
	struct sm_mac_evidence *e = &p->evidence;
	int ret;

	if (e->attempted) return -EALREADY;
	*e = (struct sm_mac_evidence){ .attempted = true };
	e->started_ns = ktime_get_boottime_ns();
	for (unsigned int i = 0; i < ARRAY_SIZE(sm_evidence_commands); i++) {
		e->frames[i].command = sm_evidence_commands[i];
		e->frames[i].expected_size = sm_mac_observe_data_size(sm_evidence_commands[i]);
	}
	i2c_lock_bus(p->gauge->adapter, I2C_LOCK_SEGMENT);
	e->stage = SM_EVIDENCE_ID_FRAME;
	e->frames_attempted = 1;
	ret = sm_gauge_mac_observe_locked(p->gauge, 0x0001, &e->frames[0]);
	if (ret) goto out;
	e->stage = SM_EVIDENCE_ID_VALUE;
	if (sm_le16(e->frames[0].raw + 2) != 0x2719) { ret = -ENODEV; goto out; }
	e->stage = SM_EVIDENCE_BATTERY_BEFORE;
	ret = sm_gauge_word_locked(p->gauge, 0x0a, false, 0);
	e->battery_before_ns = ktime_get_boottime_ns();
	if (ret < 0) goto out;
	e->battery_before = ret; e->battery_before_valid = true;
	for (unsigned int i = 1; i < ARRAY_SIZE(sm_evidence_commands); i++) {
		e->stage = SM_EVIDENCE_STATUS_FRAME;
		e->frames_attempted = i + 1;
		ret = sm_gauge_mac_observe_locked(p->gauge, sm_evidence_commands[i], &e->frames[i]);
		if (ret) goto out;
	}
	e->stage = SM_EVIDENCE_BATTERY_AFTER;
	ret = sm_gauge_word_locked(p->gauge, 0x0a, false, 0);
	e->battery_after_ns = ktime_get_boottime_ns();
	if (ret < 0) goto out;
	e->battery_after = ret; e->battery_after_valid = true;
	ret = 0; e->stage = SM_EVIDENCE_COMPLETE;
out:
	i2c_unlock_bus(p->gauge->adapter, I2C_LOCK_SEGMENT);
	e->error = ret; e->ended_ns = ktime_get_boottime_ns(); e->terminal = true;
	return ret;
}

static ssize_t mac_evidence_capture_store(struct device *dev,
	struct device_attribute *attr, const char *buf, size_t count)
{
	struct sm_protection *p = dev_get_drvdata(dev);
	int ret;

	if (!sysfs_streq(buf, "capture")) return -EINVAL;
	mutex_lock(&p->lock);
	ret = sm_protection_capture_locked(p);
	mutex_unlock(&p->lock);
	return ret ? ret : count;
}
static DEVICE_ATTR(mac_evidence_capture, 0200, NULL, mac_evidence_capture_store);

/* Pure cached reads: even attempted=0 never starts an I2C transaction. */
static ssize_t mac_evidence_show(struct device *dev,
	struct device_attribute *attr, char *buf)
{
	struct sm_protection *p = dev_get_drvdata(dev);
	struct sm_mac_evidence *e = &p->evidence;
	ssize_t n;

	mutex_lock(&p->lock);
	n = sysfs_emit(buf, "schema=1 attempted=%d terminal=%d stage=%u error=%d "
		"frames_attempted=%u started_ns=%llu ended_ns=%llu "
		"battery_before_valid=%d battery_before=0x%x battery_before_ns=%llu "
		"battery_after_valid=%d battery_after=0x%x battery_after_ns=%llu "
		"compatibility_verified=0\\n", e->attempted, e->terminal, e->stage, e->error,
		e->frames_attempted, e->started_ns, e->ended_ns,
		e->battery_before_valid, e->battery_before, e->battery_before_ns,
		e->battery_after_valid, e->battery_after, e->battery_after_ns);
	for (unsigned int i = 0; i < ARRAY_SIZE(sm_evidence_commands); i++) {
		struct sm_mac_receipt *r = &e->frames[i];

		n += sysfs_emit_at(buf, n, "frame=%u cmd=0x%04x attempted=%d expected_size=%d "
			"select_attempted=%d select_rc=%d read_attempted=%d read_rc=%d "
			"full_read=%d validate_attempted=%d validate_rc=%d "
			"started_ns=%llu select_end_ns=%llu read_end_ns=%llu ended_ns=%llu raw=",
			i, sm_evidence_commands[i], r->attempted, r->expected_size,
			r->select_attempted, r->select_rc, r->read_attempted, r->read_rc,
			r->full_read, r->validate_attempted, r->validate_rc,
			r->started_ns, r->select_end_ns, r->read_end_ns, r->ended_ns);
		if (r->full_read) n += sysfs_emit_at(buf, n, "%*phN\\n", 36, r->raw);
		else n += sysfs_emit_at(buf, n, "unavailable\\n");
	}
	mutex_unlock(&p->lock);
	return n;
}
static DEVICE_ATTR(mac_evidence, 0400, mac_evidence_show, NULL);

'''
provider=provider[:at]+extra+provider[at:]
provider=replace(provider,'static struct attribute *sm_protection_attrs[] = { &dev_attr_protection_state.attr, NULL };','''static struct attribute *sm_protection_attrs[] = {
	&dev_attr_protection_state.attr, &dev_attr_mac_evidence_capture.attr,
	&dev_attr_mac_evidence.attr, NULL,
};''')
(HERE/'samurai-gauge-protection.c').write_text(provider)
for n in expected:
 patch=''.join(difflib.unified_diff((BASE/n).read_text().splitlines(True),(HERE/n).read_text().splitlines(True),fromfile='r8/'+n,tofile='candidate/'+n))
 (HERE/(n+'.patch')).write_text(patch)
pins={n:{'path':str(BASE/n),'sha256':h} for n,h in expected.items()}
for label,path in {'R8_manifest':REF/'charging-session-20261023/r8-source-integration/source-manifest.json',
 'existing_classifier':HERE.parent/'tca-classifier/tca-reference.h',
 'classifier_receipt':HERE.parent/'tca-classifier/test-result.json',
 'existing_six_packet_audit':HERE.parent/'protection-query-candidate/result.json'}.items():pins[label]={'path':str(path),'sha256':sha(path)}
(HERE/'source-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
print(json.dumps({'derived':True,'device_accessed':False,'old_files_modified':False}))
