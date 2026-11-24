#!/usr/bin/env python3
"""READ-ONLY audit measurement harness (Phase 1 discovery).

Produces, under docs/plans/master-audit-2026-11-23/evidence/:
  - full-file-tree.txt        categorised inventory of in-scope files
  - inventory.json            machine-readable summary
  - complexity.csv            per-source-file metrics (Python + web + astro)
  - complexity-notebooks.csv  notebook metrics (kept separate)
  - raw-measurements.json     full per-file detail (evidence)

Scope = git-tracked files plus git non-ignored untracked files. No ignored path is
read. No repository file outside evidence/ is written.

Run with: uv run python evidence/measurement/measure.py   (portable; no absolute paths)

REVISION PINNING: every content measurement reads byte-identical blobs exported with
`git archive HEAD`, materialised into a temporary snapshot directory. The worktree is
never used as the content source, so a dirty or concurrently edited worktree cannot
change the measured numbers. Worktree state is recorded for verification only.
"""

from __future__ import annotations

import ast
import csv
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import tokenize
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EVID = SCRIPT_DIR.parent


def _repo_root() -> Path:
    res = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=EVID, capture_output=True, text=True
    )
    return Path(res.stdout.strip())


REPO = _repo_root()
TS_HELPER = SCRIPT_DIR / "ts_measure.mjs"
HEAD = subprocess.run(
    ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True
).stdout.strip()

SNAPSHOT_DIR = Path(
    os.environ.get("AUDIT_SNAPSHOT_DIR")
    or (Path(tempfile.gettempdir()) / f"audit-snapshot-{HEAD[:12]}")
)
TMP_DIR = SNAPSHOT_DIR.parent / (SNAPSHOT_DIR.name + "-tmp")


def snapshot_manifest() -> dict:
    """Materialise the pinned HEAD tree once and describe how it was obtained."""
    counts = {"files": 0, "bytes": 0}
    marker = SNAPSHOT_DIR / ".audit-snapshot-complete"
    if not marker.exists():
        archive = subprocess.run(
            ["git", "archive", "--format=tar", HEAD],
            cwd=REPO,
            capture_output=True,
            check=True,
        ).stdout
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
            tar.extractall(SNAPSHOT_DIR, filter="data")
        marker.write_text(HEAD + "\n")
    for f in SNAPSHOT_DIR.rglob("*"):
        if f.is_file() and f.name != ".audit-snapshot-complete":
            counts["files"] += 1
            counts["bytes"] += f.stat().st_size
    worktree = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    return {
        "content_source": "git archive HEAD materialised snapshot (pinned revision)",
        "snapshot_dir": str(SNAPSHOT_DIR),
        "head": HEAD,
        "snapshot_files": counts["files"],
        "snapshot_bytes": counts["bytes"],
        "worktree_tracked_changes": worktree.stdout.strip(),
        "worktree_tracked_clean": worktree.stdout.strip() == "",
        "verification_commands": [
            "git rev-parse HEAD",
            "git archive --format=tar HEAD | tar -tf -",
            "git status --porcelain --untracked-files=no",
        ],
    }


def ensure_snapshot() -> None:
    """Import-time hook so indexes.py shares the identical pinned snapshot."""
    snapshot_manifest()


PY_EXT = {".py"}
WEB_CODE_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".astro", ".css"}
SOURCE_EXT = PY_EXT | WEB_CODE_EXT

# --------------------------------------------------------------------------- #
# 1. File enumeration
# --------------------------------------------------------------------------- #

# Ignored-by-git paths that exist on disk but are out of scope (never enumerated):
EXCLUDED_IGNORED = [
    ".git/",
    ".env",
    ".env.keys",
    "node_modules/",
    "app/node_modules/",
    ".venv/",
    "__pycache__/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".mypy_cache/",
    ".hypothesis/",
    ".coverage",
    "coverage.xml",
    "htmlcov/",
    "build/",
    "dist/",
    "app/dist/",
    "app/.astro/",
    "data/pipeline/",
    "data/analysis/",
    "data/forecasts/",
    "data/cache/",
    "data/logs/",
    "data/manual/ (except tracked *.md)",
    "playwright-report/",
    "test-results/",
    ".claude/ (ignored copy; tracked .claude/*.md still in scope)",
    ".context7/ (ignored; tracked .context7/*.md still in scope)",
    ".worktrees/",
    "*.parquet under data/pipeline, *.pkl, *.bak",
]

EXCLUDED_VENDORED_NOTE = (
    "No tracked vendored/third-party source trees exist. node_modules, .venv and "
    "app/node_modules are git-ignored and were not enumerated. data/raw/external/datagov/*.geojson "
    "are downloaded upstream datasets (tracked, data category), not source."
)


AUDIT_DIR = "docs/plans/master-audit-2026-11-23/"


