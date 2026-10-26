/* Host fault injection executes the production handoff source unchanged. */
#include "qcom_pmic_typec_apsd.c"
#include <stdio.h>
#include <stdlib.h>

static int cases, quiesced, joins, released, api_error, add_error;
static void (*cleanup_action)(void *);
static void *cleanup_data, *allocated;
static s64 test_ms;
static int io_count, fail_io, failed_code, change_io, slow_io, writes;
static unsigned int write_regs[8], write_masks[8], write_vals[8];

void *devm_kzalloc(struct device *dev, size_t n, int flags)
{
	(void)dev; (void)flags;
	allocated = calloc(1, n);
	return allocated;
}
int samurai_apsd_tcpm_quiesce(struct device *dev, struct regmap *map)
{
	(void)dev; (void)map;
	joins++;
	if (api_error)
		return api_error;
	quiesced = 1;
	return 0;
}
void samurai_apsd_tcpm_release(struct device *dev)
{
	(void)dev;
	released++;
	/* A release is lifetime cleanup, and must retain the physical fence. */
}
int devm_add_action_or_reset(struct device *dev, void (*fn)(void *), void *arg)
{
	(void)dev;
	if (add_error) {
		fn(arg);
		return add_error;
	}
	cleanup_action = fn;
	cleanup_data = arg;
	return 0;
}
s64 ktime_get_boottime(void) { return ++test_ms; }
s64 ktime_to_ms(s64 value) { return value; }
void msleep(unsigned int ms) { test_ms += ms; }
static int io(struct regmap *map)
{
	io_count++;
	if (io_count == change_io)
		map->r[0x1310] ^= BIT(4);
	if (io_count == slow_io)
		test_ms += 300;
	return io_count == fail_io ? failed_code : 0;
}
int regmap_read(struct regmap *map, unsigned int reg, unsigned int *value)
{
	int ret = io(map);
	if (ret)
		return ret;
	*value = map->r[reg];
	return 0;
}
int regmap_update_bits(struct regmap *map, unsigned int reg,
			unsigned int mask, unsigned int value)
{
	int ret;
	if (!quiesced || joins != 1)
		abort();
	if ((reg != 0x1362 || mask != 0x6c) && (reg != 0x1358 || mask != 0x80))
		abort();
	if (value)
		abort();
	write_regs[writes] = reg;
	write_masks[writes] = mask;
	write_vals[writes++] = value;
	ret = io(map);
	if (ret)
		return ret;
	map->r[reg] = (map->r[reg] & ~mask) | value;
	return 0;
}

