/* Add this block before pm8008_probe() in drivers/mfd/qcom-pm8008.c. */
#define PM8008_FACTORY_ADDRESS	0x08
#define PM8008_ASSIGNED_ADDRESS	0x04
#define PM8008_SID_CONFIG		0x0644

/* Serialize reset/address setup across PM8008 devices on a shared bus. */
static DEFINE_MUTEX(pm8008_address_lock);

static int pm8008_read_identity(struct i2c_client *client, u16 address)
{
	u8 reg[] = { 0x01, 0x00 }, data[6];
	struct i2c_msg messages[] = {
		{ .addr = address, .len = sizeof(reg), .buf = reg },
		{ .addr = address, .flags = I2C_M_RD, .len = sizeof(data), .buf = data },
	};
	int ret;

	ret = i2c_transfer(client->adapter, messages, ARRAY_SIZE(messages));
	if (ret < 0)
		return ret;
	if (ret != ARRAY_SIZE(messages))
		return -EIO;
	if (data[4] != 0x51 || data[5] != 0x2c)
		return -ENODEV;
	return 0;
}

static int pm8008_initialize_address(struct i2c_client *client,
				     struct gpio_desc *reset)
{
	struct device *dev = &client->dev;
	u8 write_sid[] = { PM8008_SID_CONFIG >> 8, PM8008_SID_CONFIG & 0xff, 1 };
	struct i2c_msg message = {
		.addr = PM8008_FACTORY_ADDRESS,
		.len = sizeof(write_sid),
		.buf = write_sid,
	};
	u32 initial;
	int ret, write_ret;

	if (!device_property_present(dev, "qcom,initial-address")) {
		/* Keep the pre-existing reset behaviour for ordinary PM8008 nodes. */
		if (reset) {
			ret = gpiod_direction_output(reset, 0);
			if (ret)
				return ret;
		}
		usleep_range(1000, 2000);
		return 0;
	}

	ret = device_property_read_u32(dev, "qcom,initial-address", &initial);
	if (ret)
		return ret;
	if (initial != PM8008_FACTORY_ADDRESS ||
	    client->addr != PM8008_ASSIGNED_ADDRESS || !reset ||
	    (client->flags & I2C_CLIENT_TEN) ||
	    !i2c_check_functionality(client->adapter, I2C_FUNC_I2C))
		return -EINVAL;

	ret = pm8008_read_identity(client, client->addr);
	if (!ret) {
		/* Firmware already assigned the address; preserve its LDO state. */
		ret = gpiod_direction_output(reset, 0);
		goto out;
	}
	if (ret != -ENXIO && ret != -EREMOTEIO)
		goto out;

	ret = gpiod_direction_output(reset, 1);
	if (ret)
		goto out;
	usleep_range(10000, 11000);
	ret = pm8008_read_identity(client, initial);
	if (!ret || ret == -ENODEV) {
		dev_err(dev, "initial I2C address is occupied; sibling PMIC must remain reset\n");
		ret = -EBUSY;
		goto out;
	}
	if (ret != -ENXIO && ret != -EREMOTEIO)
		goto out;

	ret = gpiod_direction_output(reset, 0);
	if (ret)
		goto out;
	usleep_range(10000, 11000);
	ret = pm8008_read_identity(client, initial);
	if (ret)
		goto out;
	write_ret = i2c_transfer(client->adapter, &message, 1);
	usleep_range(1000, 2000);
	ret = pm8008_read_identity(client, client->addr);
	if (!ret)
		dev_info(dev, "assigned PM8008 primary address 0x%02x\n", client->addr);
	else if (write_ret < 0)
		ret = write_ret;
	else if (write_ret != 1)
		ret = -EIO;
out:
	return ret;
}

static int pm8008_reset_and_address(struct i2c_client *client)
{
	struct gpio_desc *reset;
	int ret;

	reset = devm_gpiod_get_optional(&client->dev, "reset", GPIOD_ASIS);
	if (IS_ERR(reset))
		return PTR_ERR(reset);

	mutex_lock(&pm8008_address_lock);
	ret = pm8008_initialize_address(client, reset);
	mutex_unlock(&pm8008_address_lock);
	return ret;
}
