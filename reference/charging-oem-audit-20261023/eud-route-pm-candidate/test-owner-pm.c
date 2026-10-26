static void pm_owner_cases(void)
{
 struct samurai_apsd_owner *o;struct samurai_eud_producer *token=NULL;
 struct platform_device debug={.resource={0x088e0000,0x088e1fff,IORESOURCE_MEM},.has_resource=true};
 setup(true);prepared();wire(true);tick();o=bound_owner;
 assert(o->once.attempted&&mock_apsd_writes==1&&o->route_lease.client);
 assert(!route_prepare(&route_platform.dev));
 assert(route_provider->pm_prepared&&!route_provider->retired&&!atomic_read(&boot_evidence_retired));
 assert(o->route_client&&!o->quarantined&&!o->route_lease.client&&!o->phy.cookie&&!o->dwc_window.cookie&&!host.pm_refs&&!pd->leased);
 assert(samurai_eud_producer_claim(&debug,&token)==-EBUSY&&!token);
 assert(!dwc3_apsd_owner_pause(&dwc,DWC3_APSD_SYSTEM));int count=queued;
 dwc3_apsd_owner_resume(&dwc,DWC3_APSD_SYSTEM);assert(queued==count);
 route_complete(&route_platform.dev);assert(o->work.pending&&!o->blocked&&!o->quarantined);tick();
 assert(mock_apsd_writes==1&&o->once.phase==SAMURAI_APSD_CANCELLED);
 wire(false);tick();wire(true);tick();assert(mock_apsd_writes==2);
 tick();assert(o->once.phase==SAMURAI_APSD_COMPLETE&&!o->route_lease.client);
 teardown();puts("PM owner1 route-first pause restores exact tokens; DWC complete cannot resume early or rerun the old physical epoch");

 setup(true);prepared();o=bound_owner;
 assert(!dwc3_apsd_owner_pause(&dwc,DWC3_APSD_SYSTEM));assert(!route_prepare(&route_platform.dev));count=queued;
 route_complete(&route_platform.dev);assert(queued==count&&o->blocked==DWC3_APSD_SYSTEM);
 dwc3_apsd_owner_resume(&dwc,DWC3_APSD_SYSTEM);assert(o->work.pending&&!o->blocked);tick();
 assert(!mock_apsd_writes&&o->once.phase==SAMURAI_APSD_DETACHED);
 teardown();puts("PM owner2 DWC-first prepare and route-first complete preserve every other lifecycle fence");

 setup(true);wire(true);tick();o=bound_owner;
 assert(o->pd_phase==OWNER_PD_WAIT_FIRST_OFF&&!o->pd_prepared&&!mock_apsd_writes);
 assert(!route_prepare(&route_platform.dev));route_complete(&route_platform.dev);tick();
 assert(o->pd_phase==OWNER_PD_WAIT_FIRST_OFF&&!o->pd_prepared&&!mock_apsd_writes);
 teardown();puts("PM owner3 logical sleep/resume cannot synthesize the first physical off needed to initialize PD5V");

 setup(true);prepared();o=bound_owner;assert(!owner_enter_windows(o));drop_phy_write=4;
 assert(route_prepare(&route_platform.dev)==-EIO&&phy_writes==4&&o->quarantined&&o->phy.cookie&&o->route_lease.client);
 assert(route_prepare(&route_platform.dev)==-EIO&&phy_writes==4);route_complete(&route_platform.dev);assert(phy_writes==4);
 release_phy();dwc3_apsd_owner_unbind(&dwc);
 o->phy.cookie=o->dwc_window.cookie=0;assert(!samurai_eud_route_end(&o->route_lease));assert(!owner_route_release(o));
 o->extra_pm=false;host.pm_refs=0;owner_pd_release(o);bound_owner=NULL;kref_put(&o->ref,owner_free);teardown();
 puts("PM owner4 failed PHY restore stays quarantined through repeated PM calls with no additional writes");

 setup(true);prepared();o=bound_owner;assert(!route_prepare(&route_platform.dev));count=queued;route_live_csr=1;
 route_complete(&route_platform.dev);assert(queued==count&&(o->blocked&DWC3_APSD_ROUTE)&&route_provider->blocked);
 dwc3_apsd_owner_resume(&dwc,DWC3_APSD_SYSTEM);owner_queue(o,0);assert(queued==count&&!mock_apsd_writes);
 teardown();puts("PM owner5 failed live route revalidation cannot restart the actual APSD worker");
}
