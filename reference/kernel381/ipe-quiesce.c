// SPDX-License-Identifier: GPL-2.0-only
/* Called with the A5 lifecycle lock held, after its CPU has been stopped.
 * CPAS, IPE clocks and GDSCs must remain held until reset ACKs and DMA unmap.
 */
static int clear_ipe_reset_done(void __iomem *base, u32 status,
				u32 clear, u32 command)
{
	u32 value;

	writel(BIT(0), base + clear);
	writel(1, base + command);
	return readl_poll_timeout(base + status, value, !(value & BIT(0)),
				 100, 10000);
}

static int reset_ipe_block(void __iomem *base, u32 reset, u32 reset_value,
			   u32 status, u32 clear, u32 command)
{
	u32 value;
	int ret;

	ret = clear_ipe_reset_done(base, status, clear, command);
	if (ret)
		return ret;
	writel(reset_value, base + reset);
	ret = readl_poll_timeout(base + status, value, value & BIT(0),
				 100, 50000);
	if (ret)
		return ret;
	return clear_ipe_reset_done(base, status, clear, command);
}

int camss_a5_ipe_quiesce(struct camss_a5_resources *res)
{
	unsigned int i;
	int ret, first_error = 0;

	if (!res || !res->dev || !res->sierra || !res->ipe[0] || !res->ipe[1])
		return -EINVAL;
	if ((res->enabled_groups & 0xd) != 0xd ||
	    (res->held_domains & 0x6) != 0x6)
		return -EHOSTDOWN;
	/* Never race the firmware's own register/IRQ handling. */
	if (readl(res->sierra + 0x08) & BIT(9))
		return -EBUSY;
	for (i = 0; i < 2; i++) {
		res->ipe_reset_acks[i] = 0;
		ret = reset_ipe_block(res->ipe[i], 0x10, 0xf,
				      0x44, 0x34, 0x38);
		if (!ret)
			res->ipe_reset_acks[i] |= BIT(0);
		else if (!first_error)
			first_error = ret;
		/* Try TOP as well when CDM failed; retain DMA backing unless
		 * both blocks of both engines return acknowledged resets.
		 */
		ret = reset_ipe_block(res->ipe[i], 0x1008, 0x3,
				      0x100c, 0x1014, 0x101c);
		if (!ret)
			res->ipe_reset_acks[i] |= BIT(1);
		else if (!first_error)
			first_error = ret;
	}
	return first_error;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_quiesce);
