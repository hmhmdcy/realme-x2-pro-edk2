#!/bin/bash
# 1) ????? v7.3-rc6 ?? tag?2) ?? API ? torvalds/linux fork ? hmhmdcy ??
echo "=== ?? tag ==="
timeout 90 git ls-remote --tags https://github.com/torvalds/linux.git 'v7.3-rc6*' 2>&1 | head -5
echo "=== ?? commit ??? a90ee4305c4a ==="
timeout 90 git ls-remote https://github.com/torvalds/linux.git a90ee4305c4a5df72c11b31dacfdc76e00fcf78a 2>&1 | head -3

TOKEN=$(grep -o 'ghp_[A-Za-z0-9]*' /home/cy122/.git-credentials | head -1)
if [ -z "$TOKEN" ]; then echo "!! ??? token"; exit 1; fi
echo "=== token: ${TOKEN:0:4}... (len ${#TOKEN}) ==="

echo "=== ???? fork ==="
curl -s -o /tmp/f.json -w "http=%{http_code}\n" -H "Authorization: token $TOKEN" \
     https://api.github.com/repos/hmhmdcy/linux
python3 -c "import json;d=json.load(open('/tmp/f.json'));print('exist:',d.get('full_name') or d.get('message'))"

echo "=== ?? fork ==="
curl -s -o /tmp/fork.json -w "http=%{http_code}\n" -X POST \
     -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
     https://api.github.com/repos/torvalds/linux/forks
python3 -c "import json;d=json.load(open('/tmp/fork.json'));print('fork:',d.get('full_name'),d.get('clone_url'),d.get('message'))"

echo "=== ?? fork ?? ==="
for i in $(seq 1 30); do
  code=$(curl -s -o /tmp/f2.json -w "%{http_code}" -H "Authorization: token $TOKEN" \
        https://api.github.com/repos/hmhmdcy/linux)
  if [ "$code" = "200" ]; then echo "ready after ${i}0s"; break; fi
  sleep 10
done
python3 -c "import json;d=json.load(open('/tmp/f2.json'));print('status:',d.get('full_name'),d.get('size'),'KB')"