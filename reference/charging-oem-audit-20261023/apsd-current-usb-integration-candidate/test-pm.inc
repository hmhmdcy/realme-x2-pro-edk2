 /* New owner publication is modeled; actual PM/IRQ and start/withdraw C. */
 reset();apsd_backend=true;samurai_usb_apsd_start(&input);input.apsd_sample_serial=45;input.apsd_attempt_epoch=7;
 assert(registrations==1&&input.apsd_registered);assert(!samurai_usb_prepare(&pdev.dev));
 assert(withdrawals==1&&!input.apsd_registered&&input.apsd_joining&&input.pm_prepared);
 assert(!samurai_usb_suspend(&pdev.dev)&&!samurai_usb_resume(&pdev.dev)&&registrations==1);
 union power_supply_propval native={500000};assert(!samurai_usb_set_property(&supply,POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT,&native));
 samurai_usb_complete(&pdev.dev);assert(registrations==2&&input.apsd_registered&&!input.apsd_joining);
 assert(input.apsd_sample_serial==45&&input.apsd_attempt_epoch==7&&input.udc_valid&&input.udc_current_ua==500000);cleared();groups++;

 reset();apsd_backend=true;samurai_usb_apsd_start(&input);assert(!samurai_usb_prepare(&pdev.dev));
 assert(withdrawals==1&&registrations==1&&!input.paused);samurai_usb_complete(&pdev.dev);
 assert(registrations==2&&input.apsd_registered&&!input.pm_prepared);groups++;

 reset();apsd_backend=true;samurai_usb_apsd_start(&input);assert(!samurai_usb_prepare(&pdev.dev));enable_error=222;
 assert(samurai_usb_suspend(&pdev.dev)==-EIO&&!input.paused&&!input.apsd_registered&&registrations==1);
 samurai_usb_complete(&pdev.dev);assert(registrations==2&&input.apsd_registered);cleared();groups++;

 reset();apsd_backend=true;samurai_usb_apsd_start(&input);samurai_usb_shutdown(&pdev);
 assert(withdrawals==1&&!input.apsd_registered&&input.paused);samurai_usb_shutdown(&pdev);assert(withdrawals==1);groups++;

 reset();apsd_backend=true;input.paused=true;input.apsd_joining=true;samurai_usb_apsd_start(&input);
 assert(!registrations&&input.apsd_joining);input.paused=false;input.pm_prepared=true;samurai_usb_apsd_start(&input);
 assert(!registrations&&input.apsd_joining);input.pm_prepared=false;samurai_usb_apsd_start(&input);
 assert(registrations==1&&input.apsd_registered&&!input.apsd_joining);groups++;
