from pathlib import Path
import runpy,re,difflib,json,hashlib
repo=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(repo/'reference/kernel122/ensure-rootfs-volume.py'))
k=Path('/home/cy122/pmos-samurai-rootfs122/camera124/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel124');ref=repo/'reference/kernel124'
assert not (ref/'sm8150-cphy-power-7.3.patch').exists()
before={};changed={}
def edit(name,fn):
 p=k/name;t=p.read_text();before[name]=t;new=fn(t);assert new!=t,name;p.write_text(new);changed[name]=new
def once(t,a,b):assert t.count(a)==1,(a,t.count(a));return t.replace(a,b,1)
def function(t,name,new):
 m=re.search(r'^(?:static )?(?:s64|int|u8|u16|void) '+name+r'\(',t,re.M);assert m,name
 start=m.start();b=t.index('{',m.end());i=b+1;depth=1
 while depth:depth+=(t[i]=='{')-(t[i]=='}');i+=1
 return t[:start]+new.rstrip()+t[i:]
base='drivers/media/platform/qcom/camss/'
def core(t):
 for label in ['csiphy_res_8150','csid_res_8150']:
  i=t.index('static const struct camss_subdev_resources '+label);j=t.index('\n};',i)+3;s=t[i:j]
  if label.startswith('csiphy'):
   assert s.count('.regulators = {},')==4;s=s.replace('.regulators = {},','.regulators = { { .supply = "vdda-phy", .init_load_uA = 0 } },')
  else:
   pattern=r'\.regulators = \{\s*\{ \.supply = "vdda-phy", \.init_load_uA = 0 \},\s*\{ \.supply = "vdda-pll", \.init_load_uA = 0 \}\s*\},'
   s,n=re.subn(pattern,'.regulators = {},',s);assert n==2
  t=t[:i]+s+t[j:]
 t=function(t,'camss_get_link_freq','''s64 camss_get_link_freq(struct media_entity *entity, unsigned int bpp,
			unsigned int lanes, bool is_cphy)
{
	struct media_pad *sensor_pad;
	unsigned int mul = bpp, div = 2 * lanes;

	/* C-PHY transfers 16 bits per seven symbols per trio. */
	if (!bpp || bpp > 64 || !lanes || lanes > (is_cphy ? 3 : 4))
		return -EINVAL;
	if (is_cphy) {
		mul *= 7;
		div *= 16;
	}
	sensor_pad = camss_find_sensor_pad(entity);
	if (!sensor_pad)
		return -ENODEV;

	return v4l2_get_link_freq(sensor_pad, mul, div);
}''')
 t=once(t,' * @lanes: Number of lanes in the link to the sensor',' * @lanes: Number of lanes or trios in the link to the sensor\n * @is_cphy: Whether the sensor uses C-PHY encoding')
 t=function(t,'camss_parse_endpoint_node','''static int camss_parse_endpoint_node(struct device *dev,
				     struct fwnode_handle *ep,
				     struct camss_async_subdev *csd)
{
	struct csiphy_lanes_cfg *lncfg = &csd->interface.csi2.lane_cfg;
	struct v4l2_mbus_config_mipi_csi2 *mipi_csi2;
	struct v4l2_fwnode_endpoint vep = { { 0 } };
	unsigned int i, used = 0;
	bool is_cphy;
	int ret;

	ret = v4l2_fwnode_endpoint_parse(ep, &vep);
	if (ret)
		return ret;
	if (vep.bus_type != V4L2_MBUS_CSI2_DPHY &&
	    vep.bus_type != V4L2_MBUS_CSI2_CPHY)
		return -EINVAL;
	is_cphy = vep.bus_type == V4L2_MBUS_CSI2_CPHY;
	mipi_csi2 = &vep.bus.mipi_csi2;
	if (!mipi_csi2->num_data_lanes ||
	    mipi_csi2->num_data_lanes > (is_cphy ? 3 : 4))
		return -EINVAL;
	if (is_cphy && fwnode_property_present(ep, "clock-lanes"))
		return -EINVAL;
	if (!is_cphy) {
		if (mipi_csi2->clock_lane > 4)
			return -EINVAL;
		used = BIT(mipi_csi2->clock_lane);
	}
	for (i = 0; i < mipi_csi2->num_data_lanes; i++) {
		unsigned int pos = mipi_csi2->data_lanes[i];

		if (pos > (is_cphy ? 2 : 4) || (used & BIT(pos)))
			return -EINVAL;
		if (is_cphy && (mipi_csi2->line_orders[i] !=
			       V4L2_MBUS_CSI2_CPHY_LINE_ORDER_ABC ||
			       mipi_csi2->lane_polarities[i + 1]))
			return -EINVAL;
		used |= BIT(pos);
	}
	csd->interface.csiphy_id = vep.base.port;
	lncfg->is_cphy = is_cphy;
	if (!is_cphy) {
		lncfg->clk.pos = mipi_csi2->clock_lane;
		lncfg->clk.pol = mipi_csi2->lane_polarities[0];
	}
	lncfg->num_data = mipi_csi2->num_data_lanes;
	lncfg->data = devm_kcalloc(dev, lncfg->num_data,
				 sizeof(*lncfg->data), GFP_KERNEL);
	if (!lncfg->data)
		return -ENOMEM;
	for (i = 0; i < lncfg->num_data; i++) {
		lncfg->data[i].pos = mipi_csi2->data_lanes[i];
		lncfg->data[i].pol = mipi_csi2->lane_polarities[i + 1];
	}
	return 0;
}''')
 return t
