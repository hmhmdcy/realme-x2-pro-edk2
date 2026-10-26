struct fixture {
 struct pm8008_imx319_lab_state s;struct device dev;struct regmap primary,secondary;
 struct pm8008_lab_rail l1,l4;struct regulator_dev r1,r4;
};
static int assert_p(void *cookie) {
 struct fixture *f=cookie;assert(f->s.lock.held);reset_calls++;
 if(reset_failure)return reset_failure;
 for(unsigned int i=0;i<7;i++)f->secondary.registers[0x4046+i*0x100]=0;
 f->primary.registers[0x950]=0;return 0;
}
static void init(struct fixture *f,bool original_global) {
 memset(f,0,sizeof(*f));f->s.magic=PM8008_IMX319_LAB_MAGIC;
 f->s.parent=&f->dev;f->s.primary=&f->primary;f->s.secondary=&f->secondary;
 f->s.mask=PM8008_IMX319_LAB_MASK;f->s.ready=true;f->s.claimed=true;
 f->s.assert_p_reset=assert_p;f->s.reset_cookie=f;
 f->s.global_initialized=true;f->s.global_original=original_global;
 f->primary.owner=f->secondary.owner=&f->s;f->primary.primary=true;
 f->primary.registers[0x950]=original_global;f->secondary.ready_after=1;
 f->l1=(struct pm8008_lab_rail){.state=&f->s,.index=0,.target_uV=1104000,.step_rate=38400};
 f->l4=(struct pm8008_lab_rail){.state=&f->s,.index=3,.target_uV=2800000,.step_rate=38400};
 f->r1.rail=&f->l1;f->r4.rail=&f->l4;
 put_unaligned_le16(1104,f->secondary.registers+0x4040);
 put_unaligned_le16(2800,f->secondary.registers+0x4340);
 io_count=write_count=fail_at=fail_mode=delay_count=last_delay=0;persistent=false;
 reset_calls=0;reset_failure=0;
}
static void off(struct fixture *f) {
 assert(!(f->secondary.registers[0x4046]&0x80));
 assert(!(f->secondary.registers[0x4346]&0x80));
}
static void blocked_after_fault(struct fixture *f) {
 assert(f->s.fault);unsigned int writes=write_count,calls=io_count;
 assert(pm8008_lab_enable(&f->r1)==-EIO);
 assert(pm8008_lab_set_voltage_sel(&f->r4,162)==-EIO);
 assert(pm8008_lab_is_enabled(&f->r1)==-EIO);
 assert(write_count==writes&&io_count==calls);
}
int main(void) {
 unsigned int cases=0,enable_calls,set_calls,disable_calls;
 struct fixture *f=calloc(1,sizeof(*f));assert(f);
 for(unsigned int global=0;global<2;global++) {
  init(f,global);assert(pm8008_lab_get_voltage(&f->r1)==1104000);
  assert(pm8008_lab_set_voltage_sel(&f->r1,72)==0);
  assert(pm8008_lab_set_voltage_sel(&f->r4,162)==0);
  assert(pm8008_lab_enable(&f->r4)==0);assert(last_delay==93);
  assert(pm8008_lab_enable(&f->r1)==0);assert(last_delay==49);
  assert(f->s.enabled_mask==9&&f->s.attempted_mask==9);
  assert(pm8008_lab_is_enabled(&f->r1)==1);
  assert(pm8008_lab_disable(&f->r1)==0);
  assert(f->s.enabled_mask==8&&f->primary.registers[0x950]==1);
  assert(pm8008_lab_disable(&f->r4)==0);off(f);
  assert(f->primary.registers[0x950]==global&&!f->s.fault);cases++;
 }
 init(f,false);assert(pm8008_lab_enable(&f->r1)==0);enable_calls=io_count;cases++;
 for(unsigned int mode=0;mode<3;mode++)for(unsigned int at=1;at<=enable_calls;at++) {
  init(f,false);fail_at=at;fail_mode=mode;
  assert(pm8008_lab_enable(&f->r1)<0);off(f);assert(!f->s.attempted_mask&&!f->s.enabled_mask);
  assert(reset_calls==0);blocked_after_fault(f);
  /* Child cleanup/reprobe cannot reset the parent fault. */
  fail_at=0;pm8008_lab_cleanup(&f->s);assert(!f->s.claimed&&!f->s.ready&&f->s.fault);
  f->s.removing=false;f->s.ready=true;blocked_after_fault(f);cases++;
 }
 for(unsigned int reset_fail=0;reset_fail<2;reset_fail++)
 for(unsigned int mode=0;mode<3;mode++)for(unsigned int at=1;at<=enable_calls;at++) {
  init(f,false);fail_at=at;fail_mode=mode;persistent=true;
  reset_failure=reset_fail?-EIO:0;
  assert(pm8008_lab_enable(&f->r1)<0);blocked_after_fault(f);
  if(f->secondary.registers[0x4046]&0x80)assert(f->s.attempted_mask&1);
  assert(reset_calls<=1);
  cases++;
 }
 init(f,false);assert(pm8008_lab_set_voltage_sel(&f->r1,72)==0);set_calls=io_count;
 for(unsigned int mode=0;mode<3;mode++)for(unsigned int at=1;at<=set_calls;at++) {
  init(f,false);put_unaligned_le16(1000,f->secondary.registers+0x4040);fail_at=at;fail_mode=mode;
  assert(pm8008_lab_set_voltage_sel(&f->r1,72)<0);off(f);blocked_after_fault(f);cases++;
 }
 init(f,false);assert(pm8008_lab_enable(&f->r1)==0);io_count=0;
 assert(pm8008_lab_disable(&f->r1)==0);disable_calls=io_count;
 for(unsigned int mode=0;mode<3;mode++)for(unsigned int at=1;at<=disable_calls;at++) {
  init(f,false);assert(pm8008_lab_enable(&f->r1)==0);io_count=0;fail_at=at;fail_mode=mode;
  int disabled=pm8008_lab_disable(&f->r1);
  assert(f->s.reset_held?disabled==0:disabled<0);assert(f->s.fault);blocked_after_fault(f);
  if(f->secondary.registers[0x4046]&0x80)assert(f->s.attempted_mask&1);
  cases++;
 }
 /* VANA count was acquired, VDIG failed: reset isolation permits a balanced VANA put. */
 for(unsigned int failed_reset=0;failed_reset<2;failed_reset++) {
  init(f,false);assert(pm8008_lab_enable(&f->r4)==0);
  io_count=0;fail_at=1;persistent=true;reset_failure=failed_reset?-EIO:0;
  assert(pm8008_lab_enable(&f->r1)==-EIO);
  int ret=pm8008_lab_disable(&f->r4);
  assert(failed_reset?ret<0:ret==0);assert(reset_calls==1);
  if(!failed_reset){assert(f->s.reset_held);off(f);unsigned int count=io_count;
   assert(pm8008_lab_disable(&f->r4)==0);assert(io_count==count);}
  pm8008_lab_cleanup(&f->s);assert(reset_calls==1);cases++;
 }
 init(f,false);f->secondary.ready_after=11;
 assert(pm8008_lab_enable(&f->r4)==-ETIME);assert(delay_count==10);off(f);blocked_after_fault(f);cases++;
 for(unsigned int ready=1;ready<=10;ready++) {
  init(f,false);f->secondary.ready_after=ready;
  assert(pm8008_lab_enable(&f->r4)==0&&delay_count==ready);
  assert(pm8008_lab_disable(&f->r4)==0);off(f);cases++;
 }
 for(unsigned int original=0;original<2;original++)for(unsigned int unexpected=0;unexpected<7;unexpected++){
  init(f,original);f->secondary.registers[0x4046+unexpected*0x100]=0x80;
  assert(pm8008_lab_enable(&f->r1)==-EBUSY&&f->s.fault&&write_count==0);cases++;
  init(f,original);f->secondary.registers[0x4146]=0x80;
  mutex_lock(&f->s.lock);assert(pm8008_lab_restore_global(&f->s)==-EBUSY);mutex_unlock(&f->s.lock);
  assert(f->s.fault&&f->primary.registers[0x950]==original&&write_count==0);cases++;
 }
 for(unsigned int value=2;value<256;value++){
  init(f,false);f->primary.registers[0x950]=value;
  assert(pm8008_lab_enable(&f->r1)==-EINVAL&&write_count==0);off(f);blocked_after_fault(f);cases++;
 }
 init(f,false);f->s.ready=false;assert(pm8008_lab_enable(&f->r1)==-EAGAIN&&write_count==0);cases++;
 init(f,false);f->s.removing=true;assert(pm8008_lab_enable(&f->r1)==-EIO&&write_count==0);cases++;
 init(f,false);assert(pm8008_lab_set_voltage_sel(&f->r1,71)==-EINVAL&&io_count==0);cases++;
 init(f,false);f->l1.index=1;assert(pm8008_lab_enable(&f->r1)==-EINVAL&&io_count==0);cases++;
 init(f,false);assert(pm8008_lab_enable(&f->r1)==0);
 assert(pm8008_lab_set_voltage_sel(&f->r1,72)==-EBUSY);blocked_after_fault(f);
 pm8008_lab_cleanup(&f->s);off(f);assert(f->s.fault&&!f->s.claimed);cases++;
 free(f);printf("{\"cases\":%u,\"enable_api_points\":%u,\"set_api_points\":%u,\"disable_api_points\":%u,\"passed\":true}\n",cases,enable_calls,set_calls,disable_calls);
 return 0;
}
