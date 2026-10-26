#!/usr/bin/env python3
"""P2 documentation cleanup for the linux-port mirror (Windows working copy).

1. rename docs/sectionNN-<topic>.md -> docs/NN-<topic>.md
2. rewrite every reference to the old file names (scripts and top-level docs)
3. add a guard to the one-shot sync-sectionNN.sh scripts so they can never
   append a section body back into HANDOVER-NEXT.md (which is an index now)
4. refresh the generated README-MIRROR.md text and the health-check filter

Idempotent: run it again and it reports nothing to do.
"""
import os, re

W = "/mnt/e/RealmeX2Pro edk2"
LP = os.path.join(W, "linux-port")
DOCS = os.path.join(LP, "docs")
SCRIPTS = os.path.join(LP, "scripts")
GUARD = ("\n# 2026-10-08: HANDOVER-NEXT.md is an index now - a section lives in exactly one\n"
         "# file (linux-port/docs/NN-<topic>.md or sessions/NN-<topic>.md).  Never append\n"
         "# a section body back into the handover.\n"
         "if grep -q '^## History index' \"$HW\" 2>/dev/null; then\n"
         "  echo \"HANDOVER-NEXT.md is an index now - nothing to append; edit the section file instead.\"\n"
         "  exit 0\n"
         "fi\n")
APPENDERS = ["sync-section19.sh"] + ["sync-section%d.sh" % n for n in range(20, 27)]
REF = re.compile(r"section(\d\d)-([a-z0-9-]+\.md)")

def rw(path, fn):
    with open(path, encoding="utf-8") as f:
        t = f.read()
    n = fn(t)
    if n != t:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(n)
        print("  patched", os.path.relpath(path, W))
    return n != t

def main():
    print("== 1. rename docs/sectionNN-*.md ==")
    for name in sorted(os.listdir(DOCS)):
        m = re.match(r"section(\d\d)-(.*)$", name)
        if m:
            new = "%s-%s" % (m.group(1), m.group(2))
            os.rename(os.path.join(DOCS, name), os.path.join(DOCS, new))
            print("  %s -> %s" % (name, new))

    print("== 2. rewrite old file names ==")
    for name in sorted(os.listdir(SCRIPTS)):
        p = os.path.join(SCRIPTS, name)
        if os.path.isfile(p):
            rw(p, lambda t: REF.sub(r"\1-\2", t))
    for name in sorted(os.listdir(W)):
        if name.endswith(".md"):
            rw(os.path.join(W, name), lambda t: REF.sub(r"\1-\2", t))
    for sub in ("sessions", "reference"):
        d = os.path.join(W, sub)
        if os.path.isdir(d):
            for name in sorted(os.listdir(d)):
                if name.endswith(".md"):
                    rw(os.path.join(d, name), lambda t: REF.sub(r"\1-\2", t))

    print("== 3. guard the one-shot section syncers ==")
    for name in APPENDERS:
        p = os.path.join(SCRIPTS, name)
        if not os.path.isfile(p):
            print("  (no %s)" % name)
            continue
        def add_guard(t, name=name):
            if "## History index" in t:
                return t
            out, done = [], False
            for l in t.splitlines(keepends=True):
                out.append(l)
                if not done and l.startswith("HW="):
                    out.append(GUARD)
                    done = True
            if not done:
                print("  WARN: no HW= line in %s" % name)
                return t
            print("  guard added to %s" % name)
            return "".join(out)
        rw(p, add_guard)

    print("== 4. health check: ignore the generated README-MIRROR.md ==")
    rw(os.path.join(SCRIPTS, "docs-health-check.sh"),
       lambda t: t.replace("grep -v 'artifacts'", "grep -v -e artifacts -e README-MIRROR.md"))

    print("== 5. mirror script: describe the new docs naming ==")
    rw(os.path.join(SCRIPTS, "mirror-linux-port.sh"),
       lambda t: t.replace(
           "    docs/            section 18-21 companions, old-project verification, EDK2 embed",
           "    docs/            NN-<topic>.md companions for handover sections 19-28,\n"
           "                     plus the Android DTS reference / EDK2 embed / old-project notes"))
    print("done")

main()