#define CHECK(expr) do { cases++; if (!(expr)) { \
	fprintf(stderr, "line %d: %s\n", __LINE__, #expr); abort(); } } while (0)
static void reset(struct regmap *map)
{
	if (cleanup_action)
		cleanup_action(cleanup_data);
	free(allocated);
	allocated = NULL; cleanup_action = NULL; cleanup_data = NULL;
	memset(map, 0, sizeof(*map));
	map->r[0x150a] = 0x40;
	map->r[0x1362] = 0xff;
	map->r[0x1358] = 0xff;
	quiesced = joins = released = api_error = add_error = 0;
	io_count = fail_io = change_io = slow_io = writes = 0;
	failed_code = -EIO;
	test_ms = 0;
}

int main(void)
{
	struct regmap map;
	struct device dev = { 0 };
	struct qcom_pmic_typec_apsd *h;
	int max_io, i, before;
	unsigned int r, mask;
	const int sample_starts[] = { 5, 9, 15, 19, 25 };

	reset(&map);
	h = qcom_pmic_typec_apsd_prepare(&dev, &map);
	CHECK(!IS_ERR(h));
	CHECK(writes == 2 && write_regs[0] == 0x1362 && write_regs[1] == 0x1358);
	CHECK(map.r[0x1362] == 0x93 && map.r[0x1358] == 0x7f);
	max_io = io_count;
	CHECK(qcom_pmic_typec_apsd_verify(h) == 0);
	CHECK(qcom_pmic_typec_apsd_verify(NULL) == 0);
	CHECK(joins == 1 && writes == 2);
	cleanup_action(cleanup_data); cleanup_action = NULL;
	CHECK(released == 1 && quiesced);

	/* Every actual transport call of the production takeover can fail. */
	for (i = 1; i <= max_io; i++) {
		reset(&map); fail_io = i;
		h = qcom_pmic_typec_apsd_prepare(&dev, &map);
		CHECK(IS_ERR(h) && PTR_ERR(h) == -EIO);
		CHECK(writes <= 2 && joins == 1);
	}
	/* A changed/off mixed or inherited source must not start PD hardware. */
	for (i = 0; i < 6; i++) {
		reset(&map);
		switch (i) {
		case 0: map.r[0x1310] = 0x10; break;
		case 1: map.r[0x1509] = 0x20; break;
		case 2: map.r[0x150b] = 0x20; break;
		case 3: map.r[0x150b] = 0x01; break;
		case 4: map.r[0x150a] = 0x00; break;
		case 5: map.r[0x150a] = 0x60; break;
		}
		h = qcom_pmic_typec_apsd_prepare(&dev, &map);
		CHECK(IS_ERR(h) && PTR_ERR(h) == -EAGAIN && !writes);
	}
	for (i = 0; i < (int)ARRAY_SIZE(sample_starts); i++) {
		reset(&map); change_io = sample_starts[i];
		h = qcom_pmic_typec_apsd_prepare(&dev, &map);
		CHECK(IS_ERR(h));
	}
	reset(&map); slow_io = 1;
	h = qcom_pmic_typec_apsd_prepare(&dev, &map);
	CHECK(IS_ERR(h) && PTR_ERR(h) == -EAGAIN && !writes);
	reset(&map); api_error = -EBUSY;
	h = qcom_pmic_typec_apsd_prepare(&dev, &map);
	CHECK(IS_ERR(h) && PTR_ERR(h) == -EBUSY && !writes && !io_count && !released);
	reset(&map); add_error = -ENOMEM;
	h = qcom_pmic_typec_apsd_prepare(&dev, &map);
	CHECK(IS_ERR(h) && PTR_ERR(h) == -ENOMEM && !writes && released == 1);

	/* A live isolation fault latches. No RX/TX guard performs a repair. */
	for (r = 0; r < 2; r++) {
		for (mask = 1; mask <= 0x80; mask <<= 1) {
			if (!(mask & isolation[r].mask))
				continue;
			reset(&map);
			h = qcom_pmic_typec_apsd_prepare(&dev, &map);
			CHECK(!IS_ERR(h));
			map.r[isolation[r].reg] |= mask;
			CHECK(qcom_pmic_typec_apsd_verify(h) == -EUCLEAN);
			map.r[isolation[r].reg] &= ~mask;
			before = io_count;
			CHECK(qcom_pmic_typec_apsd_verify(h) == -EUCLEAN && io_count == before);
			CHECK(writes == 2 && joins == 1);
		}
	}
	for (i = 1; i <= 2; i++) {
		reset(&map);
		h = qcom_pmic_typec_apsd_prepare(&dev, &map);
		CHECK(!IS_ERR(h)); fail_io = io_count + i;
		CHECK(qcom_pmic_typec_apsd_verify(h) == -EIO);
		fail_io = 0; before = io_count;
		CHECK(qcom_pmic_typec_apsd_verify(h) == -EIO && io_count == before);
	}
	CHECK(PTR_ERR(qcom_pmic_typec_apsd_prepare(NULL, &map)) == -EINVAL);
	CHECK(PTR_ERR(qcom_pmic_typec_apsd_prepare(&dev, NULL)) == -EINVAL);
	reset(&map);
	printf("production handoff: %d assertions; %d takeover IO fault points\n", cases, max_io);
	return 0;
}
