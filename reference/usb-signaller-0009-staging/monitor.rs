use futures_lite::StreamExt;
use std::time::Duration;
use tokio_udev::{AsyncMonitorSocket, EventType};
use zbus::{Connection, object_server::SignalEmitter};

use crate::service::{service_start, service_stop};
use crate::udc::{UDC, UDCMode, discover_udcs};
use crate::UsbModedDBus;

async fn rearm_device_mode_service() {
    for _ in 0..50 {
        if let Some(udc_name) = discover_udcs().into_iter().next()
            && let Ok(udc) = UDC::load(&udc_name)
        {
            let service = match udc.mode {
                UDCMode::Developer => Some("usb-signaller-developer-mode"),
                UDCMode::Tethering => Some("usb-signaller-tethering-mode"),
                UDCMode::MTP => Some("usb-signaller-mtp-mode"),
                _ => None,
            };
            if let Some(service) = service {
                if let Err(error) = service_start(service) {
                    eprintln!("❌ Failed to restore {service}: {error}");
                }
            }
            return;
        }
        tokio::time::sleep(Duration::from_millis(100)).await;
    }
    eprintln!("❌ Device role returned but no UDC appeared");
}

pub async fn monitor_usb_events(connection: Connection) -> anyhow::Result<()> {
    let mut monitor = AsyncMonitorSocket::new(
        tokio_udev::MonitorBuilder::new()?
            .match_subsystem("typec")?
            .match_subsystem("usb_role")?
            .listen()?,
    )?;
    let emitter = SignalEmitter::new(&connection, "/com/meego/usb_moded")?;
    let mut last_role = String::new();

    while let Some(event) = monitor.next().await {
        let event = event?;

        if event
            .subsystem()
            .map(|value| value.to_string_lossy() == "usb_role")
            .unwrap_or(false)
        {
            let role = std::fs::read_to_string(event.syspath().join("role"))
                .unwrap_or_default()
                .trim()
                .to_string();
            if role != last_role {
                last_role = role.clone();
                match role.as_str() {
                    "host" => {
                        println!("ℹ️  USB role changed to host; stopping mode services");
                        for service in [
                            "usb-signaller-developer-mode",
                            "usb-signaller-tethering-mode",
                            "usb-signaller-mtp-mode",
                        ] {
                            let _ = service_stop(service);
                        }
                    }
                    "device" => {
                        println!("ℹ️  USB role changed to device; rearming mode service");
                        rearm_device_mode_service().await;
                    }
                    _ => {}
                }
            }
            continue;
        }

        match event.event_type() {
            EventType::Add => {
                println!("ℹ️  Cable connected (typec)");
                if let Err(e) =
                    UsbModedDBus::sig_usb_event_ind(&emitter, String::from("USB connected")).await
                {
                    eprintln!("❌ Failed to emit USB event signal: {e}");
                }
            }

            EventType::Remove => {
                println!("ℹ️  Cable disconnected (typec)");
                if let Err(e) =
                    UsbModedDBus::sig_usb_event_ind(&emitter, String::from("USB disconnected"))
                        .await
                {
                    eprintln!("❌ Failed to emit USB event signal: {e}");
                }
            }
            _ => {}
        }
    }

    Ok(())
}
