# Host-side USB VBUS automation probe (2026-11-12)

## Purpose

The remaining basic acceptance step is a real cable unplug/plug while the
phone is in `s2idle`.  This note records whether the Windows host can
electrically cycle VBUS without a person touching the cable.

## Result: blocked without elevation

The current NCM link is on the AMD `PCI\VEN_1022&DEV_43D5` root hub,
port 5 (`USB\VID_0525&PID_A4A1`).  The NVIDIA
`PCI\VEN_10DE&DEV_1ADB` USB Type-C Port Policy Controller is on a
different PCI path and is not the controller for this link.

The Windows host also has `ACPI\ANX7411` / `ANXUcmCxCD`, an Analogix
UCM client.  Its device stack exposes no documented ordinary-user
connector-power interface.  The system-provided `UsbCApi.dll` exports
`UsbCApi_SetConnectorPowerRole`, but the official Microsoft MUTT 3.0.2
`UsbCApiCmd.exe` returns `0x80070005` (Access denied) when run without
elevation:

```text
Querying the providers present on the system:
ExitCode=-2147024891
```

The root hub's `IOCTL_USB_HUB_CYCLE_PORT` also returned
`ERROR_GEN_FAILURE (31)`.  This does not prove the port hardware cannot
be cycled by a privileged UCM/PPC caller; it proves the current
unattended session cannot do it safely.

## Artifact

Microsoft MUTT package 3.0.2:

```text
E:\edk2-samurai-out\standard-arm64-v731\usb-typec-host-api-20261112\MUTTPackage-3_0_2.msi
SHA-256 7741618eeb97572b3a83965799738b2934b5d474782ba2670ccd07c678c022de
```

The package was extracted with `msiexec /a` to
`usb-typec-host-api-20261112\extracted`; no installer, driver, or
system service was installed.  The extracted `UsbCApiCmd.exe`, `x64`
build, is the executable used for the access-denied probe.

## Safety

Do not elevate, disable, or replace the NVIDIA/ANX UCM drivers merely to
obtain an automated wake test.  A privileged role-switch experiment
must first be proven not to disturb the display, charging, or the
current NCM link.  The physical cable test remains the authoritative
acceptance method for USB insert/remove wake.