edit(base+'camss.c',core)
edit(base+'camss.h',lambda t:once(t,'unsigned int lanes);','unsigned int lanes, bool is_cphy);'))
edit(base+'camss-csiphy.h',lambda t:once(once(once(t,' * @num_data: number of data lanes',' * @is_cphy: C-PHY trio encoding\n * @num_data: number of data lanes or trios'),'struct csiphy_lanes_cfg {','struct csiphy_lanes_cfg {\n\tbool is_cphy;'),'\tint lane_array_size;','\tint lane_array_size;\n\tconst struct csiphy_lane_regs *cphy_regs;\n\tint cphy_array_size;'))
edit(base+'camss-csid.h',lambda t:once(t,'struct csid_phy_config {','struct csid_phy_config {\n\tbool is_cphy;'))
def csiphy(t):
 a='camss_get_link_freq(&csiphy->subdev.entity, bpp, num_lanes);';assert t.count(a)==2;t=t.replace(a,'camss_get_link_freq(&csiphy->subdev.entity, bpp, num_lanes,\n\t\t\t\t\tcsiphy->cfg.csi2->lane_cfg.is_cphy);')
 t=once(t,'\tu8 lane_mask = csiphy->res->hw_ops->get_lane_mask(&cfg->csi2->lane_cfg);','\tu8 lane_mask;')
 marker='\tu8 val;\n\n\tlink_freq = camss_get_link_freq'
 t=once(t,marker,'''	u8 val;

	/* Reject unsupported C-PHY before any lane mask or MMIO access. */
	if (cfg->csi2->lane_cfg.is_cphy &&
	    (!csiphy->regs || !csiphy->regs->cphy_regs))
		return -EOPNOTSUPP;
	lane_mask = csiphy->res->hw_ops->get_lane_mask(&cfg->csi2->lane_cfg);

	link_freq = camss_get_link_freq''')
 return t
edit(base+'camss-csiphy.c',csiphy)
def csid(t):
 t=once(t,'\t\t\t\t\tcsid->phy.lane_cnt);','\t\t\t\t\tcsid->phy.lane_cnt, csid->phy.is_cphy);')
 t=once(t,'\t\t\tcsid->tpg_linked = true;','\t\t\tcsid->phy.is_cphy = false;\n\t\t\tcsid->tpg_linked = true;')
 t=once(t,'\t\t\tcsid->phy.lane_cnt = lane_cfg->num_data;','\t\t\tcsid->phy.is_cphy = lane_cfg->is_cphy;\n\t\t\tcsid->phy.lane_cnt = lane_cfg->num_data;')
 return t
