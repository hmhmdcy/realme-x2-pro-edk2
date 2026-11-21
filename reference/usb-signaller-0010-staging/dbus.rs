use anyhow::Result;
use std::string::String;
use tokio::sync::Mutex;
use tokio::time::{Duration, sleep};
use zbus::{Connection, connection, interface, object_server::SignalEmitter};

use crate::udc::{UDC, discover_udcs};
use crate::urs::URSRole;
use crate::urs::{URS, discover_urss};
use crate::utils::{string_to_udcmode, udcmode_to_string};

pub struct UsbModedDBus;

static SET_MODE_LOCK: Mutex<()> = Mutex::const_new(());

pub async fn create_usbmoded_connection() -> Result<Connection> {
    return Ok(connection::Builder::system()?
        .name("com.meego.usb_moded")?
        .serve_at("/com/meego/usb_moded", UsbModedDBus)?
        .build()
        .await?);
}

#[interface(name = "com.meego.usb_moded")]
impl UsbModedDBus {
    #[zbus(signal, name = "sig_usb_event_ind")]
    pub async fn sig_usb_event_ind(emitter: &SignalEmitter<'_>, event: String) -> zbus::Result<()>;

    #[zbus(name = "set_mode")]
    pub async fn set_mode(
        &self,
        mode: &str,
        #[zbus(signal_emitter)] emitter: SignalEmitter<'_>,
    ) -> Result<String, zbus::fdo::Error> {
        // The default mode is applied while the D-Bus service is becoming
        // ready. Serialize that transition with user-requested mode changes so
        // configfs, OpenRC mode services and NetworkManager cannot overlap.
        let _guard = SET_MODE_LOCK.lock().await;
        println!("ℹ️  DBus: set_mode({mode})");

        /* Netboot mode may never be interrupted */
        if mode == "netboot_mode" {
            eprintln!("⚠️  Netboot mode cannot be changed");
            return Err(zbus::fdo::Error::Failed(
                "Netboot mode cannot be changed".into(),
            ));
        }

        /* USB Role Switcher */
        for name in &discover_urss() {
            if URS::load(name).is_ok() {
                let role = match mode {
                    "host_mode" => URSRole::Host,
                    _ => URSRole::Device,
                };

                /* Configure role */
                if let Ok(urs) = URS::set_role(&role) {
                    println!("URS reconfigured:");
                    println!("  Name: {}", urs.name);
                    println!("  Role: {:?}", urs.role);
                    if let Some(udc) = urs.udc {
                        println!("  UDC: {}", udc.name);
                    }
                }

                /* Host role doesn't require any UDC configuration, return here */
                if role == URSRole::Host {
                    /* Trigger show dialog */
                    if let Err(error) = emitter
                        .sig_usb_event_ind(String::from("mode_requested_show_dialog"))
                        .await
                    {
                        eprintln!("❌ Failed to emit signal to show dialog: {error}");
                    }
                    return Ok("host_mode".to_string());
                }
            }
        }

        /* Role is device, process UDC */
        /* UDC registration can lag the role switch.  Retry discovery for a
         * bounded time instead of failing on the first empty scan. */
        let mut udc_names = discover_udcs();
        let mut udc_wait_ms = 0;
        while udc_names.is_empty() && udc_wait_ms < 10_000 {
            sleep(Duration::from_millis(250)).await;
            udc_wait_ms += 250;
            udc_names = discover_udcs();
        }

        /* Determine the target mode enum before moving 'mode' */
        let target_mode = string_to_udcmode(mode);

        /* Apply the mode to discovered UDCs */
        for name in &udc_names {
            match UDC::load(name) {
                Ok(udc) => {
                    match UDC::set_mode(udc, target_mode.clone()) {
                        Ok(udc) => {
                            println!("UDC reconfigured:");
                            println!("  Name: {}", udc.name);
                            println!("  Enabled: {}", udc.enabled);
                            println!("  Mode: {:?}", udc.mode);
                            if let Some(gadget) = udc.gadget {
                                println!("  Gadget: {}", gadget.name);
                            }
                            let return_str = udcmode_to_string(target_mode);

                            /* Trigger show dialog */
                            if let Err(error) = emitter
                                .sig_usb_event_ind(String::from("mode_requested_show_dialog"))
                                .await
                            {
                                eprintln!("❌ Failed to emit signal to show dialog: {error}");
                            }

                            return Ok(return_str.to_string());
                        }
                        Err(err) => {
                            eprintln!("❌ UDC reconfiguring failed: {err:?}");
                            return Err(zbus::fdo::Error::Failed(format!(
                                "UDC reconfiguring failed: {err:?}"
                            )));
                        }
                    };
                }
                Err(err) => {
                    eprintln!("❌ UDC loading failed: {err:?}");
                    return Err(zbus::fdo::Error::Failed(format!(
                        "UDC loading failed: {err:?}"
                    )));
                }
            };
        }

        /* UDC failed so this must be an error */
        return Err(zbus::fdo::Error::Failed("UDC failed".to_string()));
    }

    #[zbus(name = "mode_request")]
    pub async fn mode_request(&self) -> Result<String, zbus::fdo::Error> {
        println!("ℹ️  DBus: mode_request()");
        /* Search for USB Role Switcher */
        for name in &discover_urss() {
            let mut skipped: bool = false;
            /* When the cable is plugged in, reading the URS immediately may give 'device'
             * as role. A few ms later, it may have switched to 'host', causing no UDC
             * to be present anymore. Retry in that case until role is stable
             */
            for _n in 1..10 {
                if let Ok(urs) = URS::load(name) {
                    let role = urs.role;
                    println!("Loaded URS: {} ({:?})", urs.name, role);

                    match role {
                        /* Host role has no additional modes */
                        URSRole::Host => return Ok("host_mode".to_string()),
                        /* Load UDC associated with URS in device role */
                        URSRole::Device => {
                            if let Some(udc) = urs.udc {
                                let mode = udc.mode;
                                println!("URS (role Device) UDC: {mode:?}");
                                return Ok(udcmode_to_string(mode).to_string());
                            } else {
                                eprintln!(
                                    "⚠️  URS (role Device) has no UDC assigned yet, rereading role..."
                                );
                                sleep(Duration::from_millis(1000)).await;
                                continue;
                            }
                        }
                        URSRole::Unknown => {
                            eprintln!("❌ Unknown USB role, cannot proceed");
                            return Err(zbus::fdo::Error::Failed(
                                "Unknown USB role, cannot proceed".to_string(),
                            ));
                        }
                    }
                } else {
                    skipped = true;
                }
            }

            if skipped {
                continue;
            }

            return Err(zbus::fdo::Error::Failed(
                "URS Device has no UDC assigned".to_string(),
            ));
        }

        /* No USB Role Switcher available, fallback to UDC only */
        for name in &discover_udcs() {
            println!("⚠️  Fallback to UDC-only mode, UDC: {name}");
            if let Ok(udc) = UDC::load(name) {
                let mode = udc.mode;
                return Ok(udcmode_to_string(mode).to_string());
            }
        }

        /* Pre-flight checks enforces that the necessary hardware is present */
        eprintln!("❌ No USB Device Controler (UDC) or USB Role Switcher (URS) available!");
        return Err(zbus::fdo::Error::Failed(
            "No UDC or URS available!".to_string(),
        ));
    }

    #[zbus(name = "get_modes")]
    pub async fn get_modes(&self) -> String {
        /*
         * Netboot mode is never available for users.
         * Unknown and disconnected modes are internal modes.
         */
        let mut available_modes =
            String::from("developer_mode,tethering_mode,charging_only,mtp_ffs_mode");

        /* USB Role Switcher is required for host mode */
        for name in &discover_urss() {
            if URS::load(name).is_ok() {
                available_modes.push_str(",host_mode");
                break;
            }
        }

        return available_modes;
    }
}
