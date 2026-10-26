struct fixture {
 struct imx319 s;struct device dev;struct regulator va,vd,vi;
 struct clk clk;struct gpio_desc gpio;struct v4l2_ctrl vf,hf;
};
static void init(struct fixture *f,bool of) {
 memset(f,0,sizeof(*f));memset(calls,0,sizeof(calls));event_count=0;
 failure_op=-1;failure_at=1;persistent=false;pm_references=0;put_sync_error=0;runtime_active=false;bad_chip_id=false;
 f->dev.sensor=&f->s;f->s.dev=&f->dev;f->s.sd.sensor=&f->s;f->s.sd.ctrl_handler=&f->s;
 f->va.role=0;f->vd.role=1;f->vi.role=2;
 f->s.vana=&f->va;f->s.vdig=&f->vd;f->s.vif=&f->vi;
 f->s.clk=&f->clk;f->s.reset_gpio=&f->gpio;f->s.vflip=&f->vf;f->s.hflip=&f->hf;
 f->s.of_power_resources=of;f->s.identified=!of;f->s.profile=&host_profile;f->s.cur_mode=&host_mode;
}
static void balanced(struct fixture *f) {
 assert(f->s.vana_enabled==(f->va.references==1));
 assert(f->s.vdig_enabled==(f->vd.references==1));
 assert(f->s.vif_enabled==(f->vi.references==1));
 assert(f->s.clock_enabled==f->clk.enabled);
 assert(!f->s.mutex.held);
}
static void off(struct fixture *f) {
 balanced(f);assert(!f->va.references&&!f->vd.references&&!f->vi.references&&!f->clk.enabled);
}
static void fault_gate(struct fixture *f) {
 unsigned int previous=event_count;assert(imx319_power_on(&f->s)==-EIO);
 assert(event_count==previous);balanced(f);
}
static void test_power(void) {
 struct fixture f;
 const unsigned int normal[]={PIN_DEFAULT,GPIO_ASSERT,EN_VANA,EN_VDIG,EN_VIF,CLOCK_ON,
  GPIO_RELEASE,CLOCK_OFF,GPIO_ASSERT,DIS_VIF,DIS_VDIG,DIS_VANA,PIN_SLEEP};
 init(&f,true);assert(!imx319_power_on(&f.s));balanced(&f);
 assert(!f.gpio.asserted);assert(!imx319_power_off(&f.s));off(&f);
 assert(f.gpio.asserted&&!f.s.identified);assert(event_count==sizeof(normal)/sizeof(normal[0]));
 assert(!memcmp(normal,events,sizeof(normal)));cases++;
 for(int cycle=0;cycle<3;cycle++) {
  assert(!imx319_power_on(&f.s));assert(!imx319_power_off(&f.s));off(&f);cases++;
 }
 for(int op=PIN_DEFAULT;op<=GPIO_RELEASE;op++) {
  for(int persist=0;persist<2;persist++) {
   init(&f,true);failure_op=op;persistent=persist;
   assert(imx319_power_on(&f.s)==-EIO);assert(f.s.power_fault);off(&f);fault_gate(&f);cases++;
  }
 }
 const int off_faults[]={GPIO_ASSERT,DIS_VIF,DIS_VDIG,DIS_VANA,PIN_SLEEP};
 for(unsigned int i=0;i<sizeof(off_faults)/sizeof(off_faults[0]);i++) {
  for(int persist=0;persist<2;persist++) {
   init(&f,true);assert(!imx319_power_on(&f.s));
   memset(calls,0,sizeof(calls));failure_op=off_faults[i];persistent=persist;
   assert(imx319_power_off(&f.s)==-EIO);assert(f.s.power_fault&&!f.s.identified);
   balanced(&f);assert(!f.clk.enabled);fault_gate(&f);
   /* A failed regulator disable retains its only real consumer reference. */
   assert(f.vi.references==(off_faults[i]==DIS_VIF));
   assert(f.vd.references==(off_faults[i]==DIS_VDIG));
   assert(f.va.references==(off_faults[i]==DIS_VANA));
   failure_op=-1;assert(!imx319_power_off(&f.s));off(&f);assert(f.s.power_fault);cases++;
  }
 }
 init(&f,true);assert(!imx319_power_on(&f.s));unsigned int prev=event_count;
 assert(imx319_power_on(&f.s)==-EIO&&event_count==prev);assert(!imx319_power_off(&f.s));off(&f);cases++;
 init(&f,false);assert(!imx319_power_on(&f.s));assert(!imx319_power_off(&f.s));assert(!event_count);cases++;
}
static void test_stream(void) {
 struct fixture f;
 for(int of=0;of<2;of++) {
  init(&f,of);assert(!imx319_set_stream(&f.s.sd,0));assert(!event_count);cases++;
  assert(!imx319_set_stream(&f.s.sd,1));assert(f.s.streaming&&pm_references==1);
  assert(f.vf.grabbed&&f.hf.grabbed);unsigned int prev=event_count;
  assert(!imx319_set_stream(&f.s.sd,1)&&event_count==prev);cases++;
  assert(!imx319_set_stream(&f.s.sd,0));assert(!f.s.streaming&&!pm_references);
  assert(!f.vf.grabbed&&!f.hf.grabbed);prev=event_count;
  assert(!imx319_set_stream(&f.s.sd,0)&&event_count==prev);off(&f);cases++;
  init(&f,of);f.s.removing=true;assert(imx319_set_stream(&f.s.sd,1)==-ENODEV);
  assert(!event_count&&!pm_references);cases++;
  init(&f,of);f.s.power_fault=true;assert(imx319_set_stream(&f.s.sd,1)==-EIO);
  assert(!event_count&&!pm_references);cases++;
  init(&f,of);failure_op=PM_GET;assert(imx319_set_stream(&f.s.sd,1)==-EIO);
  assert(!f.s.streaming&&!pm_references&&!calls[START]&&!calls[PM_PUT_SYNC]&&!calls[PM_PUT]);off(&f);cases++;
  init(&f,of);failure_op=START;assert(imx319_set_stream(&f.s.sd,1)==-EIO);
  assert(!f.s.streaming&&!pm_references&&!f.vf.grabbed&&!f.hf.grabbed);
  assert(calls[STOP]==(unsigned int)of&&calls[PM_PUT_SYNC]==(unsigned int)of);
  assert(calls[PM_PUT]==(unsigned int)!of&&!f.s.power_fault);off(&f);cases++;
  init(&f,of);assert(!imx319_set_stream(&f.s.sd,1));failure_op=STOP;
  assert(imx319_set_stream(&f.s.sd,0)==(of?-EIO:0));assert(!f.s.streaming&&!pm_references);
  assert(f.s.power_fault==(bool)of);off(&f);prev=event_count;
  assert(!imx319_set_stream(&f.s.sd,0)&&event_count==prev);cases++;
 }
 for(int op=PIN_DEFAULT;op<=GPIO_RELEASE;op++) {
  init(&f,true);failure_op=op;assert(imx319_set_stream(&f.s.sd,1)==-EIO);
  assert(!f.s.streaming&&!pm_references&&!calls[START]);off(&f);cases++;
 }
 for(int op=DIS_VIF;op<=PIN_SLEEP;op++) {
  init(&f,true);assert(!imx319_set_stream(&f.s.sd,1));failure_op=op;
  assert(imx319_set_stream(&f.s.sd,0)==-EIO);assert(!f.s.streaming&&!pm_references&&f.s.power_fault);
  assert(!f.vf.grabbed&&!f.hf.grabbed);balanced(&f);unsigned int prev=event_count;
  assert(imx319_set_stream(&f.s.sd,1)==-EIO&&event_count==prev);cases++;
 }
 init(&f,true);assert(!imx319_set_stream(&f.s.sd,1));put_sync_error=-EIO;
 assert(imx319_set_stream(&f.s.sd,0)==-EIO);assert(f.s.power_fault&&!pm_references);off(&f);cases++;
 init(&f,true);failure_op=START;put_sync_error=-EIO;
 assert(imx319_set_stream(&f.s.sd,1)==-EIO);assert(f.s.power_fault&&!pm_references);off(&f);cases++;
 for(int mismatch=0;mismatch<2;mismatch++) {
  init(&f,true);if(mismatch)bad_chip_id=true;else failure_op=IDENTIFY;
  assert(imx319_set_stream(&f.s.sd,1)==-EIO);assert(!f.s.streaming&&!pm_references);
  assert(!calls[REG_WRITE]&&!calls[STOP]&&!calls[START]&&!calls[CTRL_SETUP]);off(&f);cases++;
 }
 for(unsigned int index=1;index<=308;index++) {
  init(&f,true);failure_op=REG_WRITE;failure_at=index;
  assert(imx319_set_stream(&f.s.sd,1)==-EIO);
  assert(calls[REG_WRITE]==index&&calls[STOP]==1&&!calls[START]&&!pm_references&&!f.s.streaming);
  off(&f);cases++;
 }
 init(&f,true);failure_op=CTRL_SETUP;assert(imx319_set_stream(&f.s.sd,1)==-EIO);
 assert(calls[REG_WRITE]==308&&calls[STOP]==1&&!calls[START]&&!pm_references);off(&f);cases++;
}
int main(void) {
 test_power();test_stream();
 printf("{\"passed\":true,\"cases\":%u}\n",cases);return 0;
}
