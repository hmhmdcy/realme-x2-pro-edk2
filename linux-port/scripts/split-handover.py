#!/usr/bin/env python3
"""Split HANDOVER-NEXT.md (30 sections, 109 KB) into a slim entry plus one file per section.

Input  (the Windows authoring copy):  E:\RealmeX2Pro edk2\HANDOVER-NEXT.md
Outputs (same root):
    HANDOVER-NEXT.md                      slimmed: title + sections 0-7 + history index
    archive/HANDOVER-NEXT-full-2026-10-08.md   verbatim copy of the input
    reference/DECISIONS.md                former sections 8-11
    sessions/NN-<topic>.md               former sections 12-18, 29, 30
Former sections 19-28 already live in linux-port/docs/ and are only referenced.

Run from WSL: python3 "/mnt/e/RealmeX2Pro edk2/linux-port/scripts/split-handover.py"
"""
import os, re, sys

ROOT = "/mnt/e/RealmeX2Pro edk2"
SRC = os.path.join(ROOT, "HANDOVER-NEXT.md")
STAMP = "2026-10-08"
FULL = "archive/HANDOVER-NEXT-full-%s.md" % STAMP
DECISIONS = "reference/DECISIONS.md"

SESSIONS = {
    12: "12-final-image-and-log-gap.md",
    13: "13-eud-log-ring-implemented.md",
    14: "14-eud-log-ring-verified.md",
    15: "15-full-debug-and-crash-root-cause.md",
    16: "16-commits-noise-and-cpufreq-bug.md",
    17: "17-submodule-solution-a.md",
    18: "18-mainline-kernel-in-firmware.md",
    29: "29-eud-console-tty-command-channel.md",
    30: "30-artifacts-and-workflow.md",
}
LINUX = {
    19: "linux-port/docs/19-loadoptions.md",
    20: "linux-port/docs/20-linux-boot.md",
    21: "linux-port/docs/21-eud-framing.md",
    22: "linux-port/docs/22-kernel-upstream.md",
    23: "linux-port/docs/23-upstream-push.md",
    24: "linux-port/docs/24-push-done.md",
    25: "linux-port/docs/25-eud-console.md",
    26: "linux-port/docs/26-real-machine-review.md",
    27: "linux-port/docs/27-userspace-and-shortcuts.md",
    28: "linux-port/docs/28-flywheel.md",
}
WHAT = {
    8:  "Linux boot path and persistent variables - decision",
    9:  "Port checklist status",
    10: "Linux porting paths; when a GPT change is really needed",
    11: "EDL (9008) resources for RMX1931; the auth question",
    12: "Final image verified, why boot logs were still missed, two fixes",
    13: "EUD log ring buffer implemented",
    14: "EUD log ring: verified on hardware",
    15: "Full DEBUG works; the real cause of the +0x34B8 crash",
    16: "Commits, boot-option noise removed, SetCPUFreqDxe bug",
    17: "Submodule solved with plan A (fork + branch)",
    18: "Mainline Linux: the kernel goes into the firmware volume",
    19: "Kernel command line in the boot option LoadOptions",
    20: "Mainline Linux boots on hardware; kernel moved to the FAT",
    21: "EUD log garbling: kernel-side FIFO overflow",
    22: "Kernel side into GitHub: fork from upstream",
    23: "Kernel side: fetch and branches done, push blocked",
    24: "samurai-bringup pushed to GitHub",
    25: "EUD real console + firmware cmdline/DTB update",
    26: "Real-hardware review: console works, two culprits, panic loop",
    27: "Userspace reached; console to /dev/kmsg; shortcuts vs goals",
    28: "Button-free fastboot and the hands-off flywheel",
    29: "EUD COM console, tty and command channel",
    30: "Current artifacts and how to drive the phone",
}

def main():
    with open(SRC, encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines(keepends=True)
    heads = []
    for i, l in enumerate(lines):
        m = re.match(r"^## (\d+)\. ", l)
        if m:
            heads.append((int(m.group(1)), i, l.rstrip()))
    nums = [n for n, _, _ in heads]
    if nums != list(range(0, 31)):
        sys.exit("refusing to run: expected sections 0..30 in order, found %s" % nums)
    if os.path.exists(os.path.join(ROOT, FULL)):
        sys.exit("refusing to run: %s already exists (split already done?)" % FULL)

    body = {}
    for k, (n, i, title) in enumerate(heads):
        end = heads[k + 1][1] if k + 1 < len(heads) else len(lines)
        body[n] = "".join(lines[i:end]).rstrip() + "\n"

    def write(rel, data):
        p = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(data)
        print("wrote %-52s %7d bytes" % (rel, len(data.encode())))

    write(FULL, text if text.endswith("\n") else text + "\n")

    head = ("# Reference and decisions (formerly HANDOVER-NEXT sections 8-11)\n\n"
            "> Extracted verbatim from HANDOVER-NEXT.md on %s.  The living handover is\n"
            "> HANDOVER-NEXT.md; the session logs are in `sessions/`.\n\n" % STAMP)
    write(DECISIONS, head + "\n---\n".join(body[n] for n in (8, 9, 10, 11)))

    for n, rel in SESSIONS.items():
        src = ("---\n<!-- from HANDOVER-NEXT.md, section %d (extracted %s; full original:\n"
               "     %s) -->\n\n" % (n, STAMP, FULL))
        write("sessions/" + rel, src + body[n])

    intro = [
        "> Updated %s (Asia/Shanghai).  Sections 0-7 below are the living part:\n" % STAMP,
        "> current state, next steps, repo state, tools, pitfalls, safety, open questions.\n",
        "> The history (former sections 8-30) now lives in exactly one file per section -\n",
        "> see the index at the end of this file.  Read DOCS-INDEX.md for the whole map.\n",
        "> Companion documents: DOCS-INDEX.md, README.md, EUD.md, BINARIES.md,\n",
        "> linux-port/README.md.\n",
    ]
    idx = ["## History index (the former sections 8-30)\n\n",
           "Old references such as \"section 26\" or \"HANDOVER-NEXT.md 19.7\" still resolve\n",
           "through this table.  Nothing is duplicated: the file in the third column is\n",
           "the only copy.\n\n",
           "| old section | what | file |\n|---|---|---|\n"]
    for n in range(8, 31):
        if n in LINUX:
            rel = LINUX[n]
        elif n in SESSIONS:
            rel = "sessions/" + SESSIONS[n]
        else:
            rel = DECISIONS
        idx.append("| %d | %s | `%s` |\n" % (n, WHAT[n], rel))
    idx += [
        "\nRules that keep this file from growing again:\n\n",
        "* The living sections stay here; never append a session log to this file.\n",
        "* A new session writes one file - `sessions/NN-<topic>.md`, or\n",
        "  `linux-port/docs/NN-<topic>.md` for the Linux side - and adds one row above.\n",
        "* One fact, one file; mirrors point at the source and never carry their own copy.\n\n",
        "The complete pre-split text is kept verbatim in `%s`.\n" % FULL,
    ]
    h8 = heads[8][1]
    entry = "".join(lines[:2]) + "".join(intro) + "".join(lines[9:h8]) + "\n" + "".join(idx)
    write("HANDOVER-NEXT.md", entry)
    print("")
    print("old: %d lines / %d bytes" % (len(lines), len(text.encode())))
    print("new: %d lines / %d bytes" % (len(entry.splitlines()), len(entry.encode())))

if __name__ == "__main__":
    main()