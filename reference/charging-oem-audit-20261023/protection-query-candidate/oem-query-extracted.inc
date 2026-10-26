#define BQ28Z610_REG_CNTL1					0x3e
#define BQ28Z610_REG_CNTL1_SIZE				4
#define BQ28Z610_SEAL_STATUS				0x0054
#define BQ28Z610_SEAL_BIT				(BIT(0) | BIT(1))
#define BQ28Z610_SEAL_VALUE					3
#define BQ28Z610_REG_GAUGE_EN				0x0057
#define BQ28Z610_GAUGE_EN_BIT				BIT(3)
static int bq8z610_sealed(void)
{
	int value = 0;
	u8 CNTL1_VAL[BQ28Z610_REG_CNTL1_SIZE] = {0,0,0,0};
	bq27541_i2c_txsubcmd(BQ28Z610_REG_CNTL1, BQ28Z610_SEAL_STATUS);
	usleep_range(10000, 10000);
	bq27541_read_i2c_block(BQ28Z610_REG_CNTL1, BQ28Z610_REG_CNTL1_SIZE, CNTL1_VAL);
	pr_err("%s bq8z610_sealed CNTL1_VAL[0] = %x,CNTL1_VAL[1] = %x,\
		CNTL1_VAL[2] = %x,CNTL1_VAL[3] = %x,\n",
		__func__,CNTL1_VAL[0],CNTL1_VAL[1],CNTL1_VAL[2],CNTL1_VAL[3]);
		value = (CNTL1_VAL[3] & BQ28Z610_SEAL_BIT);
	if(value == BQ28Z610_SEAL_VALUE) {
		pr_err("bq8z610 sealed, value = %x return 1\n",value);
		return 1;
	} else {
		pr_err("bq8z610 sealed, value = %x return 0\n",value);
		return 0;
	}
}
static int bq8z610_check_gauge_enable(void)
{
	/*    return control_cmd_read(di, CONTROL_STATUS) & (1 << 13);*/
	int value = 0;
	u8 CNTL1_VAL[BQ28Z610_REG_CNTL1_SIZE] = {0,0,0,0};
	bq27541_i2c_txsubcmd(BQ28Z610_REG_CNTL1, BQ28Z610_REG_GAUGE_EN);
	//usleep_range(10000, 10000);
	msleep(1000);
	bq27541_read_i2c_block(BQ28Z610_REG_CNTL1, BQ28Z610_REG_CNTL1_SIZE, CNTL1_VAL);
	pr_err("%s  CNTL1_VAL[0] = %x,CNTL1_VAL[1] = %x,\
		CNTL1_VAL[2] = %x,CNTL1_VAL[3] = %x,\n",
		__func__,CNTL1_VAL[0],CNTL1_VAL[1],CNTL1_VAL[2],CNTL1_VAL[3]);
	value = (CNTL1_VAL[2] & BQ28Z610_GAUGE_EN_BIT);
	if(value == BQ28Z610_GAUGE_EN_BIT) {
		pr_err("bq8z610 gauge_enable, value = %x return 1\n",value);
		return 1;
	} else {
		pr_err("bq8z610 gauge_enable, value = %x return 0\n",value);
		return 0;
	}
}
