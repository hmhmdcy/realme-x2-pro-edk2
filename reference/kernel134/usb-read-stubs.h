/* SPDX-License-Identifier: GPL-2.0-only */
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
struct samurai_usb_input { void *map; int lock; };
static struct samurai_usb_status fixture[2];
static int fixture_reads, fixture_fault, fixture_lock_balance;
static void fixture_reset(struct samurai_usb_status a, struct samurai_usb_status b, int fault)
{
	fixture[0] = a; fixture[1] = b;
	fixture_reads = 0; fixture_fault = fault; fixture_lock_balance = 0;
}
static void mutex_lock(int *lock) { (void)lock; fixture_lock_balance++; }
static void mutex_unlock(int *lock) { (void)lock; fixture_lock_balance--; }
static int regmap_read(void *map, unsigned int reg, unsigned int *value)
{
	static const unsigned int expected[] = { 0x1307, 0x1308, 0x1310, 0x1506, 0x1509, 0x150b, 0x150d };
	const struct samurai_usb_status *s = &fixture[fixture_reads / 7];
	const unsigned char fields[] = { s->apsd, s->result, s->plugin, s->cc, s->attached, s->misc, s->legacy };
	int i = fixture_reads++;
	(void)map;
	assert(i < 14 && reg == expected[i % 7]);
	if (i == fixture_fault) return -EIO;
	*value = fields[i % 7];
	return 0;
}
