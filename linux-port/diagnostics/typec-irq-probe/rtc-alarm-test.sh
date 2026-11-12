#!/bin/sh
set -eu

delay=${1:-10}
now=$(cat /sys/class/rtc/rtc0/since_epoch)
future=$((now + delay))
echo "now=$now future=$future"
echo 0 >/sys/class/rtc/rtc0/wakealarm
echo "$future" >/sys/class/rtc/rtc0/wakealarm
echo "alarm=$(cat /sys/class/rtc/rtc0/wakealarm)"

i=0
while [ "$i" -lt $((delay + 5)) ]; do
	sleep 1
	i=$((i + 1))
	echo "t=$i rtc=$(cat /sys/class/rtc/rtc0/since_epoch) alarm=$(cat /sys/class/rtc/rtc0/wakealarm)"
done
