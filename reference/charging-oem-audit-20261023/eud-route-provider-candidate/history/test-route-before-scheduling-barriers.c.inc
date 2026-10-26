static struct platform_device route_device,producer_device;
static struct device dwc_device,wrong_device;
static pthread_mutex_t event_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t event_changed=PTHREAD_COND_INITIALIZER;
struct owner {
 struct samurai_eud_route_client *client;
 struct samurai_eud_route_lease lease;
 int refs,calls,error;
 bool accept,end,unregister_inside,block,entered,allow,join_worker;
 pthread_t worker;
};
static bool owner_get(void*ctx){struct owner*o=ctx;assert(!depth);if(!o->accept)return false;o->refs++;return true;}
static void owner_put(void*ctx){struct owner*o=ctx;assert(!depth&&o->refs>1);o->refs--;}
static int cancel_owner(void*ctx)
{
 struct owner*o=ctx;assert(!depth&&o->refs==2);o->calls++;
 assert(samurai_eud_route_validate(&o->lease)==-ESTALE||!o->lease.client);
 struct samurai_eud_producer *attempt=NULL;assert(samurai_eud_producer_claim(&producer_device,&attempt)==-EBUSY&&!attempt);
 if(o->block){pthread_mutex_lock(&event_lock);o->entered=true;pthread_cond_broadcast(&event_changed);while(!o->allow)pthread_cond_wait(&event_changed,&event_lock);pthread_mutex_unlock(&event_lock);}
 if(o->join_worker)assert(!pthread_join(o->worker,NULL));
 if(o->end&&o->lease.client)assert(!samurai_eud_route_end(&o->lease));
 if(o->unregister_inside){assert(!samurai_eud_route_client_unregister(o->client));o->client=NULL;assert(o->refs==2);}
 return o->error;
}
static const struct samurai_eud_route_client_ops owner_ops={owner_get,owner_put,cancel_owner};
static void setup_route(struct owner*o)
{
 assert(!route_provider&&!producer&&!atomic_load(&kernel_allocations)&&!atomic_read(&route_exclusive));
 reset();boot_record();producer_ever_granted=early_producer_seen=false;atomic_set(&boot_evidence_retired,0);route_binding=0;
 memset(o,0,sizeof(*o));o->accept=o->end=true;o->refs=1;
 route_node=(struct device_node){"realme,rmx1931-eud-off-route",true,0,0,0,false,false};
 hardware_node=(struct device_node){"qcom,sm8150-eud-com",false,0,EUD_START,EUD_BYTES,false,false};
 consumer_node=(struct device_node){"snps,dwc3",true,0,DWC_START,0xcd00,false,false};
 chosen_node=(struct device_node){0};of_chosen=&chosen_node;acpi_disabled=1;saved_command_line="console=tty0 loglevel=7";
 route_device=(struct platform_device){.dev={&route_node,NULL,0,true}};
 producer_device=(struct platform_device){.dev={&hardware_node,NULL,0,true},.resource={EUD_START,EUD_START+EUD_BYTES-1,IORESOURCE_MEM},.has_resource=true};
 dwc_device=(struct device){&consumer_node,NULL,0,true};wrong_device=(struct device){&hardware_node,NULL,0,true};
}
static void publish_route(struct owner*o)
{assert(!route_probe(&route_device));assert(!samurai_eud_route_client_register(&route_device.dev,&dwc_device,&owner_ops,o,&o->client)&&o->refs==2);}
static void lease_route(struct owner*o){assert(!samurai_eud_route_begin(o->client,&o->lease));assert(!samurai_eud_route_validate(&o->lease));}
static void finish_route(struct owner*o,const char*name)
{
 if(route_device.dev.data)route_remove(&route_device);
 if(o->client){assert(!samurai_eud_route_client_unregister(o->client));o->client=NULL;}
 assert(!route_provider&&!producer&&!atomic_load(&kernel_allocations)&&!atomic_read(&route_exclusive));
 assert(o->refs==1&&!route_device.dev.refs&&!producer_device.dev.refs&&!dwc_device.refs&&!hardware_node.refs&&!consumer_node.refs);
 printf("route: %s\n",name);
}
static void *remove_route_thread(void*unused){(void)unused;route_remove(&route_device);return NULL;}
static void *retire_route_thread(void*data){assert(!route_retire(data));return NULL;}
static void *owned_worker(void*data)
{struct owner*o=data;assert(!samurai_eud_route_validate(&o->lease));pthread_mutex_lock(&event_lock);while(!o->allow)pthread_cond_wait(&event_changed,&event_lock);pthread_mutex_unlock(&event_lock);return NULL;}
int main(void)
{
 assert(!prior_handoff_tests());assert(!route_init());struct owner o;struct samurai_eud_producer *token;
 setup_route(&o);publish_route(&o);lease_route(&o);struct samurai_eud_route_lease copied=o.lease;
 assert(samurai_eud_route_validate(&copied)==-ESTALE);assert(samurai_eud_route_client_unregister(o.client)==-EBUSY);
 assert(samurai_eud_producer_claim(&producer_device,&token)==-EBUSY&&!token);
 assert(!samurai_eud_route_end(&o.lease));finish_route(&o,"actual paired handoff, device/client identity, exact lease address and producer exclusion");

 setup_route(&o);assert(!samurai_eud_producer_claim(&producer_device,&token)&&token);samurai_eud_producer_release(token);
 assert(route_probe(&route_device)==-EBUSY&&!route_provider&&!atomic_read(&route_exclusive));finish_route(&o,"released/failed producer attempts retain current-boot history and cannot reuse EFI-off evidence");

 setup_route(&o);assert(!samurai_eud_earlycon_claim(EUD_START));assert(route_probe(&route_device)==-EBUSY);
 finish_route(&o,"actual early entry permanently records possible hardware use before late route publication");

 const char*bad[]={"earlycon=eud,mmio,0x88e0000", "\"earlycon=eud,mmio,0x88e0000\"", "console=uart8250,mmio,0x88e0000", "console=eud", "console=ttyEUD0", "earlyprintk"};
 for(unsigned int i=0;i<sizeof(bad)/sizeof(*bad);i++){setup_route(&o);saved_command_line=(char*)bad[i];assert(route_probe(&route_device)==-EOPNOTSUPP&&!route_provider);}
 setup_route(&o);saved_command_line="console=tty0 -- earlycon=eud";publish_route(&o);finish_route(&o,"real kernel next_arg handles quoted early/console aliases and -- without inventing an argument parser");

 setup_route(&o);chosen_node.stdout=true;assert(route_probe(&route_device)==-EOPNOTSUPP);
 setup_route(&o);acpi_disabled=0;assert(route_probe(&route_device)==-EOPNOTSUPP);
 setup_route(&o);hardware_node.available=true;assert(route_probe(&route_device)==-EINVAL&&!hardware_node.refs&&!consumer_node.refs);
 setup_route(&o);consumer_node.start++;assert(route_probe(&route_device)==-EINVAL);
 setup_route(&o);((struct samurai_eud_handoff*)published)->checksum^=1;assert(route_probe(&route_device)==-EBADMSG&&!route_provider&&!atomic_read(&route_exclusive));
 finish_route(&o,"ACPI/stdout, live debug node, wrong physical controller and invalid firmware evidence never publish ownership");

 setup_route(&o);assert(!route_probe(&route_device));assert(samurai_eud_route_client_register(&route_device.dev,&wrong_device,&owner_ops,&o,&o.client)==-EXDEV&&o.refs==1);
 assert(!samurai_eud_route_client_register(&route_device.dev,&dwc_device,&owner_ops,&o,&o.client));lease_route(&o);
 ((struct samurai_eud_handoff*)published)->checksum^=1;assert(samurai_eud_route_validate(&o.lease)==-EBADMSG&&atomic_read(&boot_evidence_retired));
 assert(!samurai_eud_route_end(&o.lease));finish_route(&o,"fresh evidence errors fence the actual generation and preserve the error without self-join");

 setup_route(&o);publish_route(&o);lease_route(&o);assert(!route_prepare(&route_device.dev));
 struct samurai_eud_route_status status;assert(!samurai_eud_route_status(o.client,&status)&&status.revoked&&status.exclusive&&!o.lease.client);
 assert(samurai_eud_route_begin(o.client,&o.lease)==-ESHUTDOWN);finish_route(&o,"PM retires and joins but keeps producer exclusion; no unproved resume-time evidence rearm");

 setup_route(&o);publish_route(&o);lease_route(&o);o.end=false;o.error=-EIO;route_remove(&route_device);
 assert(route_provider&&atomic_read(&route_exclusive)&&o.client&&o.lease.client);assert(samurai_eud_producer_claim(&producer_device,&token)==-EBUSY);
 assert(!samurai_eud_route_end(&o.lease));assert(!samurai_eud_route_client_unregister(o.client));o.client=NULL;
 finish_route(&o,"failed remove retains real publication/context; later joined end/unregister releases exclusion without clearing the error");

 setup_route(&o);publish_route(&o);lease_route(&o);o.unregister_inside=true;route_remove(&route_device);
 assert(!o.client&&o.refs==1&&!route_provider);finish_route(&o,"actual callback pin survives unregister inside cancel_join through final callback return");

 setup_route(&o);publish_route(&o);lease_route(&o);o.block=true;pthread_t remove_thread,wait_thread;
 struct samurai_eud_route_provider *p=route_provider;assert(!pthread_create(&remove_thread,NULL,remove_route_thread,NULL));
 pthread_mutex_lock(&event_lock);while(!o.entered)pthread_cond_wait(&event_changed,&event_lock);pthread_mutex_unlock(&event_lock);
 assert(!pthread_create(&wait_thread,NULL,retire_route_thread,p));assert(samurai_eud_producer_claim(&producer_device,&token)==-EBUSY);
 pthread_mutex_lock(&event_lock);o.allow=true;pthread_cond_broadcast(&event_changed);pthread_mutex_unlock(&event_lock);
 assert(!pthread_join(remove_thread,NULL)&&!pthread_join(wait_thread,NULL));finish_route(&o,"real concurrent retirement waiters keep completion storage and producer fence alive through the original callback");

 setup_route(&o);publish_route(&o);lease_route(&o);o.block=o.join_worker=true;assert(!pthread_create(&o.worker,NULL,owned_worker,&o));
 assert(!pthread_create(&remove_thread,NULL,remove_route_thread,NULL));pthread_mutex_lock(&event_lock);while(!o.entered)pthread_cond_wait(&event_changed,&event_lock);pthread_mutex_unlock(&event_lock);
 assert(samurai_eud_producer_claim(&producer_device,&token)==-EBUSY);
 pthread_mutex_lock(&event_lock);o.allow=true;pthread_cond_broadcast(&event_changed);pthread_mutex_unlock(&event_lock);
 assert(!pthread_join(remove_thread,NULL));assert(!samurai_eud_producer_claim(&producer_device,&token));samurai_eud_producer_release(token);
 finish_route(&o,"real worker join completes before a functional EUD producer can be granted after removal");

 setup_route(&o);publish_route(&o);lease_route(&o);assert(samurai_eud_earlycon_claim(EUD_START)==-EBUSY&&!early_producer_seen);
 assert(samurai_eud_earlycon_claim(EUD_START+0x100)==-EINVAL);assert(!samurai_eud_earlycon_claim(0x12340000));
 assert(!samurai_eud_route_end(&o.lease));finish_route(&o,"active owner excludes late EUD early entry; wrong overlapping base rejects and unrelated hardware remains separate");
 reset();puts("12 actual route-provider groups passed");return 0;
}
