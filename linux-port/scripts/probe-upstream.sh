#!/bin/bash
D=/home/cy122/x2pro-linux/upstream
TOKEN=$(grep -o 'ghp_[A-Za-z0-9]*' /home/cy122/.git-credentials | head -1)
cd "$D" 2>/dev/null || exit 1

echo "=== A) ?????? ==="
timeout 20 git -c http.proxy= -c https.proxy= ls-remote up HEAD 2>&1 | head -2
echo "rc=$?"

echo "=== B) ??? ==="
timeout 20 git ls-remote up HEAD 2>&1 | head -2
echo "rc=$?"

echo "=== C) ?? commit ????API? ==="
curl -s -H "Authorization: token $TOKEN" \
  https://api.github.com/repos/torvalds/linux/commits/a90ee4305c4a5df72c11b31dacfdc76e00fcf78a -o /tmp/c.json
python3 - <<PY
import json
d=json.load(open('/tmp/c.json'))
c=d.get('commit')
if not c:
    print("API ??:", str(d)[:200]); raise SystemExit
print("sha      :", d.get('sha'))
print("tree     :", c['tree']['sha'])
print("parents  :", [p['sha'] for p in d.get('parents',[])])
a,cm=c['author'],c['committer']
print("author   :", a['name'], "<%s>"%a['email'], a['date'])
print("committer:", cm['name'], "<%s>"%cm['email'], cm['date'])
print("msg first:", c['message'].splitlines()[0])
print("msg lines:", len(c['message'].splitlines()))
PY

echo "=== D) ???? baseline ? tree ==="
git -C /home/cy122/x2pro-linux/linux rev-parse 'b0630f810^{tree}'
git -C /home/cy122/x2pro-linux/linux log -1 --format='%T%n%an <%ae> %ad%n%cn <%ce> %cd%n%s' b0630f810