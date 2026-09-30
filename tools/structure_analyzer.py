#!/usr/bin/env python3
"""SP-69 client-side structural analyzer — runs in the CUSTOMER's CI; emits DERIVED findings only.

Reimplements the graph-code technique (MIT, Vitali Avagyan) WITHOUT Memgraph: parse each source file
with Tree-sitter, extract function/method definitions + identifier references, and derive two
structural signals that text-based tools (Sonar's duplicated_lines_density) miss because the text
differs:

  * semantic duplication — functions with the same STRUCTURAL fingerprint (AST node-type shape, with
    identifier/literal TEXT ignored) in different locations: the same logic reimplemented.
  * dead code — a uniquely-named function never referenced anywhere in the repo and not an entry point
    (a conservative, name-based heuristic — labelled as such, never asserted as certain).

The customer's source NEVER leaves their CI: this prints ONLY derived findings (kind, file, symbol,
line, confidence, is_ai_marked) as JSON to stdout — never source text. is_ai_marked is set per finding
by git-blaming its location to the introducing commit and matching AI-agent commit trailers (SP-29).
Nothing is per-developer. Languages: Python, TS/JS, Go, Java, C#.

Usage:  structure_analyzer.py <repo_root>  >  findings.json
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

# ext -> (tree-sitter language name, {definition node types}, name is on field 'name')
_LANGS = {
    ".py": ("python", {"function_definition"}),
    ".ts": ("typescript", {"function_declaration", "method_definition", "generator_function_declaration"}),
    ".tsx": ("tsx", {"function_declaration", "method_definition", "generator_function_declaration"}),
    ".js": ("javascript", {"function_declaration", "method_definition", "generator_function_declaration"}),
    ".jsx": ("javascript", {"function_declaration", "method_definition", "generator_function_declaration"}),
    ".go": ("go", {"function_declaration", "method_declaration"}),
    ".java": ("java", {"method_declaration", "constructor_declaration"}),
    ".cs": ("csharp", {"method_declaration", "local_function_statement", "constructor_declaration"}),
}

_SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "vendor",
              ".terraform", "site-packages", "worker-layer", "__pycache__", ".next", "target", "bin", "obj"}

# Names that are legitimately never called from within the repo (entry points / framework hooks), so a
# "never referenced" verdict on them is a false positive — excluded from dead code.
_ENTRY_POINTS = {"main", "__init__", "__main__", "init", "setup", "run", "handler", "handle", "index",
                 "app", "application", "start", "configure", "register", "toString", "equals", "hashCode",
                 "Main", "ServeHTTP", "Dispose", "ConfigureServices", "Configure"}

# AI-agent commit-trailer markers (SP-29 subset) — used to flag a finding's region as AI-authored.
_AI_MARKERS = re.compile(
    r"(co-authored-by:\s*(claude|copilot|cursor|devin|codex|aider|gemini|sweep)\b"
    r"|(generated|written|authored)\s+(with|by)\s+(claude|copilot|cursor|chatgpt|gpt|ai)\b"
    r"|\[(claude|copilot|cursor|ai)\]|noreply@(anthropic|openai|cursor)\b)",
    re.IGNORECASE)

_MIN_FP_NODES = 20      # ignore tiny functions — trivial getters would all "match"
_MAX_FINDINGS = 500     # bound the payload; report the strongest first
_MAX_BLAME = 200        # bound git-blame calls


def _iter_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in _LANGS:
                yield os.path.join(dirpath, fn), ext


def _named_type_seq(node):
    """Pre-order sequence of named-node TYPES under `node` — the structural shape with identifier and
    literal TEXT discarded (only their node type is kept), so two functions differing only in names or
    literal values share a fingerprint."""
    out = []
    stack = [node]
    while stack:
        n = stack.pop()
        for c in reversed(n.named_children):
            out.append(c.type)
            stack.append(c)
    return out


def _def_name(node):
    nm = node.child_by_field_name("name")
    if nm is not None and nm.text:
        return nm.text.decode("utf-8", "replace")
    return None


def _analyze_file(path, root, lang_name, def_types, parser, ident_counts, defs, fingerprints):
    try:
        with open(path, "rb") as fh:
            src = fh.read()
    except OSError:
        return
    if len(src) > 2_000_000:   # skip very large/generated files
        return
    try:
        tree = parser.parse(src)
    except Exception:  # noqa: BLE001 — a parse failure on one file must not sink the run
        return
    rel = os.path.relpath(path, root)

    stack = [tree.root_node]
    while stack:
        n = stack.pop()
        if n.type.endswith("identifier") and n.text:
            ident_counts[n.text.decode("utf-8", "replace")] += 1
        if n.type in def_types:
            name = _def_name(n)
            seq = _named_type_seq(n)
            fp = hashlib.sha256(("\x1f".join(seq)).encode()).hexdigest()[:32] if len(seq) >= _MIN_FP_NODES else None
            rec = {"file": rel, "name": name, "line": n.start_point[0] + 1,
                   "size": len(seq), "fp": fp}
            defs.append(rec)
            if fp:
                fingerprints[fp].append(rec)
        stack.extend(n.children)


def _git_ai_marked(root, blame_cache):
    """Return a fn(file, line) -> bool that git-blames the line to its introducing commit and matches
    AI-agent trailers (SP-29). Bounded + fail-soft; regions we can't blame are simply not AI-marked."""
    calls = {"n": 0}

    def marked(file, line):
        if os.environ.get("SKIP_AI_BLAME") or calls["n"] >= _MAX_BLAME:
            return False
        key = (file, line)
        if key in blame_cache:
            return blame_cache[key]
        calls["n"] += 1
        res = False
        try:
            sha = subprocess.run(
                ["git", "-C", root, "blame", "-L", f"{line},{line}", "--porcelain", "--", file],
                capture_output=True, text=True, timeout=8).stdout.split("\n", 1)[0].split(" ")[0]
            if sha and len(sha) >= 7:
                msg = subprocess.run(["git", "-C", root, "log", "-1", "--format=%B", sha],
                                     capture_output=True, text=True, timeout=8).stdout
                res = bool(_AI_MARKERS.search(msg or ""))
        except Exception:  # noqa: BLE001
            res = False
        blame_cache[key] = res
        return res

    return marked


