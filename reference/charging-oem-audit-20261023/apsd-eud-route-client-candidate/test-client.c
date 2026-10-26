int main(void)
{
 (void)qcom_snps_hsphy_shutdown; /* Kept from the reused whole-provider fixture. */
 struct samurai_apsd_owner*o;struct samurai_eud_producer*token=NULL;
 struct platform_device debug={.resource={0x088e0000,0x088e1fff,IORESOURCE_MEM},.has_resource=true};
 setup(true);config_route_client=false;tick();assert(bound_owner->primary_error==-EOPNOTSUPP&&!reads&&!writes&&!phy_writes&&!analog_calls&&!mock_apsd_writes);teardown();
 puts("1 disabled route client refuses before PHY/PD/analog/command access");

 setup(true);route_remove(&route_platform);tick();assert(bound_owner->work.pending&&!bound_owner->route_client&&!reads&&!writes&&!analog_calls);
 assert(!route_probe(&route_platform));prepared();assert(bound_owner->route_client&&bound_owner->ref.refs==4);teardown();
 puts("2 missing actual route publication defers; real provider/client binds before PD preparation");

 setup(true);prepared();wire(true);tick();o=bound_owner;
 assert(mock_apsd_writes==1&&o->once.phase==SAMURAI_APSD_WAIT_DONE&&o->route_lease.client&&o->phy.cookie&&o->dwc_window.halted);
 struct samurai_eud_route_lease copied=o->route_lease;assert(samurai_eud_route_validate(&copied)==-ESTALE);
 tick();assert(o->once.phase==SAMURAI_APSD_COMPLETE&&!o->route_lease.client&&!o->phy.cookie&&!o->dwc_window.cookie&&!host.pm_refs);
 assert(phy_writes==6&&dwc_ends==1&&!eud_ends&&mock_apsd_writes==1);tick();assert(mock_apsd_writes==1);teardown();
 puts("3 real route lease plus PD/PHY final validation permits one modeled transfer and exact reverse restoration");

 setup(true);prepared();boundary_mode=1;wire(true);tick();o=bound_owner;
 assert(o->once.attempted&&o->primary_error==-EBADMSG&&!mock_apsd_writes&&!o->route_lease.client&&!host.pm_refs);
 assert(atomic_read(&boot_evidence_retired)&&route_provider->evidence_error==-EBADMSG);teardown();
 puts("4 fresh EFI evidence failure at final callback consumes the epoch but blocks the modeled command");

 setup(true);prepared();o=bound_owner;assert(!owner_enter_windows(o));route_remove(&route_platform);
 assert(o->quarantined&&(o->blocked&DWC3_APSD_ROUTE)&&!o->route_client&&!o->route_lease.client&&!o->phy.cookie&&!host.pm_refs&&!pd->leased);
 assert(phy_writes==6&&dwc_ends==1&&!dwc_cancels&&!eud_ends&&!route_provider);
 assert(!samurai_eud_producer_claim(&debug,&token)&&token);samurai_eud_producer_release(token);token=NULL;
 int n=queued;dwc3_apsd_owner_resume(&dwc,DWC3_APSD_SYSTEM);owner_queue(o,0);assert(queued==n);teardown();
 puts("5 route-only removal joins and normally restores a live gadget before debug ownership can resume");

 setup(true);prepared();o=bound_owner;assert(!owner_enter_windows(o));dwc3_apsd_owner_stop_pre(&dwc);route_remove(&route_platform);
 assert(route_provider&&route_provider->join_error==-EBUSY&&o->route_lease.client&&o->dwc_window.cookie&&o->extra_pm&&!dwc_ends);
 assert(samurai_eud_producer_claim(&debug,&token)==-EBUSY&&!token);
 dwc3_apsd_owner_stop_post(&dwc);assert(!o->route_lease.client&&!host.pm_refs);dwc3_apsd_owner_unbind(&dwc);
 assert(!bound_owner&&!route_provider);assert(!samurai_eud_producer_claim(&debug,&token));samurai_eud_producer_release(token);token=NULL;teardown();
 puts("6 UDC retirement retains route exclusion until actual shutdown/end and later unregister acknowledgement");

 setup(true);prepared();o=bound_owner;assert(!owner_enter_windows(o));drop_phy_write=4;route_remove(&route_platform);
 assert(o->quarantined&&route_provider&&route_provider->join_error==-EIO&&o->route_lease.client&&o->phy.cookie&&phy_writes==4&&!dwc_ends);
 assert(samurai_eud_producer_claim(&debug,&token)==-EBUSY&&!token);release_phy();dwc3_apsd_owner_unbind(&dwc);
 assert(bound_owner==o&&!o->dwc&&o->route_client&&o->route_lease.client&&phy_writes==4);
 /* Test-fixture destruction of powered-off orphan resources only. This is
  * neither a production retry nor a successful hardware restore receipt. */
 o->phy.cookie=o->dwc_window.cookie=0;assert(!samurai_eud_route_end(&o->route_lease));assert(!owner_route_release(o));
 o->extra_pm=false;host.pm_refs=0;owner_pd_release(o);bound_owner=NULL;kref_put(&o->ref,owner_free);teardown();
 puts("7 failed PHY restoration retains real route publication and owner tombstone without another MMIO write");

 setup(true);prepared();unbind_on_route_unlock=true;route_remove(&route_platform);
 assert(!bound_owner&&!route_provider&&!route_platform.dev.refs&&!host.refs&&!pd->leased);teardown();
 puts("8 actual route callback pin survives DWC unbind between retirement publication and callback dispatch");

 setup(true);prepared();wire(true);tick();o=bound_owner;assert(o->route_lease.client&&mock_apsd_writes==1);
 assert(!route_prepare(&route_platform.dev));assert(atomic_read(&boot_evidence_retired)&&route_provider->retired&&!o->route_client&&o->quarantined&&!o->route_lease.client&&!host.pm_refs);
 n=queued;dwc3_apsd_owner_resume(&dwc,DWC3_APSD_SYSTEM);owner_queue(o,0);assert(queued==n&&!o->work.pending);
 assert(samurai_eud_producer_claim(&debug,&token)==-EBUSY&&!token);teardown();
 puts("9 PM expires the actual route and joins/restores; ordinary resume neither rearms stale evidence nor grants debug ownership");
 assert(!APSD_writes);return 0;
}
