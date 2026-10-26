struct fixture {
 struct device dev;struct device_node parent,regs,ldo[3];
 struct property parent_props[4],props[3][10];unsigned char voltage[3][2][4];
};
static unsigned int cases;
static void u32bytes(unsigned char *p,u32 value) { p[0]=value>>24;p[1]=value>>16;p[2]=value>>8;p[3]=value; }
static void prop(struct property *p,const char *name,const void *value,int length,struct property *next) {
 p->name=name;p->value=value;p->length=length;p->next=next;
}
static void init(struct fixture *f) {
 memset(f,0,sizeof(*f));f->dev.of_node=&f->parent;f->parent.basename="pmic";f->parent.compatible="qcom,pm8008";
 f->parent.children=&f->regs;f->regs.basename="regulators";f->regs.children=&f->ldo[0];
 prop(&f->parent_props[0],"realme,imx319-power-lab",NULL,0,&f->parent_props[1]);
 prop(&f->parent_props[1],"name","pmic",5,NULL);f->parent.properties=&f->parent_props[0];
 for(int i=0;i<3;i++) {
  struct device_node *n=&f->ldo[i];n->basename=i==0?"ldo1":i==1?"ldo4":"ldo7";n->available=true;
  n->next=i==0?&f->ldo[1]:NULL;n->properties=f->props[i];
  u32bytes(f->voltage[i][0],i==0?1100000:2800000);u32bytes(f->voltage[i][1],i==0?1104000:2800000);
  prop(&f->props[i][0],"name",n->basename,5,&f->props[i][1]);
  prop(&f->props[i][1],"regulator-name",i==0?"cam-rear-vdig":"cam-rear-vana",14,&f->props[i][2]);
  prop(&f->props[i][2],"regulator-min-microvolt",f->voltage[i][0],4,&f->props[i][3]);
  prop(&f->props[i][3],"regulator-max-microvolt",f->voltage[i][1],4,&f->props[i][4]);
  prop(&f->props[i][4],"phandle",f->voltage[i][0],4,NULL);
 }
}
static void check(struct fixture *f,int expected) {
 assert(pm8008_lab_validate_dt(&f->dev)==expected);
 assert(f->parent.refs==0&&f->regs.refs==0);
 for(int i=0;i<3;i++)assert(f->ldo[i].refs==0);
 cases++;
}
int main(void) {
 struct fixture f;
 init(&f);check(&f,0);
 init(&f);for(int i=0;i<2;i++)f.ldo[i].properties=&f.props[i][1];check(&f,0);
 for(int rail=0;rail<2;rail++) {
  init(&f);prop(&f.props[rail][5],"linux,phandle",f.voltage[rail][0],4,NULL);f.props[rail][4].next=&f.props[rail][5];check(&f,0);
  for(int length=0;length<=9;length++)if(length!=5) {
   init(&f);f.props[rail][0].length=length;check(&f,-EINVAL);
  }
  const char *bad_names[]={"ldo7","ldo0","LDO1","ldo4","ldo1","ldo", "ldo1x"};
  for(unsigned int i=0;i<sizeof(bad_names)/sizeof(bad_names[0]);i++) {
   if(!strcmp(bad_names[i],rail?"ldo4":"ldo1"))continue;
   init(&f);f.props[rail][0].value=bad_names[i];f.props[rail][0].length=(int)strlen(bad_names[i])+1;check(&f,-EINVAL);
  }
  init(&f);f.props[rail][0].value=NULL;check(&f,-EINVAL);
  const char malformed[5]={'l','d','o','1','x'};
  init(&f);f.props[rail][0].value=malformed;check(&f,-EINVAL);
  const char *unknown[]={"regulator-always-on","regulator-boot-on","regulator-pull-down","regulator-enable-ramp-delay",
   "status","vin-supply","vdd-supply","regulator-allow-set-load","regulator-initial-mode"};
  for(unsigned int i=0;i<sizeof(unknown)/sizeof(unknown[0]);i++) {
   init(&f);prop(&f.props[rail][5],unknown[i],NULL,0,NULL);f.props[rail][4].next=&f.props[rail][5];check(&f,-EINVAL);
  }
  init(&f);u32bytes(f.voltage[rail][0],1000000);check(&f,-EINVAL);
  init(&f);u32bytes(f.voltage[rail][1],3300000);check(&f,-EINVAL);
  init(&f);f.props[rail][2].length=3;check(&f,-EINVAL);
  init(&f);f.props[rail][3].value=NULL;check(&f,-EINVAL);
  init(&f);f.props[rail][1].next=&f.props[rail][3];check(&f,-EINVAL);
  init(&f);f.props[rail][2].next=&f.props[rail][4];check(&f,-EINVAL);
  init(&f);f.ldo[rail].available=false;check(&f,-EINVAL);
 }
 init(&f);f.dev.of_node=NULL;check(&f,-EINVAL);
 init(&f);f.parent.compatible="qcom,other";check(&f,-EINVAL);
 init(&f);f.parent.properties=&f.parent_props[1];check(&f,-EINVAL);
 init(&f);f.parent.children=NULL;check(&f,-EINVAL);
 init(&f);f.regs.children=NULL;check(&f,-EINVAL);
 init(&f);f.ldo[0].next=NULL;check(&f,-EINVAL);
 init(&f);f.ldo[1].basename="ldo1";check(&f,-EINVAL);
 init(&f);f.ldo[1].next=&f.ldo[2];check(&f,-EINVAL);
 init(&f);prop(&f.parent_props[2],"vdd-l1-l2-supply",NULL,0,NULL);f.parent_props[1].next=&f.parent_props[2];check(&f,-EINVAL);
 printf("{\"passed\":true,\"cases\":%u}\n",cases);return 0;
}
