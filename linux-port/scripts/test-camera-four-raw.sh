#!/bin/sh
# Capture two private RAW frames from each RMX1931 camera through CAMSS.
# Usage: test-camera-four-raw.sh [all|front|rear|tele|wide] [output-dir]
set -u

output_dir=${2:-/tmp/samurai-camera-raw}

mkdir -p "$output_dir"

find_media_device() {
	for dev in /dev/media*; do
		[ -e "$dev" ] || continue
		if media-ctl -d "$dev" -p 2>/dev/null |
			grep -q 'msm_vfe0_rdi0'; then
			printf '%s\n' "$dev"
			return 0
		fi
	done
	return 1
}

media=${MEDIA_DEVICE:-$(find_media_device)}
if [ -z "$media" ]; then
	echo "MISSING CAMSS media device" >&2
	exit 1
fi

video=${VIDEO_DEVICE:-$(media-ctl -d "$media" -e "msm_vfe0_video0" 2>/dev/null)}
if [ -z "$video" ] || [ ! -e "$video" ]; then
	echo "MISSING CAMSS VFE video node" >&2
	exit 1
fi

disable_links() {
	for link_phy in 0 1 2 3; do
		media-ctl -d "$media" \
			--link "\"msm_csiphy${link_phy}\":1->\"msm_csid0\":0"[0] \
			2>/dev/null || true
	done
}

capture_two() {
	name=$1
	phy=$2
	model=$3
	width=$4
	height=$5
	media_fmt=$6
	pixel_fmt=$7
	sensor=$(media-ctl -d "$media" -p |
		sed -n "s/^- entity [0-9]*: \\(${model} [^ ]*\\) (.*/\\1/p" |
		head -n 1)

	echo "=== $name ==="
	if [ -z "$sensor" ]; then
		echo "MISSING sensor entity for $model"
		return 1
	fi
	echo "SENSOR=$sensor"
	disable_links
	media-ctl -d "$media" \
		--link "\"msm_csiphy${phy}\":1->\"msm_csid0\":0"[1]
	media-ctl -d "$media" \
		--link '"msm_csid0":1->"msm_vfe0_rdi0":0'[1]
	media-ctl -d "$media" \
		--set-v4l2 "\"${sensor}\":0[fmt:${media_fmt}/${width}x${height}]"
	media-ctl -d "$media" \
		--set-v4l2 "\"msm_csiphy${phy}\":0[fmt:${media_fmt}/${width}x${height}]"
	media-ctl -d "$media" \
		--set-v4l2 "\"msm_csiphy${phy}\":1[fmt:${media_fmt}/${width}x${height}]"
	media-ctl -d "$media" \
		--set-v4l2 "\"msm_csid0\":0[fmt:${media_fmt}/${width}x${height}]"
	media-ctl -d "$media" \
		--set-v4l2 "\"msm_csid0\":1[fmt:${media_fmt}/${width}x${height}]"
	media-ctl -d "$media" \
		--set-v4l2 "\"msm_vfe0_rdi0\":0[fmt:${media_fmt}/${width}x${height}]"
	media-ctl -d "$media" \
		--set-v4l2 "\"msm_vfe0_rdi0\":1[fmt:${media_fmt}/${width}x${height}]"
	v4l2-ctl -d "$video" \
		--set-fmt-video=width="${width}",height="${height}",pixelformat="${pixel_fmt}"

	output="$output_dir/two-${name}.raw"
	rm -f "$output"
	timeout 20 v4l2-ctl -d "$video" --stream-mmap \
		--stream-count=2 --stream-to="$output"
	echo "RESULT $name bytes=$(wc -c < "$output")"
	sha256sum "$output"
	sleep 1
}

# Keep the boot log intact: the runtime verifier checks it for service and
# firmware failures that may have happened before the camera capture.
echo "MEDIA=$media"
echo "VIDEO=$video"
case "${1:-all}" in
front)
	capture_two front 2 imx471 1928 1088 SRGGB10_1X10 pRAA
	;;
rear)
	capture_two rear 1 imx319 1632 1224 SRGGB10_1X10 pRAA
	;;
tele)
	capture_two tele 3 s5k3m5 2104 1560 SGRBG10_1X10 pgAA
	;;
wide)
	capture_two wide 0 s5kgw1 4608 3456 SGBRG10_1X10 pGAA
	;;
all)
	capture_two front 2 imx471 1928 1088 SRGGB10_1X10 pRAA
	capture_two rear 1 imx319 1632 1224 SRGGB10_1X10 pRAA
	capture_two tele 3 s5k3m5 2104 1560 SGRBG10_1X10 pgAA
	capture_two wide 0 s5kgw1 4608 3456 SGBRG10_1X10 pGAA
	;;
*)
	echo "usage: $0 [all|front|rear|tele|wide]" >&2
	exit 2
	;;
esac

echo "=== PM ==="
echo "CAMSS=$(cat /sys/bus/platform/devices/acb3000.camss/power/runtime_status)"
echo "MMCX_STATE=$(cat /sys/kernel/debug/pm_genpd/mmcx/current_state)"
echo "MMCX_PERF=$(cat /sys/kernel/debug/pm_genpd/mmcx/perf_state)"
echo "TAINTED=$(cat /proc/sys/kernel/tainted)"

echo "=== DMESG ==="
dmesg | tail -100
