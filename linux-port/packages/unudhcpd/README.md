# unudhcpd DHCP broadcast fix (0.5.0-r2)

This package pins Alpine's `unudhcpd` 0.5.0 baseline and carries the
upstreamable fix in `0012-unudhcpd-honor-dhcp-broadcast-flag.patch`.
It is the standard postmarketOS DHCP server used by Developer and
Tethering USB modes; the board only supplies its address configuration.

The fix keeps the client's DHCP BROADCAST flag and sends the OFFER/ACK to
`255.255.255.255` when requested. Windows NCM may use that path after a
host re-enumeration and previously remained on APIPA even while the
phone's UDC, carrier and `unudhcpd.usb0` listener were healthy.

The package is a normal OpenRC/systemd subpackage build. No private board
API, kernel change, or hard-coded Windows MAC address is added.

Signed local artifacts:

| package | SHA-256 |
| --- | --- |
| `unudhcpd-0.5.0-r2.apk` | `67cc4aca6aa17cb4ec7c7cc5bcdeec1ddcb032a11a77b5a204f13edccb9b45d3` |
| `unudhcpd-openrc-0.5.0-r2.apk` | `af45f76fcf14eec5940eb57aa9c3964bf466359dbdb5350a01a3493dbff6a21b` |

The deployed aarch64 binary is
`4c2ca9ef8bc9473c680d112ca8df4b6fa9e3eeda604455cb6b38a20fbffa7b87`.
Two UDC soft reconnect cycles reacquired Windows DHCP
`172.16.42.2/24` from `172.16.42.1`, followed by NCM SSH and an
8 MiB SHA-256-matched round trip.
