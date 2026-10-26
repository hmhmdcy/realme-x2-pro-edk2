"""Default-off board-gated current-now/status + current-avg candidate."""
from pathlib import Path
import difflib,hashlib,json,re
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
BASE=REF/'charging-ui-audit-20261023/kernel-bq27xxx_battery.c'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(BASE.read_bytes())=='b2cd415a995cb196559c0e4981988f737c17c98486449659d168314926aec69e'
base=BASE.read_text();source=base
properties=re.search(r'^static enum power_supply_property bq28z610_props\[\] = \{.*?^\};',base,re.M|re.S).group()
new_properties=properties.replace('bq28z610_props[]','bq28z610_samurai_props[]').replace('\n};','\n\tPOWER_SUPPLY_PROP_CURRENT_AVG,\n};')
source=source.replace(properties,properties+'\n\n/* Enabled only by the explicit native samurai profile below. */\n'+new_properties)
marker='static bool bq27xxx_dt_to_nvm = true;'
helpers='''/* Experimental board profile. Built-in kernel command-line opt-in only;
 * read-only after boot, default off. No type or current is supplied by it.
 */
static bool samurai_instant_current;
module_param(samurai_instant_current, bool, 0444);
MODULE_PARM_DESC(samurai_instant_current,
	"Use verified samurai BQ28Z610 0x0c for current_now/status; expose 0x14 current_avg (default off)");

static bool bq27xxx_samurai_instant(struct bq27xxx_device_info *di)
{
	return samurai_instant_current && di->chip == BQ28Z610 &&
		of_machine_is_compatible("realme,samurai") &&
		of_device_is_compatible(di->dev->of_node, "ti,bq28z610");
}

static void bq27xxx_samurai_props(struct bq27xxx_device_info *di,
				 struct power_supply_desc *desc)
{
	if (!bq27xxx_samurai_instant(di))
		return;
	desc->properties = bq28z610_samurai_props;
	desc->num_properties = ARRAY_SIZE(bq28z610_samurai_props);
}

static int bq27xxx_samurai_average_current(struct bq27xxx_device_info *di,
					 union power_supply_propval *val)
{
	int raw;

	if (!bq27xxx_samurai_instant(di))
		return -EINVAL;
	raw = bq27xxx_read(di, BQ27XXX_REG_AI, false);
	if (raw < 0)
		return raw;
	val->intval = (int)((s16)raw) * 1000;
	return 0;
}

'''
# bq27xxx_read is defined later: place its only new user after that helper.
avg_start=helpers.index('static int bq27xxx_samurai_average_current')
avg=helpers[avg_start:];helpers=helpers[:avg_start]
assert source.count(marker)==1;source=source.replace(marker,helpers+marker)
marker='static bool bq27xxx_battery_is_full('
assert source.count(marker)==1;source=source.replace(marker,avg+marker)
old='\tcurr = bq27xxx_read(di, BQ27XXX_REG_AI, false);'
new='''	/* The native opt-in changes both STATUS and CURRENT_NOW together.
	 * CURRENT_AVG retains the original signed 0x14 path. Do not consult
	 * any charger/source property while servicing a gauge property.
	 */
	if (bq27xxx_samurai_instant(di))
		curr = di->bus.read(di, 0x0c, false);
	else
		curr = bq27xxx_read(di, BQ27XXX_REG_AI, false);'''
assert source.count(old)==1;source=source.replace(old,new)
old='''	case POWER_SUPPLY_PROP_CURRENT_NOW:
		ret = bq27xxx_battery_current_and_status(di, val, NULL, NULL);
		break;'''
assert source.count(old)==1
source=source.replace(old,old+'''
	case POWER_SUPPLY_PROP_CURRENT_AVG:
		ret = bq27xxx_samurai_average_current(di, val);
		break;''')
needle='\tpsy_desc->num_properties = bq27xxx_chip_data[di->chip].props_size;'
assert source.count(needle)==1;source=source.replace(needle,needle+'\n\tbq27xxx_samurai_props(di, psy_desc);')
(HERE/'baseline-bq27xxx_battery.c').write_bytes(BASE.read_bytes())
(HERE/'bq27xxx_battery.c').write_bytes(source.encode())
(HERE/'samurai-current.patch').write_text(''.join(difflib.unified_diff(base.splitlines(True),source.splitlines(True),fromfile='a/drivers/power/supply/bq27xxx_battery.c',tofile='b/drivers/power/supply/bq27xxx_battery.c')))
r=dict(passed=True,source_commit='ba61a62293e0f6bc5838c06f2e85e033e3d702a8',baseline_sha256=sha(BASE.read_bytes()),candidate_sha256=sha((HERE/'bq27xxx_battery.c').read_bytes()),
 default_enabled=False,gate=['explicit samurai_instant_current','native realme,samurai','original BQ28Z610 chip','native ti,bq28z610 node'],
 current_now_register='0x0c only enabled profile; original AI otherwise',current_avg_register='0x14 only advertised for enabled profile',
 shared_headers_modified=False,source_or_charger_query_added=False,lock_added=False,installed=False,Image_built=False,phone_accessed=False,SDK_invoked=False,Git_invoked=False)
(HERE/'source-result.json').write_text(json.dumps(r,indent=2)+'\n');print('default-off board-gated candidate prepared')
