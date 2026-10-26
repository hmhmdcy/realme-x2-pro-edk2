/* Appended to the existing boundary fixture; actual owner/provider/PD C. */
static void no_attempts(void){assert(!APSD_writes);}
int main(void)
{
 setup(true);release_phy();tick();assert(bound_owner->work.pending&&!bound_owner->phy_client&&!reads&&!writes&&!analog_calls);
 publish_phy();prepared();assert(bound_owner->phy_client&&bound_owner->ref.refs==3&&!phy_writes);teardown();puts("1 actual missing PHY publication defers before PD I/O; later instance binds");

 setup(true);prepared();wire(true);tick();assert(bound_owner->primary_error==-EOPNOTSUPP&&!bound_owner->once.attempted&&!analog_calls&&!phy_writes);
 assert(bound_owner->phy_client&&bound_owner->pd_lease.owner);teardown();puts("2 real PHY client and PD lease do not bypass the remaining attempt gate");

 setup(true);prepared();wire(true);tick();struct qcom_snps_hsphy_window_client*c=bound_owner->phy_client;
 bound_owner->once.attempted=1;bound_owner->once.phase=SAMURAI_APSD_CANCELLED;u64 epoch=bound_owner->once.epoch;
 assert(!dwc3_apsd_owner_pause(&dwc,DWC3_APSD_SYSTEM));assert(bound_owner->phy_client==c&&bound_owner->ref.refs==2&&!pd->leased);
 dwc3_apsd_owner_resume(&dwc,DWC3_APSD_SYSTEM);tick();assert(bound_owner->once.epoch==epoch&&bound_owner->once.attempted&&bound_owner->phy_client==c);
 teardown();puts("3 system PM keeps client registration and physical attempt history");

 setup(true);prepared();struct samurai_apsd_owner*o=bound_owner;release_phy();assert(o->quarantined&&o->retiring&&(o->blocked&DWC3_APSD_PHY)&&!o->phy_client&&!pd->leased&&!o->work.pending);
 int n=queued;dwc3_apsd_owner_resume(&dwc,DWC3_APSD_SYSTEM);dwc3_apsd_owner_resume(&dwc,DWC3_APSD_PD);owner_queue(o,0);
 assert(queued==n&&o->quarantined&&(o->blocked&DWC3_APSD_PHY));teardown();puts("4 provider withdrawal cancels/releases; ordinary resume cannot clear its quarantine");

 setup(true);prepared();assert(!samurai_pd5v_quiesce(pd));assert(bound_owner->phy_client&&!pd->leased);release_phy();samurai_pd5v_complete(pd);
 assert(bound_owner->quarantined&&!bound_owner->work.pending&&!bound_owner->phy_client);teardown();
 setup(true);prepared();release_phy();assert(!samurai_pd5v_quiesce(pd));samurai_pd5v_complete(pd);assert(bound_owner->quarantined);teardown();puts("5 real PD and PHY cancellation in either order preserve independent fences");

 setup(false);tick();o=bound_owner;c=o->phy_client;assert(c);struct qcom_hsphy_window_provider*p=c->provider;
 /* Deterministic scheduling cut: provider published revocation but its
  * callback has not acquired lifecycle serialization yet. No real wait or
  * hardware completion is claimed from this cut. */
 p->withdrawing=true;assert(owner_phy_resolve(o)==-ESHUTDOWN&&o->quarantined&&o->retiring);p->withdrawing=false;
 release_phy();assert(!o->phy_client&&!o->work.pending&&!analog_calls&&!phy_writes);teardown();puts("6 worker observing revoked metadata fences retirement before cleanup");

 setup(false);tick();assert(bound_owner->phy_client);unbind_on_phy_unlock=true;release_phy();
 /* The independently live PD provider still owns its own Type-C reference;
  * teardown destroys that provider and checks the final zero count. */
 assert(!bound_owner&&!notifiers&&tcpc.dev.refs==1);teardown();puts("7 provider callback context pin survives DWC unbind before callback dispatch");

 setup(false);tick();o=bound_owner;assert(!owner_enter_windows(o)&&o->phy.cookie&&phy_writes==3&&host.pm_refs==1);
 release_phy();assert(o->quarantined&&!o->phy_client&&!o->phy.cookie&&phy_writes==6&&dwc_cancels==1&&!dwc_ends&&!eud_ends&&o->extra_pm);
 assert(phy_regs[0x64/4]==0xa4&&phy_regs[0x3c/4]==0xf0&&phy_regs[0x94/4]==0xa2);
 dwc3_apsd_owner_stop_post(&dwc);assert(!o->dwc_window.cookie&&!o->eud.cookie&&!o->extra_pm&&!host.pm_refs&&eud_ends==1&&!dwc_ends);
 teardown();puts("8 forced supplier removal restores PHY then cancels DWC; later retirement consumes remaining tokens");

 setup(false);tick();o=bound_owner;assert(!owner_enter_windows(o));drop_phy_write=4;release_phy();
 assert(o->quarantined&&o->phy.cookie&&o->phy_client&&o->phy_error==-EIO&&phy_writes==4&&!dwc_cancels&&!dwc_ends&&!eud_ends);
 struct qcom_snps_hsphy_window_result receipt;assert(!qcom_snps_hsphy_window_status(o->phy_client,&receipt)&&receipt.revoked&&receipt.restore_error==-EIO&&!receipt.restored);
 dwc3_apsd_owner_unbind(&dwc);assert(bound_owner==o&&!o->dwc&&!o->phy_client&&o->quarantined&&phy_writes==4);
 /* Fixture disposal only: model destruction of the already-retired outer
  * resources, never an implementation path or a successful restore claim. */
 o->phy.cookie=o->eud.cookie=o->dwc_window.cookie=0;o->extra_pm=false;host.pm_refs=0;bound_owner=NULL;kref_put(&o->ref,owner_free);
 teardown();puts("9 failed exact restore remains quarantined; revoked handle is dropped without another MMIO attempt");

 setup(false);tick();o=bound_owner;assert(!owner_enter_windows(o));c=o->phy_client;assert(owner_phy_release(o)==-EBUSY&&o->phy_client==c&&o->ref.refs==2);
 assert(!dwc3_apsd_owner_pause(&dwc,DWC3_APSD_SYSTEM)&&o->phy_client==c&&phy_writes==6&&dwc_ends==1&&eud_ends==1&&!host.pm_refs);
 teardown();puts("10 busy unregister retains the owner; normal PM restores through the same client");

 setup(false);o=bound_owner;assert(!o->phy_client);assert(owner_enter_windows(o)==-ENODEV&&!host.pm_refs&&!analog_calls&&!phy_writes);
 tick();qcom_snps_hsphy_shutdown(&phy_platform);assert(o->quarantined&&!o->phy_client);qcom_snps_hsphy_remove(&phy_platform);release_phy();teardown();puts("11 no naked PHY fallback; shutdown and remove share the actual provider callback");

 setup(true);prepared();wire(true);tick();epoch=bound_owner->once.epoch;bound_owner->once.attempted=1;bound_owner->once.phase=SAMURAI_APSD_CANCELLED;
 c=bound_owner->phy_client;dwc3_apsd_owner_unbind(&dwc);assert(!bound_owner&&!phy_shadow.window_provider->client);
 dwc3_apsd_owner_bind(&dwc);tick();assert(bound_owner->phy_client&&bound_owner->once.epoch==epoch&&bound_owner->once.attempted&&writes==4&&!phy_writes);
 (void)c;teardown();puts("12 UDC rebind registers a new client without resetting attempted physical history");
 no_attempts();return 0;
}
