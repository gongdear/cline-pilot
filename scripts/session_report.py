#!/usr/bin/env python3
"""session_report.py — summarize a Cline session + hard engineering evidence. / Cline 会话活动摘要 + 工程进度硬证据

Usage / 用法:
  python3 session_report.py                # latest session, last 10 msgs, cwd evidence / 最新会话最近10条+当前目录证据
  python3 session_report.py 15 /path/to/repo

Output / 输出:
  - recent messages of the session (role / text / tool / result summary)
    会话最近消息（角色 / 文本 / 工具调用 / 结果摘要）
  - hard repo evidence: branch, git status, last commit, newest surefire report lines
    工程硬证据：分支、git status、最近 commit、最新 surefire 报告首行

Read-only — never modifies files. stdlib only. / 只读，不改任何文件；仅标准库。
"""
import glob
import json
import os
import subprocess
import sys


SESSIONS_ROOT = os.path.join(os.path.expanduser("~"), ".cline", "data", "sessions")


def latest_session_id():
    """Return the most recently modified Cline session directory name. / 返回最近更新的 Cline 会话目录名。"""
    if not os.path.isdir(SESSIONS_ROOT):
        return None
    entries = []
    for e in os.listdir(SESSIONS_ROOT):
        p = os.path.join(SESSIONS_ROOT, e)
        if os.path.isdir(p):
            entries.append((os.path.getmtime(p), e))
    return max(entries)[1] if entries else None


def load_session(sid):
    p = os.path.join(SESSIONS_ROOT, sid, sid + ".messages.json")
    if not os.path.exists(p):
        return None, None
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    return d.get("messages", []), d.get("updated_at")


def summarize(msgs, n):
    """Flatten the last N messages into readable one-line entries. / 把最近 N 条消息展平成可读的逐行摘要。"""
    lines = []
    for m in (msgs or [])[-n:]:
        role = m.get("role", "?")
        content = m.get("content")
        if isinstance(content, str):
            lines.append("[%s] %s" % (role, content[:160].strip()))
            continue
        for c in content or []:
            t = c.get("type")
            if t == "text":
                lines.append("[%s|text] %s" % (role, (c.get("text") or "")[:160].strip()))
            elif t in ("tool_use", "toolCall", "tool"):
                name = c.get("name") or c.get("toolName") or ""
                inp = c.get("input") or c.get("arguments") or {}
                lines.append("[%s|tool:%s] %s" % (role, name, json.dumps(inp, ensure_ascii=False)[:150]))
            elif t == "tool_result":
                r = c.get("content") or c.get("output") or ""
                r = r if isinstance(r, str) else json.dumps(r, ensure_ascii=False)
                lines.append("[%s|result] %s" % (role, str(r)[:150]))
            else:
                lines.append("[%s|%s] %s" % (role, t, json.dumps(c, ensure_ascii=False)[:120]))
    return lines


def sh(cmd, cwd):
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=60)
        out = r.stdout.strip()
        return out if out else "(exit %d %s)" % (r.returncode, r.stderr.strip()[:60])
    except Exception as e:
        return "(error %s)" % e


def repo_evidence(root):
    """Collect hard evidence: branch / status / commit / newest surefire lines. / 收集硬证据：分支、状态、commit、最新 surefire 报告行。"""
    if not os.path.exists(os.path.join(root, ".git")) and not os.path.isdir(os.path.join(root, ".git")):
        try:
            r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root, capture_output=True, text=True, timeout=20)
            if r.returncode != 0:
                return ["(not a git repo: %s)" % root]
            root = r.stdout.strip()
        except Exception:
            return ["(not a git repo: %s)" % root]
    lines = [
        "branch   : %s" % sh("git branch --show-current", root),
        "status   : %s" % (sh("git status --short | head -15", root) or "(clean)"),
        "commit   : %s" % sh("git log -1 --pretty='%h %s'", root),
    ]
    reports = sorted(
        glob.glob(os.path.join(root, "**", "target", "surefire-reports", "*.txt"), recursive=True),
        key=lambda p: os.path.getmtime(p), reverse=True,
    )[:6]
    for f in reports:
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                first = fh.readline().strip()
            lines.append("surefire : %s | %s" % (os.path.relpath(f, root), first))
        except OSError:
            pass
    if not reports:
        lines.append("surefire : (no reports yet)")
    return lines


def main(argv):
    n, repo, sid = 10, os.getcwd(), None
    for a in argv:
        if a.isdigit() and int(a) < 500:
            n = max(1, int(a))
        elif os.path.isdir(os.path.expanduser(a)):
            repo = os.path.expanduser(a)
        else:
            sid = a
    sid = sid or latest_session_id()
    if not sid:
        print("no cline sessions found under", SESSIONS_ROOT)
        return 1
    print("== session: %s ==" % sid)
    msgs, updated = load_session(sid)
    if msgs is None:
        print("(messages.json not found)")
        return 1
    print("updated_at: %s | total messages: %d" % (updated, len(msgs)))
    print("-- recent activity --")
    for line in summarize(msgs, n):
        print(line)
    print("-- repo evidence: %s --" % repo)
    for line in repo_evidence(repo):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
