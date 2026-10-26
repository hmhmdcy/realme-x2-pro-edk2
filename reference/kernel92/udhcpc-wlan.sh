#!/bin/sh
# DHCP state is applied only to wlan0. USB NCM remains available for debugging.
set -eu
[ "${interface:-}" = wlan0 ]
umask 077
ipv4()
{
    printf '%s\n' "$1" | awk -F. 'NF != 4 { exit 1 } { for (i=1;i<=4;i++) if ($i !~ /^[0-9]+$/ || $i+0>255 || length($i)>3) exit 1 }'
}
case "${1:-}" in
    deconfig)
        ip addr flush dev wlan0
        ;;
    bound|renew)
        ipv4 "$ip"
        ipv4 "$subnet"
        ip addr flush dev wlan0
        ifconfig wlan0 "$ip" netmask "$subnet" up
        for gateway in ${router:-}; do
            ipv4 "$gateway"
            ip route replace default via "$gateway" dev wlan0 metric 20
            break
        done
        if [ -n "${dns:-}" ]; then
            : > /run/samurai-wifi/resolv.conf
            for server in $dns; do
                ipv4 "$server"
                printf 'nameserver %s\n' "$server" >> /run/samurai-wifi/resolv.conf
            done
            cat /run/samurai-wifi/resolv.conf > /etc/resolv.conf
        fi
        printf 'ip=%s\nsubnet=%s\nrouter=%s\ndns=%s\nlease=%s\n' "$ip" "$subnet" "${router:-}" "${dns:-}" "${lease:-}" > /run/samurai-wifi/dhcp-lease.txt
        printf 'wlan0 DHCP lease applied\n'
        ;;
    nak|leasefail) printf 'wlan0 DHCP event: %s\n' "$1" ;;
    *) exit 1 ;;
esac
