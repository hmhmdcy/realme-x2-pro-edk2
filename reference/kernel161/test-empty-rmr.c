#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef uint32_t u32;
struct iommu_resv_region;
struct list_head { struct iommu_resv_region *first; };
struct iommu_resv_region { struct { struct iommu_resv_region *next; } list; };
struct iommu_iort_rmr_data { struct iommu_resv_region rr; int num_sids; uint16_t *sids; };
struct arm_smmu_smr { uint16_t id, mask; bool valid; };
struct arm_smmu_s2cr { int count, type, privcfg; };
struct arm_smmu_device {
	void *dev;
	struct arm_smmu_smr smrs[8];
	struct arm_smmu_s2cr s2crs[8];
};
#define INIT_LIST_HEAD(head) ((head)->first = NULL)
#define list_empty(head) (!(head)->first)
#define list_for_each_entry(pos, head, member) \
	for ((pos) = (head)->first; (pos); (pos) = (pos)->member.next)
#define container_of(ptr, type, member) ((type *)((char *)(ptr) - offsetof(type, member)))
#define dev_fwnode(dev) (dev)
#define ARM_SMMU_GR0_sCR0 0
#define ARM_SMMU_sCR0_CLIENTPD 1
#define S2CR_TYPE_BYPASS 1
#define S2CR_PRIVCFG_DEFAULT 0
static struct iommu_iort_rmr_data fixtures[2];
static uint16_t ids0[] = { 0x800, 0x820 }, ids1[] = { 0x840 };
static int reads, writes, gets, put_count, notices, preserved, fixture_count, exhausted;
static u32 scr0, before_value, after_value;
static void iort_get_rmr_sids(void *dev, struct list_head *head)
{
	(void)dev;
	gets++;
	if (fixture_count) head->first = &fixtures[0].rr;
	for (int i = 0; i < fixture_count; i++)
		fixtures[i].rr.list.next = i + 1 < fixture_count ? &fixtures[i+1].rr : NULL;
}
static void iort_put_rmr_sids(void *dev, struct list_head *head)
{
	(void)dev;
	put_count++;
	head->first = NULL;
}
static u32 arm_smmu_gr0_read(struct arm_smmu_device *smmu, int reg)
{
	(void)smmu;
	assert(reg == 0);
	reads++;
	before_value = scr0;
	return scr0;
}
static void arm_smmu_gr0_write(struct arm_smmu_device *smmu, int reg, u32 value)
{
	(void)smmu;
	assert(reg == 0);
	writes++;
	after_value = scr0 = value;
}
static int arm_smmu_find_sme(struct arm_smmu_device *smmu, uint16_t sid, int mask)
{
	(void)smmu;
	assert(mask == ~0);
	return exhausted ? -1 : (sid >> 5) & 7;
}
static const char *str_plural(int count) { return count == 1 ? "" : "s"; }
static void dev_notice(void *dev, const char *format, int count, const char *plural)
{
	(void)dev;
	(void)format;
	(void)plural;
	notices++;
	preserved = count;
}

/* ACTUAL_FUNCTIONS */

struct observation {
	struct arm_smmu_device state;
	int reads, writes, gets, puts, notices, preserved;
	u32 scr0, before_value, after_value;
};
static struct observation run(int scenario, bool candidate)
{
	struct arm_smmu_device smmu = { 0 };
	reads = writes = gets = put_count = notices = preserved = exhausted = 0;
	scr0 = scenario & 1 ? 0x61 : 0x60;
	before_value = after_value = 0;
	fixture_count = scenario < 2 ? 0 : scenario == 4 ? 2 : 1;
	fixtures[0].num_sids = scenario == 2 ? 0 : scenario == 4 ? 2 : 1;
	fixtures[0].sids = ids0;
	fixtures[1].num_sids = 1;
	fixtures[1].sids = ids1;
	if (scenario == 5) {
		smmu.smrs[0] = (struct arm_smmu_smr){ .id=0x801, .mask=0x420, .valid=true };
		smmu.s2crs[0] = (struct arm_smmu_s2cr){ .count=7, .type=3, .privcfg=2 };
	}
	if (scenario == 6) exhausted = 1;
	if (candidate) candidate_function(&smmu); else baseline_function(&smmu);
	struct observation result;
	memset(&result, 0, sizeof(result));
	result.state = smmu;
	result.reads = reads;
	result.writes = writes;
	result.gets = gets;
	result.puts = put_count;
	result.notices = notices;
	result.preserved = preserved;
	result.scr0 = scr0;
	result.before_value = before_value;
	result.after_value = after_value;
	return result;
}
int main(void)
{
	for (int scenario = 0; scenario < 7; scenario++) {
		struct observation candidate = run(scenario, true);
		struct observation baseline = run(scenario, false);
		if (scenario < 2) {
			assert(candidate.gets == 1 && candidate.reads == 0 && candidate.writes == 0);
			assert(candidate.scr0 == (u32)(scenario & 1 ? 0x61 : 0x60));
			assert(!memcmp(&candidate.state, &baseline.state, sizeof(candidate.state)));
			assert(baseline.writes == 1);
		} else {
			assert(!memcmp(&candidate, &baseline, sizeof(candidate)));
			assert(candidate.reads == 1 && candidate.writes == 1 && candidate.puts == 1);
			assert(candidate.after_value == (candidate.before_value | 1));
			assert(candidate.preserved == (scenario == 2 || scenario == 6 ? 0 : scenario == 4 ? 3 : 1));
		}
	}
	printf("7 actual-function scenarios passed\n");
	return 0;
}