def enumerate_files() -> tuple[list[str], list[str], list[str]]:
    """Return (canonical_tracked_snapshot, supplemental_untracked, self_excluded).

    Canonical scope is fixed to the git-tracked snapshot at HEAD. Audit artifacts
    written by this harness (and concurrent audit workers) are untracked, so they
    are reported as *supplemental* and never counted in any statistic. Anything
    under AUDIT_DIR is additionally hard-excluded from the supplemental list so
    the audit cannot count itself.
    """
    tracked = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.split("\0")
    tracked = sorted(p for p in tracked if p)

    untracked_all = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split("\0")
    untracked_all = sorted(p for p in untracked_all if p)
    supplemental = [p for p in untracked_all if not p.startswith(AUDIT_DIR)]
    self_excluded = [p for p in untracked_all if p.startswith(AUDIT_DIR)]
    return tracked, supplemental, self_excluded


# --------------------------------------------------------------------------- #
# 2. Categorisation
# --------------------------------------------------------------------------- #

ROOT_DOCS = {"README.md", "QUICKSTART.md", "AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md"}
ROOT_CONFIG = {
    "pyproject.toml",
    "uv.lock",
    ".pre-commit-config.yaml",
    ".gitignore",
    ".bun-version",
    ".env.example",
    ".secrets.baseline",
    "package.json",
}
APP_CONFIG = {
    "app/package.json",
    "app/tsconfig.json",
    "app/bun.lock",
    "app/astro.config.mjs",
    "app/tailwind.config.mjs",
    "app/playwright.config.ts",
    "app/.bun-version",
    "app/.gitignore",
}


def category(path: str) -> str:
    if path in ROOT_CONFIG:
        if path in {"pyproject.toml", "uv.lock"}:
            return "config:python-manifest"
        if path == "package.json":
            return "config:web-manifest"
        if path == ".secrets.baseline":
            return "config:secret-scan-baseline"
        if path == ".env.example":
            return "config:env-template"
        return "config:repo"
    if path in ROOT_DOCS:
        return "docs:root"
    if path in APP_CONFIG:
        return "web:config"
    if path == "main.py":
        return "python:entrypoint"
    if path.startswith("src/") and path.endswith(".py"):
        return "python:source"
    if path.startswith("tests/"):
        return "python:test"
    if path.startswith("scripts/"):
        return "python:script"
    if path.startswith("app/tests/"):
        return "web:test"
    if path.startswith("app/src/"):
        return "web:source"
    if path.startswith("app/scripts/"):
        return "web:script"
    if path.startswith("app/public/"):
        return "artifact:published-web-data"
    if path.startswith("notebooks/"):
        return "notebook"
    if path.startswith("docs/"):
        return "docs:evidence-and-plans"
    if path.startswith((".agents/", ".claude/", ".context7/", "prompts/")):
        return "docs:agent-context"
    if path.startswith("assets/"):
        return "design-asset"
    if path.startswith("data/"):
        return "data:tracked-input"
    if path.startswith(".github/"):
        return "ci:workflow"
    if path in {"app/README.md", "app/CHANGELOG.md"}:
        return "docs:web"
    if path.startswith("app/"):
        return "web:other"
    return "other"


def is_binary(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:4096]
    except OSError:
        return True
    return b"\0" in chunk


# --------------------------------------------------------------------------- #
# 3. Python metrics (ast)
# --------------------------------------------------------------------------- #

PY_BLOCK = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Match,
)
# ast.TryStar exists only on 3.11+; we run on 3.12 so it is present.
if hasattr(ast, "TryStar"):
    PY_BLOCK = PY_BLOCK + (ast.TryStar,)

STDLIB = set(sys.stdlib_module_names)
FIRST_PARTY_ROOTS = {"egg_n_bacon_housing", "tests", "conftest", "scripts"}


def py_code_lines(text: str) -> tuple[int, int, int]:
    """Return (code, comment, blank) physical line counts via tokenize."""
    code = comment = blank = 0
    comment_lines: set[int] = set()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.COMMENT:
                comment_lines.add(tok.start[0])
    except (tokenize.TokenError, IndentationError):
        comment_lines = set()
    for i, raw in enumerate(text.split("\n"), start=1):
        if raw.strip() == "":
            blank += 1
        elif i in comment_lines:
            comment += 1
        else:
            code += 1
    return code, comment, blank


def py_max_depth(node: ast.AST, depth: int = 0) -> int:
    deepest = depth
    for field, value in ast.iter_fields(node):
        items = value if isinstance(value, list) else [value]
        for item in items:
            if not isinstance(item, ast.AST):
                continue
            indent = 0
            if field in {"body", "orelse", "finalbody", "handlers", "cases"}:
                indent = 1 if isinstance(item, PY_BLOCK) else 0
                # elif / else branches of an If are not deeper than the If itself
                if isinstance(node, ast.If) and field == "orelse" and isinstance(item, ast.If):
                    indent = 0
            sub = py_max_depth(item, depth + indent)
            if sub > deepest:
                deepest = sub
    return deepest


