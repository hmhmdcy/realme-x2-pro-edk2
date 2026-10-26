static int pm_pauses,pm_resumes,pm_error;
static bool pm_keep_lease,pm_unregister,pm_block;
static int pause_owner(void *context)
{
 struct owner *o=context;assert(!depth);pm_pauses++;
 struct samurai_eud_route_status state;assert(!samurai_eud_route_status(o->client,&state)&&state.paused&&!state.revoked);
 assert(samurai_eud_route_begin(o->client,&(struct samurai_eud_route_lease){0})==-EAGAIN);
 if(o->lease.client)assert(samurai_eud_route_validate(&o->lease)==-ESTALE);
 if(pm_block){pthread_mutex_lock(&event_lock);o->entered=true;pthread_cond_broadcast(&event_changed);while(!o->allow)pthread_cond_wait(&event_changed,&event_lock);pthread_mutex_unlock(&event_lock);}
 if(o->lease.client&&!pm_keep_lease)assert(!samurai_eud_route_end(&o->lease));
 if(pm_unregister){assert(!samurai_eud_route_client_unregister(o->client));o->client=NULL;}
 return pm_error;
}
static void resume_owner(void *context)
{
 struct owner *o=context;assert(!depth);pm_resumes++;
 struct samurai_eud_route_status status;assert(!samurai_eud_route_status(o->client,&status)&&!status.revoked&&!status.paused&&status.exclusive);
 assert(!samurai_eud_route_begin(o->client,&o->lease));assert(!samurai_eud_route_end(&o->lease));
}
static const struct samurai_eud_route_client_ops pm_ops={.get_unless_zero=owner_get,.put=owner_put,.cancel_join=cancel_owner,.pause_join=pause_owner,.resume=resume_owner};
static void setup_pm(struct owner *o)
{
 setup_route(o);pm_pauses=pm_resumes=pm_error=0;pm_keep_lease=pm_unregister=pm_block=false;
 assert(!route_probe(&route_device));assert(!samurai_eud_route_client_register(&route_device.dev,&dwc_device,&pm_ops,o,&o->client));
}
static void *prepare_thread(void *unused){(void)unused;assert(!route_prepare(&route_device.dev));return NULL;}
static int run_provider_pm_cases(void)
{
 struct owner o;struct samurai_eud_producer *token=NULL;struct samurai_eud_route_status state;
 setup_pm(&o);lease_route(&o);u64 generation=route_provider->generation;
 for(unsigned i=0;i<2;i++){
  assert(!route_prepare(&route_device.dev));assert(!o.lease.client&&pm_pauses==(int)i+1&&pm_resumes==(int)i);
  assert(!samurai_eud_route_status(o.client,&state)&&state.paused&&!state.revoked&&state.generation>generation);generation=state.generation;
  assert(samurai_eud_producer_claim(&producer_device,&token)==-EBUSY&&!token);
  int calls=pm_pauses;assert(!route_prepare(&route_device.dev)&&pm_pauses==calls);
  route_complete(&route_device.dev);assert(pm_resumes==(int)i+1&&!atomic_read(&boot_evidence_retired));
  lease_route(&o);
 }
 assert(!samurai_eud_route_end(&o.lease));finish_route(&o,"PM1 two real suspend/resume generations keep exclusion and permit new exact leases without reboot");

 setup_pm(&o);assert(!route_prepare(&route_device.dev));unsigned reads=route_csr_reads;route_live_csr=1;route_complete(&route_device.dev);
 assert(route_csr_reads>reads&&!pm_resumes&&atomic_read(&boot_evidence_retired));assert(!samurai_eud_route_status(o.client,&state)&&state.revoked&&state.pm_error==-EIO);
 assert(samurai_eud_route_begin(o.client,&o.lease)==-ESHUTDOWN);finish_route(&o,"PM2 nonzero live CSR after sleep permanently blocks without route writes or owner resume");

 setup_pm(&o);assert(!route_prepare(&route_device.dev));route_change_on_second=true;route_csr_second=0x01010101;route_complete(&route_device.dev);
 assert(!pm_resumes&&route_provider->evidence_error==-EIO);finish_route(&o,"PM3 a second CSR read changing from zero refuses a false stable-off result");

 setup_pm(&o);assert(!route_prepare(&route_device.dev));((struct samurai_eud_handoff*)published)->checksum^=1;route_complete(&route_device.dev);
 assert(!pm_resumes&&route_provider->evidence_error==-EBADMSG);finish_route(&o,"PM4 invalid post-sleep EFI receipt remains fenced even with live CSR zero");

 setup_pm(&o);lease_route(&o);pm_error=-EIO;assert(route_prepare(&route_device.dev)==-EIO&&pm_pauses==1);
 assert(route_prepare(&route_device.dev)==-EIO&&pm_pauses==1);route_complete(&route_device.dev);assert(!pm_resumes);
 finish_route(&o,"PM5 a failed pause is permanent and is not retried by prepare or complete");

 setup_pm(&o);lease_route(&o);pm_keep_lease=true;assert(route_prepare(&route_device.dev)==-EBUSY&&!pm_resumes);
 assert(!samurai_eud_route_end(&o.lease));finish_route(&o,"PM6 a callback retaining an active lease cannot be accepted as joined");

 setup_pm(&o);pm_unregister=true;assert(!route_prepare(&route_device.dev)&&!o.client&&o.refs==1);route_complete(&route_device.dev);assert(!pm_resumes);
 finish_route(&o,"PM7 callback reference survives unregister inside pause and no stale resume is dispatched");

 setup_pm(&o);assert(!route_prepare(&route_device.dev));route_remove(&route_device);assert(!route_device.dev.data&&!pm_resumes);
 assert(!samurai_eud_route_client_unregister(o.client));o.client=NULL;finish_route(&o,"PM8 real removal while paused retires permanently and releases mapping before debug exclusion");

 setup_route(&o);route_region_fail=true;assert(route_probe(&route_device)==-EBUSY&&!route_provider&&!route_region_held&&!route_mapping_live);finish_route(&o,"PM9 an existing resource owner prevents mapping or MMIO reads");
 setup_route(&o);route_mapping_fail=true;assert(route_probe(&route_device)==-ENOMEM&&!route_region_held&&!route_mapping_live);finish_route(&o,"PM10 mapping failure releases the claimed region before admitting another producer");

 setup_pm(&o);lease_route(&o);pm_block=true;pthread_t thread;assert(!pthread_create(&thread,NULL,prepare_thread,NULL));
 pthread_mutex_lock(&event_lock);while(!o.entered)pthread_cond_wait(&event_changed,&event_lock);pthread_mutex_unlock(&event_lock);
 assert(route_prepare(&route_device.dev)==0&&route_provider->pm_joining&&pm_pauses==1);
 route_complete(&route_device.dev);assert(!pm_resumes&&route_provider->pm_prepared);
 pthread_mutex_lock(&event_lock);o.allow=true;pthread_cond_broadcast(&event_changed);pthread_mutex_unlock(&event_lock);
 assert(!pthread_join(thread,NULL));route_complete(&route_device.dev);assert(pm_resumes==1);
 finish_route(&o,"PM11 real concurrent duplicate prepare/early complete cannot bypass the original in-progress join");
 return 0;
}
