 /* Additional tests call internal entry points explicitly. Production's
  * route gate stays closed. Only post-transfer samples are modeled below. */
 setup(true);prepared();wire(true);tick();o=bound_owner;assert(!owner_enter_windows(o));
 assert(!samurai_apsd_claim(&o->once,o->once.epoch,owner_now_ms(),owner_now_ms()+5000));
 boundary_mode=1;assert(owner_transfer(o)==-EOPNOTSUPP&&!o->attempt_active&&!o->transfer.transfer_attempted);
 assert(o->once.attempted&&o->once.write_error==-EOPNOTSUPP);assert(!dwc3_apsd_owner_pause(&dwc,DWC3_APSD_SYSTEM));teardown();
 puts("13 real PD/PHY and embedded identity still fail the absent route at the final callback");

 setup(true);prepared();wire(true);tick();o=bound_owner;assert(!owner_enter_windows(o));
 assert(!samurai_apsd_claim(&o->once,o->once.epoch,owner_now_ms(),owner_now_ms()+5000));
 boundary_mode=1;(void)owner_transfer(o);o->once.phase=SAMURAI_APSD_WRITING;o->attempt_active=true;
 struct samurai_apsd_attempt copy=o->attempt;struct samurai_apsd_bus_sample fresh=o->last_sample;fresh.serial++;
 assert(copy.validate(&copy,&fresh)==-ESTALE);
 o->attempt_generation++;assert(o->attempt.validate(&o->attempt,&fresh)==-ESTALE);o->attempt_generation--;
 o->abort=true;assert(o->attempt.validate(&o->attempt,&fresh)==-ECANCELED);o->attempt_active=false;
 assert(!dwc3_apsd_owner_pause(&dwc,DWC3_APSD_SYSTEM));teardown();
 puts("14 copied address, stale actual lease generation and cancellation cannot borrow the worker attempt");

 setup(true);prepared();wire(true);tick();o=bound_owner;assert(!owner_enter_windows(o));
 assert(!samurai_apsd_claim(&o->once,o->once.epoch,owner_now_ms(),owner_now_ms()+5000));
 boundary_mode=1;(void)owner_transfer(o);o->once.phase=SAMURAI_APSD_WRITING;o->attempt_active=true;
 fresh=o->last_sample;fresh.serial++;pd->blocked=true;pd->generation++;
 assert(o->attempt.validate(&o->attempt,&fresh)==-ESTALE);o->attempt_active=false;
 assert(!dwc3_apsd_owner_pause(&dwc,DWC3_APSD_SYSTEM));teardown();
 puts("15 actual PD provider generation publication invalidates the final validation before join");

 setup(true);prepared();wire(true);tick();o=bound_owner;assert(!owner_enter_windows(o));
 assert(!samurai_apsd_claim(&o->once,o->once.epoch,owner_now_ms(),owner_now_ms()+5000));
 boundary_mode=1;(void)owner_transfer(o);o->once.phase=SAMURAI_APSD_WRITING;o->attempt_active=true;
 fresh=o->last_sample;fresh.serial++;p=o->phy_client->provider;p->withdrawing=true;
 assert(o->attempt.validate(&o->attempt,&fresh)==-ESHUTDOWN);p->withdrawing=false;o->attempt_active=false;
 assert(!dwc3_apsd_owner_pause(&dwc,DWC3_APSD_SYSTEM));teardown();
 puts("16 actual PHY revocation metadata rejects the final attempt without new analog entry");

 setup(true);prepared();wire(true);tick();o=bound_owner;
 assert(!samurai_apsd_claim(&o->once,o->once.epoch,owner_now_ms(),owner_now_ms()+5000));
 boundary_mode=2;assert(owner_transfer(o)==SAMURAI_APSD_WAIT&&o->once.phase==SAMURAI_APSD_WAIT_DONE);
 assert(owner_read(o)==SAMURAI_APSD_NEW_DONE&&o->once.phase==SAMURAI_APSD_COMPLETE);teardown();
 puts("17 modeled post-write clear is fed through the actual owner and once core before next new DONE");

 setup(true);prepared();wire(true);tick();o=bound_owner;
 assert(!samurai_apsd_claim(&o->once,o->once.epoch,owner_now_ms(),owner_now_ms()+5000));
 boundary_mode=3;assert(owner_transfer(o)==SAMURAI_APSD_WAIT&&o->once.phase==SAMURAI_APSD_WAIT_CLEAR);
 assert(owner_read(o)==SAMURAI_APSD_WAIT&&o->once.phase==SAMURAI_APSD_WAIT_CLEAR);teardown();
 puts("18 modeled post-write old DONE still cannot complete; every real production gate remains closed");