edit(base+'camss-csid.c',csid)
edit(base+'camss-csid-gen2.c',lambda t:once(t,'\tval |= phy->csiphy_id << CSI2_RX_CFG0_PHY_NUM_SEL;','\tval |= phy->csiphy_id << CSI2_RX_CFG0_PHY_NUM_SEL;\n\tval |= phy->is_cphy << CSI2_RX_CFG0_PHY_TYPE_SEL;'))
def phy(t):
 table=(out/'cphy-table-native-private.h').read_text();t=once(t,'/* 5nm 2PH', '/* SM8150 v1.1: own active camera_8150 GPLv2 register table. */\n'+table+'\n/* 5nm 2PH')
 t=once(t,'lane_mask = CSIPHY_3PH_CMN_CSI_COMMON_CTRL5_CLK_ENABLE;', 'lane_mask = lane_cfg->is_cphy ? 0 :\n\t\tCSIPHY_3PH_CMN_CSI_COMMON_CTRL5_CLK_ENABLE;')
 # Preserve the D-PHY calculation while making its bounds explicit and
 # allowing both C-PHY settle bytes. Actual C-PHY timing remains unverified.
 t=function(t,'csiphy_settle_cnt_calc','''static u16 csiphy_settle_cnt_calc(s64 link_freq, u32 timer_clk_rate)
{
	u64 ui, timer_period, count;

	if (link_freq <= 0 || !timer_clk_rate)
		return 0;
	ui = div_u64(1000000000000ULL, link_freq) / 2;
	timer_period = div_u64(1000000000000ULL, timer_clk_rate);
	count = div_u64(85000 + 6 * ui, timer_period);
	if (count <= 6)
		return 0;
	return min_t(u64, count - 6, 0xffff);
}''')
 t=function(t,'csiphy_gen2_config_lanes','''static void csiphy_gen2_write_regs(struct csiphy_device *csiphy,
				  const struct csiphy_lane_regs *r,
				  int array_size, u16 settle_cnt)
{
	int i;
	u32 val;

	for (i = 0; i < array_size; i++, r++) {
		switch (r->csiphy_param_type) {
		case CSIPHY_SETTLE_CNT_LOWER_BYTE:
			val = settle_cnt & 0xff;
			break;
		case CSIPHY_SETTLE_CNT_HIGHER_BYTE:
			val = (settle_cnt >> 8) & 0xff;
			break;
		case CSIPHY_SKEW_CAL:
		case CSIPHY_DNP_PARAMS:
			continue;
		default:
			val = r->reg_data;
			break;
		}
		writel_relaxed(val, csiphy->base + r->reg_addr);
		if (r->delay_us)
			udelay(r->delay_us);
	}
}

static void csiphy_gen2_config_lanes(struct csiphy_device *csiphy,
				     struct csiphy_config *cfg, u16 settle_cnt)
{
	struct csiphy_lanes_cfg *c = &cfg->csi2->lane_cfg;
	int i, size = csiphy->regs->cphy_array_size;

	if (!c->is_cphy) {
		csiphy_gen2_write_regs(csiphy, csiphy->regs->lane_regs,
				      csiphy->regs->lane_array_size, settle_cnt);
		return;
	}
	for (i = 0; i < c->num_data; i++)
		csiphy_gen2_write_regs(csiphy,
			csiphy->regs->cphy_regs + c->data[i].pos * size,
			size, settle_cnt);
}''')
 t=once(t,'\tu8 settle_cnt;\n\tu8 val;','\tu16 settle_cnt;\n\tu8 val;')
 t=once(t,'\tval = CSIPHY_3PH_CMN_CSI_COMMON_CTRL5_CLK_ENABLE;\n\tfor (i = 0; i < c->num_data; i++)\n\t\tval |= BIT(c->data[i].pos * 2);','\tval = c->is_cphy ? 0 : CSIPHY_3PH_CMN_CSI_COMMON_CTRL5_CLK_ENABLE;\n\tfor (i = 0; i < c->num_data; i++)\n\t\tval |= BIT(c->data[i].pos * 2 + c->is_cphy);')
 t=once(t,'\tval = 0x00;\n\twritel_relaxed(val, csiphy->base +\n\t\t       CSIPHY_3PH_CMN_CSI_COMMON_CTRLn(regs->offset, 0));','''	if (c->is_cphy) {
		writel_relaxed(0x01, csiphy->base +
			       CSIPHY_3PH_CMN_CSI_COMMON_CTRLn(regs->offset, 0));
		usleep_range(1000, 1100);
	}
	val = 0x00;
	writel_relaxed(val, csiphy->base +
		       CSIPHY_3PH_CMN_CSI_COMMON_CTRLn(regs->offset, 0));''')
 t=once(t,'csiphy_gen2_config_lanes(csiphy, settle_cnt);','csiphy_gen2_config_lanes(csiphy, cfg, settle_cnt);')
 t=once(t,'\t/* IRQ_MASK registers - disable all interrupts */','''	/* Native v1.1 C-PHY IRQ mask, after the ordered trio table. */
	if (c->is_cphy) {
		static const u8 irq_masks[] = {
			0xff, 0xff, 0xfb, 0xff, 0x7f, 0xff,
			0xff, 0xef, 0xff, 0xff, 0xff
		};

		for (i = 0; i < ARRAY_SIZE(irq_masks); i++)
			writel_relaxed(irq_masks[i], csiphy->base +
				CSIPHY_3PH_CMN_CSI_COMMON_CTRLn(regs->offset, i + 11));
		return;
	}
	/* IRQ_MASK registers - disable all interrupts */''')
 t=once(t,'regs = devm_kmalloc(dev, sizeof(*regs), GFP_KERNEL);','regs = devm_kzalloc(dev, sizeof(*regs), GFP_KERNEL);')
 marker='case CAMSS_8150:\n\t\tregs->lane_regs = &lane_regs_sc8280xp[0];\n\t\tregs->lane_array_size = ARRAY_SIZE(lane_regs_sc8280xp);'
 t=once(t,marker,marker+'\n\t\tregs->cphy_regs = &lane_regs_sm8150_cphy[0][0];\n\t\tregs->cphy_array_size = ARRAY_SIZE(lane_regs_sm8150_cphy[0]);')
 return t