def analyze(root):
    from tree_sitter_language_pack import get_parser

    parsers = {}
    ident_counts = Counter()
    def_name_counts = Counter()
    defs = []
    fingerprints = defaultdict(list)

    for path, ext in _iter_files(root):
        lang_name, def_types = _LANGS[ext]
        parser = parsers.get(lang_name)
        if parser is None:
            try:
                parser = parsers[lang_name] = get_parser(lang_name)
            except Exception:  # noqa: BLE001 — an unavailable grammar: that language is "not analyzed"
                parsers[lang_name] = None
                continue
        if parser is None:
            continue
        _analyze_file(path, root, lang_name, def_types, parser, ident_counts, defs, fingerprints)

    for d in defs:
        if d["name"]:
            def_name_counts[d["name"]] += 1

    blame_cache = {}
    ai_marked = _git_ai_marked(root, blame_cache)
    findings = []

    # --- semantic duplication: >= 2 locations sharing a structural fingerprint ---
    for fp, group in fingerprints.items():
        locs = {(g["file"], g["name"] or f"<anon>@{g['line']}"): g for g in group}
        if len(locs) < 2:
            continue
        members = list(locs.values())
        size = members[0]["size"]
        confidence = round(min(0.9, 0.5 + size / 400.0), 2)   # bigger shape = stronger; never 1.0
        is_ai = any(ai_marked(m["file"], m["line"]) for m in members)
        findings.append({
            "kind": "dup",
            "locations": [{"file": m["file"], "symbol": m["name"] or "<anonymous>", "line": m["line"]}
                          for m in members[:12]],
            "confidence": confidence,
            "size": size,
            "is_ai_marked": is_ai,
        })

    # --- dead code: a uniquely-named function never referenced anywhere, not an entry point ---
    for d in defs:
        name = d["name"]
        if not name or name in _ENTRY_POINTS or name.startswith(("test", "Test", "_test")):
            continue
        if def_name_counts[name] != 1:          # overloaded/ambiguous name -> skip (avoid false positives)
            continue
        if ident_counts.get(name, 0) > 1:       # referenced somewhere beyond its own definition -> alive
            continue
        findings.append({
            "kind": "dead",
            "locations": [{"file": d["file"], "symbol": name, "line": d["line"]}],
            "confidence": 0.5,                  # name-based heuristic — labelled, never asserted
            "size": d["size"],
            "is_ai_marked": ai_marked(d["file"], d["line"]),
        })

    findings.sort(key=lambda f: (f["kind"] != "dup", -f["confidence"], -f.get("size", 0)))
    return findings[:_MAX_FINDINGS]


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    findings = analyze(root)
    out = {
        "repository": os.environ.get("GITHUB_REPOSITORY", ""),
        "commit_sha": os.environ.get("GITHUB_SHA", ""),
        "branch": os.environ.get("GITHUB_REF_NAME", "") or "main",
        "tool": "8manager-structure",
        "findings": findings,
    }
    json.dump(out, sys.stdout)


if __name__ == "__main__":
    main()