def py_measure(rel: str) -> dict:
    abs_path = SNAPSHOT_DIR / rel
    text = abs_path.read_text(encoding="utf-8", errors="replace")
    lines = len(text.splitlines())
    code, comment, blank = py_code_lines(text)
    rec = {
        "path": rel,
        "ext": ".py",
        "lines": lines,
        "code_lines": code,
        "comment_lines": comment,
        "blank_lines": blank,
        "method": "python-ast+tokenize",
        "limitations": (
            "nesting = max block-statement nesting from module level "
            "(if/for/while/with/try/match/def/class); elif/else not deeper; "
            "lambda/comprehension bodies not counted; not cyclomatic complexity"
        ),
        "parse_ok": True,
        "parse_errors": [],
        "exported_symbols": 0,
        "exported_names": [],
        "external_imports": 0,
        "external_import_names": [],
        "internal_imports": 0,
        "defs": 0,
        "classes": 0,
        "methods": 0,
        "has_all": False,
        "max_nesting": 0,
        "toplevel_public": [],
        "stdlib_imports": [],
    }
    try:
        tree = ast.parse(text, filename=rel)
    except (SyntaxError, ValueError) as exc:
        rec["parse_ok"] = False
        rec["parse_errors"] = [f"{type(exc).__name__}: {exc}"]
        # lexical fallback, explicitly labelled
        rec["method"] = "lexical-fallback (ast.parse failed)"
        rec["limitations"] = "parse failed; nesting/deflist are lexical estimates only"
        rec["max_nesting"] = max(
            (len(m.group(1)) // 4 for m in re.finditer(r"^( +)\S", text, re.M)), default=0
        )
        rec["exported_symbols"] = len(
            re.findall(r"^(?:async\s+)?(?:def|class)\s+(?!_)\w+", text, re.M)
        )
        lex_ext = sorted(
            {
                m.group(1).split(".")[0]
                for m in re.finditer(r"^\s*(?:from|import)\s+([\w.]+)", text, re.M)
            }
            - STDLIB
            - FIRST_PARTY_ROOTS
        )
        rec["external_import_names"] = lex_ext
        rec["external_imports"] = len(lex_ext)
        return rec

    rec["max_nesting"] = py_max_depth(tree)
    ext: set[str] = set()
    internal = 0
    stdlib: set[str] = set()
    all_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in FIRST_PARTY_ROOTS:
                    internal += 1
                elif root in STDLIB:
                    stdlib.add(root)
                else:
                    ext.add(root)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                internal += 1
                continue
            root = (node.module or "").split(".")[0]
            if not root:
                continue
            if root in FIRST_PARTY_ROOTS:
                internal += 1
            elif root in STDLIB:
                stdlib.add(root)
            else:
                ext.add(root)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if getattr(node, "parent_is_class", False):
                rec["methods"] += 1
            else:
                rec["defs"] += 1
        elif isinstance(node, ast.ClassDef):
            rec["classes"] += 1
            rec["methods"] += sum(
                1 for b in node.body if isinstance(b, ast.FunctionDef | ast.AsyncFunctionDef)
            )

    # top-level public names (definition order, no nesting)
    top_public: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            if not node.name.startswith("_"):
                top_public.append(node.name)
        elif isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and not tgt.id.startswith("_") and tgt.id.isupper():
                    top_public.append(tgt.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            if not name.startswith("_") and name.isupper():
                top_public.append(name)
        elif isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
        ):
            rec["has_all"] = True
            try:
                value = ast.literal_eval(node.value)
                all_names = [v for v in value if isinstance(v, str)]
            except (ValueError, TypeError):
                all_names = []

    if all_names:
        rec["exported_names"] = all_names
        rec["exported_symbols"] = len(all_names)
    else:
        rec["exported_names"] = top_public
        rec["exported_symbols"] = len(top_public)
    rec["toplevel_public"] = top_public
    rec["external_import_names"] = sorted(ext)
    rec["external_imports"] = len(ext)
    rec["internal_imports"] = internal
    rec["stdlib_imports"] = sorted(stdlib)
    return rec


# --------------------------------------------------------------------------- #
# 4. Web metrics (typescript compiler via node)
# --------------------------------------------------------------------------- #


def web_measure(rel_paths: list[str]) -> tuple[dict, dict]:
    kind_of = {
        ".ts": "ts",
        ".tsx": "tsx",
        ".js": "js",
        ".jsx": "jsx",
        ".mjs": "mjs",
        ".cjs": "cjs",
        ".astro": "astro",
    }
    payload = [{"path": p, "kind": kind_of[Path(p).suffix]} for p in rel_paths]
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    tmp_in = TMP_DIR / "_ts_input.json"
    tmp_in.write_text(json.dumps(payload))
    proc = subprocess.run(
        ["node", str(TS_HELPER), str(SNAPSHOT_DIR), str(tmp_in), str(REPO)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"ts helper failed: {proc.stderr[:2000]}")
    data = json.loads(proc.stdout)
    if data.get("error"):
        raise SystemExit(data["error"])
    return data["files"], {"ts_version": data.get("tsVersion")}


# --------------------------------------------------------------------------- #
# 5. Notebook metrics (json, lexical)
# --------------------------------------------------------------------------- #


def notebook_measure(rel: str) -> dict:
    abs_path = SNAPSHOT_DIR / rel
    raw = abs_path.read_text(encoding="utf-8", errors="replace")
    n_lines = len(raw.splitlines())
    try:
        nb = json.loads(raw)
        cells = nb.get("cells", [])
        code_cells = [c for c in cells if c.get("cell_type") == "code"]
        md_cells = [c for c in cells if c.get("cell_type") == "markdown"]
        code_lines = sum(
            len([ln for ln in "".join(c.get("source", [])).splitlines() if ln.strip()])
            for c in code_cells
        )
        inputs = 0
        for c in code_cells:
            src = "".join(c.get("source", []))
            try:
                inputs += sum(1 for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Call))
            except SyntaxError:
                pass
        return {
            "path": rel,
            "lines": n_lines,
            "code_cells": len(code_cells),
            "markdown_cells": len(md_cells),
            "code_lines": code_lines,
            "call_sites": inputs,
            "method": "ipynb-json+lexical-code-cells",
            "limitations": "not executed; cell magics/shell escapes not parsed as Python",
        }
    except json.JSONDecodeError as exc:
        return {
            "path": rel,
            "lines": n_lines,
            "code_cells": 0,
            "markdown_cells": 0,
            "code_lines": 0,
            "call_sites": 0,
            "method": "ipynb-json (malformed)",
            "limitations": f"JSON parse failed: {exc}",
        }


# --------------------------------------------------------------------------- #
# 6. Dead-code candidates (UNCONFIRMED, identifier grep only)
# --------------------------------------------------------------------------- #


def dead_code_candidates(
    py_recs: list[dict], web_recs: list[dict], all_py: list[str], all_web: list[str]
) -> dict:
    py_texts = {}
    for p in all_py:
        py_texts[p] = (SNAPSHOT_DIR / p).read_text(encoding="utf-8", errors="replace")
    web_texts = {}
    for p in all_web:
        web_texts[p] = (SNAPSHOT_DIR / p).read_text(encoding="utf-8", errors="replace")

    py_cands = []
    for rec in py_recs:
        if not rec["path"].startswith("src/"):
            continue
        for name in rec["exported_names"]:
            if name in {"__version__"}:
                continue
            pat = re.compile(rf"(?<![\w.]){re.escape(name)}(?![\w])")
            hits = [p for p, txt in py_texts.items() if p != rec["path"] and pat.search(txt)]
            if not hits:
                py_cands.append({"symbol": name, "defined_in": rec["path"], "referencing_files": 0})

    web_cands = []
    for rec in web_recs:
        if not rec["path"].startswith("app/src/"):
            continue
        for name in rec.get("exported_names", []):
            if name in {"default", "*"} or name.startswith("*"):
                continue
            if not re.fullmatch(r"[A-Za-z_$][\w$]*", name):
                continue
            pat = re.compile(rf"(?<![\w$]){re.escape(name)}(?![\w$])")
            hits = [p for p, txt in web_texts.items() if p != rec["path"] and pat.search(txt)]
            if not hits:
                web_cands.append(
                    {"symbol": name, "defined_in": rec["path"], "referencing_files": 0}
                )
    return {"python": py_cands, "web": web_cands}


# --------------------------------------------------------------------------- #
# 7. Coverage report inspection (read-only; artifact is git-ignored)
# --------------------------------------------------------------------------- #


def _describe_cobertura(p: Path, label: str) -> dict:
    """Read a Cobertura XML header verbatim. Values are quoted, never re-derived."""
    import datetime

    out: dict = {"artifact": label, "path": str(p), "present": p.exists()}
    if not p.exists():
        return out
    raw = p.read_text(encoding="utf-8", errors="replace")
    st = p.stat()
    m = re.search(r"<coverage[^>]*>", raw)
    attrs = dict(re.findall(r'(\w[\w-]*)="([^"]*)"', m.group(0))) if m else {}
    out["file_mtime_utc"] = datetime.datetime.fromtimestamp(st.st_mtime, datetime.UTC).isoformat()
    out["size_bytes"] = st.st_size
    out["header_attributes"] = attrs
    out["classes_reported"] = len(re.findall(r"<class\b", raw))
    out["files_reported"] = len(re.findall(r"<class\b", raw))
    ts = attrs.get("timestamp")
    if ts and ts.isdigit():
        out["generated_utc"] = datetime.datetime.fromtimestamp(
            int(ts) / 1000, datetime.UTC
        ).isoformat()
    for key in ("lines-valid", "lines-covered"):
        if attrs.get(key, "").isdigit():
            out[key.replace("-", "_")] = int(attrs[key])
    if "lines_valid" in out and "lines_covered" in out:
        out["lines_missed"] = out["lines_valid"] - out["lines_covered"]
        out["line_rate_recomputed"] = round(out["lines_covered"] / max(1, out["lines_valid"]), 4)
        out["line_rate_declared"] = attrs.get("line-rate")
        out["declared_matches_recomputed"] = (
            abs(float(attrs.get("line-rate", 0)) - out["line_rate_recomputed"]) < 0.0002
        )
    return out


def coverage_report() -> dict:
    """Report the two distinct coverage artifacts without conflating them.

    * repo `coverage.xml`  = stale git-ignored artifact left in the worktree
    * /tmp/master-audit-coverage.xml = execution performed by this audit
    """
    return {
        "stale_worktree_artifact": _describe_cobertura(
            REPO / "coverage.xml", "stale-worktree-artifact"
        ),
        "fresh_audit_execution": _describe_cobertura(
            Path("/tmp/master-audit-coverage.xml"), "fresh-audit-execution"
        ),
        "htmlcov_present": (REPO / "htmlcov").is_dir(),
        "note": (
            "These are two different runs of the same suite. The worktree artifact is "
            "stale (timestamp 2026-11-22) and reports 96/4076 covered; the fresh audit "
            "execution (timestamp 2026-11-23) reports 3894/4076. Neither is a code "
            "finding; both are reported verbatim from the XML headers."
        ),
    }


# --------------------------------------------------------------------------- #
# 8. Manifest discovery
# --------------------------------------------------------------------------- #

MANIFEST_PATTERNS = [
    "pyproject.toml",
    "uv.lock",
    "package.json",
    "app/package.json",
    "app/bun.lock",
    "app/tsconfig.json",
    "app/astro.config.mjs",
    "app/tailwind.config.mjs",
    "app/playwright.config.ts",
    ".pre-commit-config.yaml",
    ".github/workflows/ci.yml",
    ".github/workflows/deploy.yml",
    ".secrets.baseline",
    ".env.example",
    ".bun-version",
    "app/.bun-version",
    "app/.gitignore",
    ".gitignore",
    "data/catalog/descriptions.yml",
]


def manifests() -> list[dict]:
    res = []
    for rel in MANIFEST_PATTERNS:
        p = SNAPSHOT_DIR / rel
        if p.exists():
            res.append(
                {
                    "path": rel,
                    "bytes": p.stat().st_size,
                    "tracked": rel in TRACKED_SET,
                }
            )
    return res


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def main() -> None:
    global TRACKED_SET
    EVID.mkdir(parents=True, exist_ok=True)
    snapshot_info = snapshot_manifest()
    tracked, supplemental_untracked, self_excluded = enumerate_files()
    TRACKED_SET = set(tracked)
    # canonical scope = fixed HEAD-tracked snapshot; audit-written files never counted
    in_scope = tracked

    cats = Counter(category(p) for p in in_scope)
    by_cat: dict[str, list[str]] = defaultdict(list)
    for p in in_scope:
        by_cat[category(p)].append(p)

    # ---- source measurement sets ----
    py_files = [p for p in in_scope if p.endswith(".py")]
    web_files = [p for p in in_scope if Path(p).suffix in WEB_CODE_EXT and not p.endswith(".css")]
    css_files = [p for p in in_scope if p.endswith(".css")]
    ipynb_files = [p for p in in_scope if p.endswith(".ipynb")]

    py_recs = [py_measure(p) for p in py_files]
    web_recs_map, web_meta = web_measure(web_files)
    web_recs = []
    for p in web_files:
        r = web_recs_map[p]
        if r.get("error"):
            r.setdefault("lines", 0)
            r.setdefault("exported_names", [])
            r.setdefault("external_import_names", [])
            r.setdefault("max_nesting", None)
            r.setdefault("parse_errors", [r["error"]])
            r["method"] = "failed"
            r["limitations"] = "parser crashed on this file"
        web_recs.append(r)

    css_recs = []
    for p in css_files:
        text = (SNAPSHOT_DIR / p).read_text(encoding="utf-8", errors="replace")
        css_recs.append(
            {
                "path": p,
                "lines": len(text.splitlines()),
                "code_lines": len([ln for ln in text.splitlines() if ln.strip()]),
                "exported_symbols": 0,
                "exported_names": [],
                "external_imports": 0,
                "external_import_names": [],
                "max_nesting": max(
                    (ln.count("{") for ln in text.splitlines()),
                    default=0,
                ),
                "method": "lexical-css",
                "limitations": "brace characters per line only; not an AST metric",
                "parse_ok": True,
                "parse_errors": [],
            }
        )

    all_recs = py_recs + web_recs + css_recs

    # ---- complexity.csv ----
    csv_path = EVID / "complexity.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "path",
                "lines",
                "exported_public_symbols",
                "external_imports",
                "max_nesting_estimate",
                "method_limitations",
                "size_flag",
                "ext",
                "category",
                "code_lines",
                "comment_lines",
                "internal_imports",
                "parse_ok",
                "parse_errors",
                "external_import_modules",
            ]
        )
        for r in sorted(all_recs, key=lambda x: (-x["lines"], x["path"])):
            n_lines = r["lines"]
            flag = ">500" if n_lines > 500 else (">300" if n_lines > 300 else "")
            if not r.get("parse_ok", True):
                flag = (flag + "|parse_error").lstrip("|")
            lim = r.get("limitations", "")
            w.writerow(
                [
                    r["path"],
                    n_lines,
                    r.get("exported_symbols", 0),
                    r.get("external_imports", 0),
                    r.get("max_nesting", ""),
                    lim,
                    flag,
                    Path(r["path"]).suffix,
                    category(r["path"]),
                    r.get("code_lines", ""),
                    r.get("comment_lines", ""),
                    r.get("internal_imports", ""),
                    "yes" if r.get("parse_ok", True) else "no",
                    "; ".join(r.get("parse_errors", []))[:300],
                    ", ".join(r.get("external_import_names", [])[:12]),
                ]
            )

    # ---- notebooks csv ----
    nb_recs = [notebook_measure(p) for p in ipynb_files]
    with (EVID / "complexity-notebooks.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "path",
                "lines",
                "code_cells",
                "markdown_cells",
                "code_lines",
                "call_sites",
                "method",
                "limitations",
            ]
        )
        for r in sorted(nb_recs, key=lambda x: -x["lines"]):
            w.writerow(
                [
                    r["path"],
                    r["lines"],
                    r["code_cells"],
                    r["markdown_cells"],
                    r["code_lines"],
                    r["call_sites"],
                    r["method"],
                    r["limitations"],
                ]
            )

    # ---- LOC aggregation ----
    def loc(subset: list[dict]) -> dict:
        return {
            "files": len(subset),
            "lines": sum(r["lines"] for r in subset),
            "code_lines": sum(r.get("code_lines", 0) for r in subset),
            "comment_lines": sum(r.get("comment_lines", 0) for r in subset),
            "blank_lines": sum(r.get("blank_lines", 0) for r in subset),
        }

    py_src = [r for r in py_recs if r["path"].startswith("src/")]
    py_tests = [r for r in py_recs if r["path"].startswith("tests/")]
    py_scripts = [r for r in py_recs if r["path"].startswith("scripts/")]
    py_entry = [r for r in py_recs if r["path"] == "main.py"]
    web_src = [r for r in web_recs if r["path"].startswith("app/src/")]
    web_tests = [r for r in web_recs if r["path"].startswith("app/tests/")]
    web_scripts = [r for r in web_recs if r["path"].startswith("app/scripts/")]
    web_other = [
        r for r in web_recs if not r["path"].startswith(("app/src/", "app/tests/", "app/scripts/"))
    ]

    # top-level modules
    py_modules: dict[str, dict] = defaultdict(lambda: {"files": 0, "lines": 0, "code_lines": 0})
    for r in py_recs:
        p = r["path"]
        if p.startswith("src/egg_n_bacon_housing/"):
            rel = p[len("src/egg_n_bacon_housing/") :]
            mod = rel.split("/")[0] if "/" in rel else "<root>"
            if rel == "__init__.py":
                mod = "<root>"
        elif p == "main.py":
            mod = "<entrypoint main.py>"
        else:
            mod = p.rsplit("/", 1)[0] if "/" in p else "<root>"
        py_modules[mod]["files"] += 1
        py_modules[mod]["lines"] += r["lines"]
        py_modules[mod]["code_lines"] += r.get("code_lines", 0)

    web_modules: dict[str, dict] = defaultdict(lambda: {"files": 0, "lines": 0, "code_lines": 0})
    for r in web_recs:
        p = r["path"]
        if p.startswith("app/src/"):
            rel = p[len("app/src/") :]
            mod = rel.split("/")[0] if "/" in rel else "<root>"
        elif p.startswith("app/tests/"):
            rel = p[len("app/tests/") :]
            mod = "tests/" + (rel.split("/")[0] if "/" in rel else "<root>")
        elif p.startswith("app/scripts/"):
            mod = "app/scripts"
        else:
            mod = p
        web_modules[mod]["files"] += 1
        web_modules[mod]["lines"] += r["lines"]
        web_modules[mod]["code_lines"] += r.get("code_lines", 0)

    parse_failures = [
        {"path": r["path"], "errors": r.get("parse_errors", [])}
        for r in all_recs
        if not r.get("parse_ok", True)
    ]

    # ---- dead-code candidates ----
    dead = dead_code_candidates(py_recs, web_recs, py_files, web_files + css_files)

    # ---- external dependency usage census ----
    ext_counter: Counter = Counter()
    for r in py_recs:
        for m in r.get("external_import_names", []):
            ext_counter[m] += 1
    web_ext_counter: Counter = Counter()
    for r in web_recs:
        for m in r.get("external_import_names", []):
            web_ext_counter[m] += 1

    inv = {
        "audit": "master-audit-2026-11-23",
        "phase": "1-discovery-read-only",
        "head_commit": HEAD,
        "revision_verification": snapshot_info,
        "generated_by": "evidence/measurement/measure.py (uv run python 3.12)",
        "scope": {
            "definition": (
                "canonical scope = fixed git-tracked snapshot at HEAD (git ls-files). "
                "Audit-written artifacts and any other non-ignored untracked file are "
                "reported as supplemental/unscored and are excluded from every statistic."
            ),
            "tracked_files_at_head": len(tracked),
            "total_in_scope_files": len(in_scope),
            "self_excluded_audit_artifacts": {
                "prefix": AUDIT_DIR,
                "count": len(self_excluded),
                "files": self_excluded,
            },
            "supplemental_untracked_not_counted": {
                "count": len(supplemental_untracked),
                "files": supplemental_untracked,
            },
            "excluded_ignored_paths": EXCLUDED_IGNORED,
            "vendored_note": EXCLUDED_VENDORED_NOTE,
            "binary_and_data_artifacts_counted_but_not_parsed": len(
                [
                    p
                    for p in in_scope
                    if Path(p).suffix
                    in {".png", ".gz", ".svg", ".geojson", ".parquet", ".jsonl", ".ipynb"}
                    or (SNAPSHOT_DIR / p).is_file()
                    and is_binary(SNAPSHOT_DIR / p)
                ]
            ),
        },
        "categories": dict(sorted(cats.items(), key=lambda kv: -kv[1])),
        "source_file_counts": {
            "python": len(py_recs),
            "web_ts_tsx_js_mjs_astro": len(web_recs),
            "css": len(css_recs),
            "notebooks": len(nb_recs),
            "total_measured_source_files": len(all_recs),
        },
        "loc": {
            "python_source_src": loc(py_src),
            "python_tests": loc(py_tests),
            "python_scripts": loc(py_scripts),
            "python_entrypoint": loc(py_entry),
            "python_total": loc(py_recs),
            "web_src": loc(web_src),
            "web_tests": loc(web_tests),
            "web_scripts": loc(web_scripts),
            "web_config_other": loc(web_other),
            "web_total": loc(web_recs),
            "css": loc(css_recs),
            "all_source_total": loc(all_recs),
            "notebooks": {
                "files": len(nb_recs),
                "raw_lines": sum(r["lines"] for r in nb_recs),
                "code_cell_lines": sum(r["code_lines"] for r in nb_recs),
            },
        },
        "tests_to_source_ratio": {
            "python": {
                "test_files": loc(py_tests)["files"],
                "source_files_src": loc(py_src)["files"],
                "test_code_lines": loc(py_tests)["code_lines"],
                "source_code_lines_src": loc(py_src)["code_lines"],
                "ratio_by_code_lines": round(
                    loc(py_tests)["code_lines"] / max(1, loc(py_src)["code_lines"]),
                    3,
                ),
                "ratio_by_files": round(loc(py_tests)["files"] / max(1, loc(py_src)["files"]), 3),
            },
            "web": {
                "test_files": loc(web_tests)["files"],
                "source_files_src": loc(web_src)["files"],
                "test_code_lines": loc(web_tests)["code_lines"],
                "source_code_lines_src": loc(web_src)["code_lines"],
                "ratio_by_code_lines": round(
                    loc(web_tests)["code_lines"] / max(1, loc(web_src)["code_lines"]),
                    3,
                ),
                "ratio_by_files": round(loc(web_tests)["files"] / max(1, loc(web_src)["files"]), 3),
            },
        },
        "top_level_modules": {
            "python": dict(sorted(py_modules.items(), key=lambda kv: -kv[1]["lines"])),
            "web": dict(sorted(web_modules.items(), key=lambda kv: -kv[1]["lines"])),
        },
        "size_thresholds": {
            "files_over_300_lines": sorted(
                [{"path": r["path"], "lines": r["lines"]} for r in all_recs if r["lines"] > 300],
                key=lambda x: -x["lines"],
            ),
            "files_over_500_lines": sorted(
                [{"path": r["path"], "lines": r["lines"]} for r in all_recs if r["lines"] > 500],
                key=lambda x: -x["lines"],
            ),
        },
        "parse_failures": parse_failures,
        "external_import_usage": {
            "python_module_to_file_count": dict(ext_counter.most_common()),
            "web_module_to_file_count": dict(web_ext_counter.most_common()),
            "web_parser": web_meta,
        },
        "coverage_report": coverage_report(),
        "manifests": manifests(),
        "dead_code_candidates_unconfirmed": {
            "method": (
                "identifier word-boundary grep across all measured source files; a symbol "
                "with zero references outside its defining file is listed. NOT proof of "
                "dead code: dynamic access (getattr, importlib, string refs), framework "
                "entry points, test-only imports and re-exports are not resolved."
            ),
            "python_count": len(dead["python"]),
            "python": dead["python"],
            "web_count": len(dead["web"]),
            "web": dead["web"],
        },
        "methodology_notes": {
            "loc": (
                "lines = physical lines (splitlines). code_lines excludes blank and "
                "comment-only lines (python: tokenize; ts/tsx/mjs: lexical //, /* */ "
                "single-line tracking which misclassifies comment text inside template "
                "literals)."
            ),
            "nesting": (
                "max_nesting_estimate is block-statement nesting depth, NOT cyclomatic "
                "complexity: it ignores boolean operators, comprehension filters and "
                "expression lambdas."
            ),
            "python_parser": "ast (stdlib) on 3.12 via uv run python",
            "web_parser": (
                f"typescript compiler API v{web_meta.get('ts_version')} loaded from "
                "app/node_modules (read-only); .astro files: frontmatter block parsed as "
                "TS, template markup not analyzed"
            ),
        },
    }
    (EVID / "inventory.json").write_text(json.dumps(inv, indent=2) + "\n")

    raw = {
        "head_commit": HEAD,
        "python": sorted(py_recs, key=lambda r: r["path"]),
        "web": sorted(
            [{k: v for k, v in r.items() if k != "external_import_names"} for r in web_recs],
            key=lambda r: r["path"],
        ),
        "css": css_recs,
        "notebooks": nb_recs,
        "files_by_category": {k: sorted(v) for k, v in by_cat.items()},
    }
    (EVID / "raw-measurements.json").write_text(json.dumps(raw, indent=2) + "\n")

    # ---- full-file-tree.txt ----
    lines: list[str] = []
    lines.append(f"# Full file tree with categories — HEAD {HEAD}")
    lines.append("# Phase 1 READ-ONLY discovery; generated by evidence/measurement/measure.py")
    lines.append("")
    lines.append("SCOPE")
    lines.append(
        "  canonical scope = fixed git-tracked snapshot at HEAD (git ls-files); "
        "audit-written files are never counted"
    )
    lines.append(f"  tracked files at HEAD: {len(tracked)}")
    lines.append(f"  total in-scope files: {len(in_scope)}")
    lines.append(f"  self-excluded audit artifacts under {AUDIT_DIR}: {len(self_excluded)}")
    lines.append(f"  supplemental untracked (not counted): {len(supplemental_untracked)}")
    for p in supplemental_untracked:
        lines.append(f"    (supplemental) {p}")
    lines.append("")
    lines.append("EXCLUSIONS (git-ignored, never enumerated or read)")
    for e in EXCLUDED_IGNORED:
        lines.append(f"  - {e}")
    lines.append("")
    lines.append("CATEGORY DEFINITIONS")
    defs = {
        "python:source": "src/egg_n_bacon_housing/**/*.py — pipeline/domain library",
        "python:test": "tests/*.py — pytest suite",
        "python:script": "scripts/**/*.py — operational + evidence CLI scripts",
        "python:entrypoint": "main.py — pipeline entry point",
        "web:source": "app/src/** — Astro pages/layouts/components + TS/TSX modules",
        "web:test": "app/tests/** — Playwright e2e + bun unit tests + fixtures",
        "web:script": "app/scripts/** — data sync/validation/measurement scripts",
        "web:config": "app-level build/test configuration files",
        "artifact:published-web-data": "app/public/** — published JSON/gz/PNG/geojson payloads served by the site",
        "design-asset": "assets/svg/** — design/reference SVGs and specs",
        "docs:evidence-and-plans": "docs/** — plans, reports, reference docs",
        "docs:agent-context": ".agents/**, .claude/**, .context7/**, prompts/**",
        "docs:root": "root-level README/AGENTS/CLAUDE/CONTRIBUTING/QUICKSTART",
        "data:tracked-input": "data/** — catalog, curated external geojson, macro parquet",
        "ci:workflow": ".github/workflows/**",
        "config:*": "manifests, lockfiles, pre-commit, secret-scan baseline, env template",
        "notebook": "notebooks/*.ipynb — exploratory source notebooks",
    }
    for k, v in defs.items():
        lines.append(f"  {k:<32} {v}")
    lines.append("")
    lines.append(
        "PER-FILE METRICS for source files are in complexity.csv "
        "(lines, code_lines, exported symbols, external imports, nesting)."
    )
    lines.append("")
    for cat in sorted(by_cat, key=lambda c: (-len(by_cat[c]), c)):
        paths = by_cat[cat]
        total_lines = 0
        total_bytes = 0
        for p in paths:
            ap = SNAPSHOT_DIR / p
            if ap.is_file():
                total_bytes += ap.stat().st_size
                if not is_binary(ap):
                    try:
                        total_lines += len(ap.read_text("utf-8").splitlines())
                    except OSError:
                        pass
        lines.append(
            f"=== {cat} — {len(paths)} files, {total_bytes / 1024:.1f} KiB, {total_lines} text lines ==="
        )
        for p in sorted(paths):
            ap = SNAPSHOT_DIR / p
            if not ap.is_file():
                lines.append(f"    {p}  [missing]")
                continue
            size = ap.stat().st_size
            if is_binary(ap):
                lines.append(f"    {p}  [{size} B binary/data]")
            else:
                n = len(ap.read_text("utf-8", errors="replace").splitlines())
                lines.append(f"    {p}  [{n} lines, {size} B]")
        lines.append("")
    (EVID / "full-file-tree.txt").write_text("\n".join(lines) + "\n")

    print(f"HEAD {HEAD}")
    print(
        f"files in scope: {len(in_scope)} (tracked HEAD {len(tracked)}; supplemental untracked {len(supplemental_untracked)} not counted; self-excluded audit artifacts {len(self_excluded)})"
    )
    print(
        f"source files measured: {len(all_recs)} (py {len(py_recs)}, web {len(web_recs)}, css {len(css_recs)})"
    )
    print(
        f"python code lines src={loc(py_src)['code_lines']} tests={loc(py_tests)['code_lines']} scripts={loc(py_scripts)['code_lines']}"
    )
    print(f"web code lines src={loc(web_src)['code_lines']} tests={loc(web_tests)['code_lines']}")
    print(f"parse failures: {len(parse_failures)}")
    print(f"dead-code candidates: py {len(dead['python'])}, web {len(dead['web'])}")
    print("wrote:", ", ".join(sorted(p.name for p in EVID.iterdir())))


if __name__ == "__main__":
    main()