edit(base+'camss-csiphy-3ph-1-0.c',phy)
def schema(t):
 t=once(t,'Board PHY supply used by the current CAMSS resource table.','1.2V CSIPHY analog supply shared by all four PHYs.')
 t=once(t,'\n  vdda-pll-supply:\n    description: Board PLL supply used by the current CAMSS resource table.\n','\n')
 t=once(t,'        - vdda-pll-supply\n','')
 marker='''            required:
              - data-lanes'''
 add='''            allOf:
              - if:
                  properties:
                    bus-type:
                      const: 1
                  required:
                    - bus-type
                then:
                  properties:
                    data-lanes:
                      maxItems: 3
                      uniqueItems: true
                      items:
                        maximum: 2
                    clock-lanes: false
                    lane-polarities: false
                    line-orders:
                      $ref: /schemas/types.yaml#/definitions/uint32-array
                      minItems: 1
                      maxItems: 3
                      items:
                        const: 0
'''
 assert t.count(marker)==4;t=t.replace(marker,add+marker);return t
edit('Documentation/devicetree/bindings/media/qcom,sm8150-camss.yaml',schema)
edit('arch/arm64/boot/dts/qcom/sm8150-samurai.dts',lambda t:t+'\n/* Native 19781 CSIPHY rail; CAMSS remains disabled pending sensor/CPAS proof. */\n&camss {\n\tvdda-phy-supply = <&vreg_l3c_1p2>;\n};\n')
patch=''.join(''.join(difflib.unified_diff(before[n].splitlines(True),changed[n].splitlines(True),fromfile='a/'+n,tofile='b/'+n)) for n in before)
(ref/'sm8150-cphy-power-7.3.patch').write_text(patch)
report=dict(candidate=124,base=123,changed_files=list(before),patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),native_cphy_tuples=129,native_reference_differences_preserved=3,cphy_support_only_sm8150=True,unsupported_hardware_rejected_before_mmio=True,cphy_rate_ratio=dict(mul='bpp*7',div='lanes*2*16'),single_shared_native_1200000_uv_phy_supply=True,unused_csid_analog_supplies_removed=True,camss_still_disabled=True,cpas_qos_not_guessed=True,cphy_timing_hardware_unverified=True,phone_unchanged=True)
(ref/'cphy-port-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
