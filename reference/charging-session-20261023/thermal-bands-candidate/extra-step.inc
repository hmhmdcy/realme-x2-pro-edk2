
	/* The same effective band drives target, Full and recharge across 44 C. */
	sequences++;initialize(&c,&bus);f=normal();
	f.sample.cell1_uv=f.sample.cell2_uv=4000000;f.sample.pack_uv=8000000;
	f.sample.temp_decic=440;
	CHECK(at(&c,1,f)==0&&c.thermal.band==5&&c.full_state.band==5&&c.target.cell_uv==4125000);
	f.sample.temp_decic=439;CHECK(at(&c,2,f)==0&&c.thermal.band==5&&c.target.cell_uv==4125000);
	f.sample.cell1_uv=f.sample.cell2_uv=4300000;f.sample.pack_uv=8600000;
	CHECK(at(&c,3,f)==-EOVERFLOW&&!c.latched&&c.thermal_reason==SM_POLICY_REASON_BAND_OVP&&stopped(&bus));
	f.sample.cell1_uv=f.sample.cell2_uv=4000000;f.sample.pack_uv=8000000;
	f.sample.temp_decic=420;CHECK(at(&c,4,f)==0&&c.thermal.band==5);
	f.sample.temp_decic=419;CHECK(at(&c,5,f)==0&&c.thermal.band==4&&c.full_state.band==4&&c.target.cell_uv==4362500);
	CHECK(c.target.current_ua==250000&&c.target.input_ua==500000);

	/* OEM 0 C direction window is 0.5 C, without a second 2 C gate. */
	sequences++;initialize(&c,&bus);f=normal();
	f.sample.cell1_uv=f.sample.cell2_uv=3800000;f.sample.pack_uv=7600000;
	f.sample.temp_decic=-1;CHECK(at(&c,1,f)==0&&c.thermal.band==0&&c.target.cell_uv==3975000);
	f.sample.temp_decic=4;CHECK(at(&c,2,f)==0&&c.thermal.band==0&&c.full_state.band==0);
	f.sample.temp_decic=5;CHECK(at(&c,3,f)==0&&c.thermal.band==1&&c.target.cell_uv==4362500);
	f.sample.temp_decic=-4;CHECK(at(&c,4,f)==0&&c.thermal.band==1&&c.full_state.band==1&&c.target.cell_uv==4362500);
	CHECK(c.full_result.recharge_threshold_uv==4162500&&c.full_result.sw_threshold_uv==4350000);
	/* The static COLD OVP reject in preflight is re-evaluated, not retained
	 * as an accidental second policy, after the OEM LCOLD band is selected. */
	f.sample.cell1_uv=f.sample.cell2_uv=4000000;f.sample.pack_uv=8000000;
	CHECK(at(&c,5,f)==0&&!c.latched&&c.thermal.band==1&&c.target.cell_uv==4362500);

	/* Missing sample and a hard fault freeze band history; neither is detach. */
	sequences++;initialize(&c,&bus);f=normal();f.sample.temp_decic=440;
	f.sample.cell1_uv=f.sample.cell2_uv=4000000;f.sample.pack_uv=8000000;
	CHECK(at(&c,1,f)==0);struct sm_thermal_state history=c.thermal;
	f.collect_error=-ENODATA;f.source_inhibit=true;f.sample.temp_decic=0;
	CHECK(at(&c,2,f)==-ENODATA&&!memcmp(&history,&c.thermal,sizeof(history))&&c.cycle.attached);
	f.collect_error=0;f.source_inhibit=false;f.sample.fault=1;f.full=true;
	CHECK(at(&c,3,f)==-EIO&&c.latched&&!memcmp(&history,&c.thermal,sizeof(history))&&!c.full_state.full);

	/* True detach resets all dynamic boundaries and pre_shake, not just hold. */
	sequences++;initialize(&c,&bus);f=normal();f.sample.temp_decic=440;
	f.sample.cell1_uv=f.sample.cell2_uv=4000000;f.sample.pack_uv=8000000;
	CHECK(at(&c,1,f)==0&&c.thermal.bounds[5]==420);
	f=(struct frame){.sample={.valid=1,.protection_ok=1}};
	CHECK(at(&c,2,f)==0&&!c.thermal.initialized&&!c.cycle.attached);
	f=normal();f.sample.temp_decic=439;CHECK(at(&c,3,f)==0&&c.thermal.band==4&&c.thermal.bounds[5]==440);

	/* INHIBIT updates fresh thermal history but cannot manufacture recharge. */
	sequences++;initialize(&c,&bus);f=normal();f.full=true;
	CHECK(at(&c,1,f)==0&&c.full_state.full);c.auto_requested=false;
	f.full=false;f.sample.temp_decic=440;f.sample.cell1_uv=f.sample.cell2_uv=4000000;f.sample.pack_uv=8000000;
	CHECK(at(&c,2,f)==0&&c.thermal.band==5&&c.full_state.full&&stopped(&bus));
	CHECK(!c.full_result.recharge&&!c.hold_requested&&c.full_state.recharge_count==0);
	c.auto_requested=true;CHECK(at(&c,3,f)==0&&c.full_holding&&c.full_state.band==5);
	CHECK(c.full_state.recharge_count==1&&!c.full_result.recharge);
	for(unsigned int i=1;i<5;i++)CHECK(at(&c,3+i*5,f)==0&&c.full_holding&&!c.full_result.recharge);
	CHECK(at(&c,28,f)==0&&c.full_result.recharge&&enabled(&bus));

	/* Streaks use the effective band; raw 44 C noise does not reset them. */
	sequences++;initialize(&c,&bus);f=normal();f.sample.temp_decic=440;
	f.sample.cell1_uv=f.sample.cell2_uv=4100000;f.sample.pack_uv=8200000;f.sample.gauge_current_ua=110000;
	for(unsigned int i=0;i<5;i++){f.sample.temp_decic=i%2?439:440;CHECK(at(&c,1+i*5,f)==0&&!c.full_state.full);}
	CHECK(c.full_state.sw_count==5&&c.full_state.band==5);
	f.sample.temp_decic=439;CHECK(at(&c,26,f)==0&&c.full_result.entered_full&&c.full_holding);

	/* First-sample OEM seed removes the old unconditional 2 C recovery. */
	sequences++;struct sm_thermal_state first={0};
	CHECK(sm_thermal_gate(&first,-21,1)&&first.band==SM_THERMAL_LOW&&first.bounds[0]==-20);
	CHECK(!sm_thermal_gate(&first,-20,1)&&first.band==0&&first.bounds[0]==-40);
	CHECK(sm_thermal_gate(&first,-21,1)&&first.band==0); /* immutable raw stop */
	CHECK(!sm_thermal_gate(&first,-20,1));
	first=(struct sm_thermal_state){0};CHECK(sm_thermal_gate(&first,531,1)&&first.bounds[6]==530);
	CHECK(!sm_thermal_gate(&first,529,1)&&first.band==5&&first.bounds[6]==550);
	CHECK(sm_thermal_gate(&first,530,1)&&first.band==5); /* immutable >=53 C */
	CHECK(!sm_thermal_gate(&first,529,1));
