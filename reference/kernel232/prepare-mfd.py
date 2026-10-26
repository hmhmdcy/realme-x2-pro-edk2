"""Add exclusive reset backends and explicit supplier lifetime to isolated195."""
from pathlib import Path
import difflib,hashlib,json
REF=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel232')
old=(P/'originals/drivers/mfd/qcom-pm8008.c').read_text();new=old
def once(a,b):
 global new
 assert new.count(a)==1,(a[:100],new.count(a));new=new.replace(a,b,1)
once('#include <linux/regmap.h>','#include <linux/regmap.h>\n#include <linux/reset.h>')
helpers=r'''
static struct i2c_driver pm8008_mfd_driver;

/* Laboratory bring-up only: do not instantiate rear regulator children. */
static bool experimental_p_address_only;
module_param(experimental_p_address_only, bool, 0444);
MODULE_PARM_DESC(experimental_p_address_only, "Validate dependent rear PMIC identity without creating children");

struct pm8008_reset {
	struct device *dev;
	struct gpio_desc *gpio;
	struct reset_control *control;
};

static bool pm8008_has_reset(struct pm8008_reset *reset)
{
	return reset->gpio || reset->control;
}

static int pm8008_set_reset(struct pm8008_reset *reset, bool asserted)
{
	if (reset->control)
		return asserted ? reset_control_assert(reset->control) :
				  reset_control_deassert(reset->control);
	if (reset->gpio)
		return gpiod_direction_output(reset->gpio, asserted);
	return 0;
}

/* Keep persistent managed links, including across a supplier rebind. */
static int pm8008_link_bound_supplier(struct device *dev, struct device *supplier,
				      const struct device_driver *expected)
{
	struct device_link *link;
	int ret = 0;

	if (supplier == dev)
		return -EINVAL;
	device_lock(supplier);
	if (!device_is_bound(supplier) ||
	    READ_ONCE(supplier->links.status) != DL_DEV_DRIVER_BOUND)
		ret = -EPROBE_DEFER;
	else if (expected && supplier->driver != expected)
		ret = -EINVAL;
	else {
		link = device_link_add(dev, supplier, DL_FLAG_AUTOPROBE_CONSUMER);
		if (!link)
			ret = -EINVAL;
	}
	device_unlock(supplier);
	return ret;
}

static int pm8008_link_reset_supplier(struct device *dev)
{
	struct of_phandle_args spec;
	struct device *supplier;
	int ret;

	if (!dev->of_node ||
	    of_count_phandle_with_args(dev->of_node, "resets", "#reset-cells") != 1)
		return -EINVAL;
	ret = of_parse_phandle_with_args(dev->of_node, "resets", "#reset-cells", 0, &spec);
	if (ret)
		return ret;
	if (!of_device_is_available(spec.np)) {
		ret = -EINVAL;
		goto put_node;
	}
	supplier = get_dev_from_fwnode(of_fwnode_handle(spec.np));
	if (!supplier) {
		ret = -EPROBE_DEFER;
		goto put_node;
	}
	ret = pm8008_link_bound_supplier(dev, supplier, NULL);
	put_device(supplier);
put_node:
	of_node_put(spec.np);
	return ret;
}

static int pm8008_get_reset(struct i2c_client *client, struct pm8008_reset *reset)
{
	struct device *dev = &client->dev;
	int ret;

	reset->dev = dev;
	if (device_property_present(dev, "resets")) {
		if (device_property_present(dev, "reset-gpios"))
			return -EINVAL;
		ret = pm8008_link_reset_supplier(dev);
		if (ret)
			return ret;
		/* Ordinary exclusive get: do not assert/deassert before address checks. */
		reset->control = devm_reset_control_get_exclusive(dev, NULL);
		return PTR_ERR_OR_ZERO(reset->control);
	}

	/* Preserve the original warm-Q GPIO behaviour, including optional reset. */
	reset->gpio = devm_gpiod_get_optional(dev, "reset", GPIOD_ASIS);
	return PTR_ERR_OR_ZERO(reset->gpio);
}

static struct device_node *pm8008_address_supplier_node(struct i2c_client *client)
{
	struct device *dev = &client->dev;
	struct device_node *node, *p_parent, *q_parent;
	u32 address, initial;
	bool same_parent;

	if (!device_property_present(dev, "qcom,address-setup-supplier"))
		return NULL;
	if (!dev->of_node || client->addr != PM8008_FACTORY_ADDRESS ||
	    (client->flags & I2C_CLIENT_TEN) ||
	    device_property_present(dev, "qcom,initial-address") ||
	    !device_property_present(dev, "resets") ||
	    device_property_present(dev, "reset-gpios") ||
	    of_property_count_u32_elems(dev->of_node, "qcom,address-setup-supplier") != 1)
		return ERR_PTR(-EINVAL);
	node = of_parse_phandle(dev->of_node, "qcom,address-setup-supplier", 0);
	if (!node)
		return ERR_PTR(-EINVAL);
	p_parent = of_get_parent(dev->of_node);
	q_parent = of_get_parent(node);
	same_parent = p_parent && p_parent == q_parent;
	of_node_put(p_parent);
	of_node_put(q_parent);
	if (node == dev->of_node || !same_parent || !of_device_is_available(node) ||
	    !of_device_is_compatible(node, "qcom,pm8008") ||
	    of_property_present(node, "qcom,address-setup-supplier") ||
	    of_property_read_u32(node, "reg", &address) ||
	    of_property_read_u32(node, "qcom,initial-address", &initial) ||
	    address != PM8008_ASSIGNED_ADDRESS || initial != PM8008_FACTORY_ADDRESS) {
		of_node_put(node);
		return ERR_PTR(-EINVAL);
	}
	return node;
}

static int pm8008_link_address_supplier(struct i2c_client *client,
				       struct device_node *node)
{
	struct i2c_client *supplier;
	int ret;

	supplier = i2c_find_device_by_fwnode(of_fwnode_handle(node));
	if (!supplier)
		return -EPROBE_DEFER;
	if (supplier->adapter != client->adapter || (supplier->flags & I2C_CLIENT_TEN))
		ret = -EINVAL;
	else
		ret = pm8008_link_bound_supplier(&client->dev, &supplier->dev,
						&pm8008_mfd_driver.driver);
	put_device(&supplier->dev);
	return ret;
}

static void pm8008_hold_reset(void *data)
{
	struct pm8008_reset *reset = data;
	int ret;

	ret = pm8008_set_reset(reset, true);
	if (ret)
		dev_err(reset->dev, "failed to hold consumer reset: %d\n", ret);
}
'''
anchor='static DEFINE_MUTEX(pm8008_address_lock);\n';once(anchor,anchor+helpers)
once('struct gpio_desc *reset)\n{\n\tstruct device *dev = &client->dev;', 'struct pm8008_reset *reset)\n{\n\tstruct device *dev = &client->dev;')
once('\t\tif (reset) {','\t\tif (pm8008_has_reset(reset)) {')
once('client->addr != PM8008_ASSIGNED_ADDRESS || !reset ||','client->addr != PM8008_ASSIGNED_ADDRESS || !pm8008_has_reset(reset) ||')
assert new.count('gpiod_direction_output(reset,')==5
new=new.replace('gpiod_direction_output(reset,','pm8008_set_reset(reset,')
start=new.index('static int pm8008_reset_and_address(');end=new.index('\nstatic int pm8008_probe(',start)
new=new[:start]+r'''static int pm8008_reset_and_address(struct i2c_client *client)
{
	struct device *dev = &client->dev;
	struct device_node *supplier;
	struct pm8008_reset *reset;
	int ret;

	supplier = pm8008_address_supplier_node(client);
	if (IS_ERR(supplier))
		return PTR_ERR(supplier);
	/* Incomplete rear VIN description: missing opt-in must never release P. */
	if (supplier && !experimental_p_address_only) {
		ret = -EOPNOTSUPP;
		goto put_node;
	}
	reset = devm_kzalloc(dev, sizeof(*reset), GFP_KERNEL);
	if (!reset) {
		ret = -ENOMEM;
		goto put_node;
	}
	ret = pm8008_get_reset(client, reset);
	if (ret)
		goto put_node;
	if (supplier) {
		/* Registered before MFD children: remove children, hold P, put reset. */
		ret = devm_add_action_or_reset(dev, pm8008_hold_reset, reset);
		if (ret)
			goto put_node;
		ret = pm8008_set_reset(reset, true);
		if (ret)
			goto put_node;
		ret = pm8008_link_address_supplier(client, supplier);
		if (ret)
			goto put_node;
	}

	mutex_lock(&pm8008_address_lock);
	ret = pm8008_initialize_address(client, reset);
	if (!ret && supplier)
		ret = pm8008_read_identity(client, client->addr);
	mutex_unlock(&pm8008_address_lock);
put_node:
	of_node_put(supplier);
	return ret;
}
''' +new[end:]
once('\tdummy = devm_i2c_new_dummy_device(dev, client->adapter, client->addr + 1);',
     '\tif (experimental_p_address_only &&\n'
     '\t    device_property_present(dev, "qcom,address-setup-supplier")) {\n'
     '\t\tdev_info(dev, "dependent PMIC identity verified; address-only bring-up, no children\\n");\n'
     '\t\treturn 0;\n'
     '\t}\n\n'
     '\tdummy = devm_i2c_new_dummy_device(dev, client->adapter, client->addr + 1);')
assert new.count('dev_set_drvdata(dev, domain);')==1
assert 'GPIOD_ASIS' in new and 'devm_reset_control_get_exclusive' in new
assert 'reset_control_get_exclusive_deasserted' not in new
(REF/'qcom-pm8008.c').write_text(new);(P/'candidate/qcom-pm8008.c').write_text(new)
patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/drivers/mfd/qcom-pm8008.c',tofile='b/drivers/mfd/qcom-pm8008.c'))
(REF/'pm8008-reset-backend-dependency.patch').write_text(patch)
report=dict(stage=232,isolated_mfd_candidate=True,old_source_sha256=hashlib.sha256(old.encode()).hexdigest(),source_sha256=hashlib.sha256(new.encode()).hexdigest(),irq_domain_drvdata_preserved=True,legacy_gpio_asis_retained=True,provider_and_q_supplier_links_added=True,release_attempted_and_sid_timing_retained=True,build_or_runtime_not_yet_validated=True)
(REF/'mfd-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
