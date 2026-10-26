#!/usr/bin/env python3
"""Generate the session/evidence map without copying experimental conclusions."""
from pathlib import Path
import argparse
import fnmatch
import json
import re


def title(path):
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("# "):
            return line[2:].strip().replace("|", "\\|")
    return path.stem


def order(path):
    match = re.match(r"(\d+)-", path.name)
    return (0, int(match[1]), path.name) if match else (1, 0, path.name)


def render(root):
    manifest_path = root / "linux-port/scripts/docs-sync-manifest.json"
    exclude = json.loads(manifest_path.read_text(encoding="utf-8")).get("exclude", [])

    def private_evidence(name):
        probe = f"reference/{name}/README.md"
        return any(fnmatch.fnmatchcase(probe, pattern) for pattern in exclude)

    lines = [
        "# 会话与证据索引", "",
        "用途：定位现有会话及reference证据。结构整理：2026-10-14；由generate-session-index.py按文件清单生成，保持原始记录的标题与结论。",
        "",
        "最后核对的部署见[检查点](../NEXT-SESSION.md)，当前操作规则见[WORKING-BOUNDARIES](../WORKING-BOUNDARIES.md)，验收范围见[硬件清单](../linux-port/docs/HARDWARE-STATUS.md)。", "",
        "## 会话文件", "", "| 记录 | 原文标题 |", "| --- | --- |",
    ]
    for path in sorted((root / "sessions").glob("*.md"), key=order):
        if path.name != "INDEX.md":
            lines.append(f"| [{path.name}](<{path.name}>) | {title(path)} |")
    lines += ["", "## Reference目录", "",
              "部分阶段只保存了reference记录，可直接从这里阅读；不要求再复制一份会话正文。", "",
              "| 目录 | 原文标题 |", "| --- | --- |"]
    evidence = list((root / "reference").glob("*/README.md"))
    def evidence_order(path):
        match = re.fullmatch(r"(kernel|rx)(\d+)", path.parent.name)
        return (match[1], int(match[2]), "") if match else ("z", 0, path.parent.name)
    for path in sorted(evidence, key=evidence_order):
        name = path.parent.name
        label = f"{name}（本地私人证据）" if private_evidence(name) else f"[{name}](<../reference/{name}/README.md>)"
        lines.append(f"| {label} | {title(path)} |")
    lines += ["", "## 早期拆分与快照", "",
              "- [旧8—30节映射](../HANDOVER-NEXT.md#旧830节映射)",
              "- [Linux技术与19—28节](../linux-port/docs/00-INDEX.md)",
              "- [旧决策8—11节](../reference/DECISIONS.md)",
              "- [2026-10-14维护前逐字快照](../archive/docs-before-maintenance-2026-10-14/README.md)"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = args.workspace / "sessions/INDEX.md"
    expected = render(args.workspace)
    if args.check:
        if not target.is_file() or target.read_text(encoding="utf-8") != expected:
            raise SystemExit("STALE: sessions/INDEX.md; regenerate with generate-session-index.py")
        print("Session/evidence index is current.")
    else:
        target.write_text(expected, encoding="utf-8", newline="\n")
        print("Generated sessions/INDEX.md.")


if __name__ == "__main__":
    main()
