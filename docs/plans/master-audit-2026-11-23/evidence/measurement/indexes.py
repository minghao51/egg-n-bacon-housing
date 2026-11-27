#!/usr/bin/env python3
"""READ-ONLY mechanical indexes for the master audit (supplements bounded deep reads).

Writes under docs/plans/master-audit-2026-11-23/evidence/:
  public-entrypoints.csv     every public Python def/class/method + CLI guards;
                             every TS/JS export definition + Astro route file
  error-surfaces.csv         every Python except/raise/exit and JS catch/throw/exit
  observability.csv          per-file log/print/error-emission counts
  schema-declarations.csv    pydantic/TypedDict/NamedTuple/Enum/dataclass,
                             TS interface/type-alias/enum, zod schemas
  discovery-inventory.md     observational summary
  measurement/*              copies of the harness scripts (audit tooling only)

Scope is the fixed HEAD-tracked snapshot from measure.enumerate_files(); files the
audit itself writes are excluded from counting. Rows are produced mechanically and
are NOT semantically reviewed.
"""

from __future__ import annotations

import ast
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import measure  # noqa: E402  (audit tooling; sibling module, no install required)

measure.ensure_snapshot()  # pinned HEAD snapshot shared with measure.py
REPO = measure.REPO
EVID = measure.EVID

PY_LOG_ROOTS = {"log", "logger", "LOGGER", "_log", "logging"}
LOG_LEVELS = {
    "debug",
    "info",
    "warning",
    "warn",
    "error",
    "exception",
    "critical",
    "fatal",
}
SCHEMA_BASES = {
    "BaseModel": "pydantic-model",
    "BaseSettings": "pydantic-settings",
    "TypedDict": "typeddict",
    "NamedTuple": "namedtuple",
    "Enum": "enum",
    "StrEnum": "enum",
    "IntEnum": "enum",
    "Flag": "enum",
    "Protocol": "protocol",
}


def clip(text: str, n: int = 140) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:n]


def base_names(node: ast.ClassDef) -> list[str]:
    out = []
    for b in node.bases:
        if isinstance(b, ast.Name):
            out.append(b.id)
        elif isinstance(b, ast.Attribute):
            out.append(b.attr)
        elif isinstance(b, ast.Subscript):
            inner = b.value
            if isinstance(inner, ast.Name):
                out.append(inner.id)
            elif isinstance(inner, ast.Attribute):
                out.append(inner.attr)
    return out


def call_snippet(src: str, node: ast.AST) -> str:
    seg = ast.get_source_segment(src, node) or ""
    return clip(seg.splitlines()[0] if seg else "", 140)


# --------------------------------------------------------------------------- #
# Python extraction
# --------------------------------------------------------------------------- #


def py_tree(rel: str):
    text = (measure.SNAPSHOT_DIR / rel).read_text(encoding="utf-8", errors="replace")
    try:
        return ast.parse(text, filename=rel), text, None
    except (SyntaxError, ValueError) as exc:  # pragma: no cover - none in repo
        return None, text, f"{type(exc).__name__}: {exc}"


def py_entrypoint_rows(rel: str, tree: ast.Module, src: str) -> list[dict]:
    rows: list[dict] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and not node.name.startswith(
            "_"
        ):
            rows.append(
                {
                    "line": node.lineno,
                    "kind": "async-function"
                    if isinstance(node, ast.AsyncFunctionDef)
                    else "function",
                    "name": node.name,
                    "signature": f"{'async ' if isinstance(node, ast.AsyncFunctionDef) else ''}def {node.name}({_args(node)}){_ret(node)}",
                    "decorators": ", ".join(
                        f"@{clip(ast.unparse(d), 40)}" for d in node.decorator_list
                    ),
                }
            )
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            methods = [
                b for b in node.body if isinstance(b, ast.FunctionDef | ast.AsyncFunctionDef)
            ]
            rows.append(
                {
                    "line": node.lineno,
                    "kind": "class",
                    "name": node.name,
                    "signature": f"class {node.name}({', '.join(base_names(node))}) [{len(methods)} methods, {sum(1 for b in node.body if isinstance(b, ast.AnnAssign) or isinstance(b, ast.Assign))} attrs]",
                    "decorators": ", ".join(
                        f"@{clip(ast.unparse(d), 40)}" for d in node.decorator_list
                    ),
                }
            )
            for m in methods:
                if m.name.startswith("_"):
                    continue
                rows.append(
                    {
                        "line": m.lineno,
                        "kind": "method",
                        "name": f"{node.name}.{m.name}",
                        "signature": f"def {m.name}({_args(m)}){_ret(m)}",
                        "decorators": ", ".join(
                            f"@{clip(ast.unparse(d), 40)}" for d in m.decorator_list
                        ),
                    }
                )
        elif isinstance(node, ast.If) and _is_main_guard(node.test):
            first = ""
            for stmt in node.body:
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                    first = clip(ast.unparse(stmt.value), 80)
                    break
            rows.append(
                {
                    "line": node.lineno,
                    "kind": "cli-main-guard",
                    "name": "__main__",
                    "signature": f"if __name__ == '__main__': {first}",
                    "decorators": "",
                }
            )
    return rows


def _args(node) -> str:
    try:
        return ast.unparse(node.args)
    except Exception:  # pragma: no cover
        return "..."


def _ret(node) -> str:
    if node.returns is None:
        return ""
    try:
        return f" -> {clip(ast.unparse(node.returns), 60)}"
    except Exception:  # pragma: no cover
        return ""


def _is_main_guard(test: ast.expr) -> bool:
    if not isinstance(test, ast.Compare):
        return False
    left, ops, comps = test.left, test.ops, test.comparators
    if not (isinstance(left, ast.Name) and left.id == "__name__"):
        return False
    for op, comp in zip(ops, comps):
        if isinstance(op, ast.Eq) and isinstance(comp, ast.Constant) and comp.value == "__main__":
            return True
        if isinstance(op, ast.In) and isinstance(comp, ast.Tuple | ast.Constant):
            vals = (
                [e.value for e in comp.elts if isinstance(e, ast.Constant)]
                if isinstance(comp, ast.Tuple)
                else [getattr(comp, "value", None)]
            )
            if "__main__" in vals:
                return True
    return False


def py_error_rows(rel: str, tree: ast.Module, src: str) -> list[dict]:
    rows: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            kind = "except" if node.type is not None else "bare-except"
            detail = ast.unparse(node.type) if node.type is not None else "(no exception type)"
            first = node.body[0] if node.body else None
            rows.append(
                {
                    "line": node.lineno,
                    "kind": kind,
                    "detail": clip(detail, 120),
                    "code": call_snippet(src, first) if first is not None else "",
                }
            )
        elif isinstance(node, ast.Raise):
            rows.append(
                {
                    "line": node.lineno,
                    "kind": "raise",
                    "detail": clip(ast.unparse(node.exc), 120) if node.exc else "bare re-raise",
                    "code": call_snippet(src, node),
                }
            )
        elif isinstance(node, ast.Call):
            f = node.func
            is_exit = (
                isinstance(f, ast.Attribute)
                and f.attr in {"exit", "_exit"}
                and isinstance(f.value, ast.Name)
                and f.value.id in {"sys", "os"}
            ) or (isinstance(f, ast.Name) and f.id in {"exit", "quit"})
            if is_exit:
                name = ast.unparse(f)
                rows.append(
                    {
                        "line": node.lineno,
                        "kind": "sys.exit" if "sys" in name or f.__class__ is ast.Name else name,
                        "detail": clip(", ".join(ast.unparse(a) for a in node.args), 100),
                        "code": call_snippet(src, node),
                    }
                )
    return sorted(rows, key=lambda r: r["line"])


def py_observability(rel: str, tree: ast.Module, lines: int, code: int, cat: str) -> dict:
    by_level: Counter = Counter()
    print_calls = logger_calls = logging_module_calls = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if isinstance(f, ast.Name) and f.id == "print":
            print_calls += 1
        elif isinstance(f, ast.Attribute) and f.attr in LOG_LEVELS:
            if isinstance(f.value, ast.Name) and f.value.id in PY_LOG_ROOTS:
                if f.value.id == "logging":
                    logging_module_calls += 1
                else:
                    logger_calls += 1
                by_level[f.attr] += 1
    return {
        "path": rel,
        "lang": "python",
        "category": cat,
        "lines": lines,
        "code_lines": code,
        "print_calls": print_calls,
        "logger_calls": logger_calls,
        "logging_module_calls": logging_module_calls,
        "console_calls": 0,
        "by_level": ";".join(f"{k}={v}" for k, v in sorted(by_level.items())),
    }


def py_schema_rows(rel: str, tree: ast.Module, cat: str) -> list[dict]:
    rows = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases = base_names(node)
        kind = None
        for b in bases:
            if b in SCHEMA_BASES:
                kind = SCHEMA_BASES[b]
                break
        decorators = {d.id for d in node.decorator_list if isinstance(d, ast.Name)}
        if kind is None and "dataclass" in decorators:
            kind = "dataclass"
        if kind is None:
            continue
        if kind == "enum":
            fields = sum(
                1
                for b in node.body
                if isinstance(b, ast.Assign)
                and any(isinstance(t, ast.Name) and not t.id.startswith("_") for t in b.targets)
            )
        else:
            fields = sum(
                1
                for b in node.body
                if isinstance(b, ast.AnnAssign)
                and isinstance(b.target, ast.Name)
                and not b.target.id.startswith("_")
            )
        field_calls = sum(
            1
            for b in node.body
            if isinstance(b, ast.AnnAssign)
            and isinstance(b.value, ast.Call)
            and isinstance(b.value.func, ast.Name)
            and b.value.func.id in {"Field", "field"}
        )
        rows.append(
            {
                "path": rel,
                "line": node.lineno,
                "name": node.name,
                "kind": kind,
                "field_count": fields,
                "field_calls": field_calls,
                "lang": "python",
                "category": cat,
            }
        )
    return rows


# --------------------------------------------------------------------------- #
# Web extraction (from measure.web_measure)
# --------------------------------------------------------------------------- #


def route_pattern(rel: str) -> str:
    p = rel[len("app/src/pages") :]
    p = p[: -len(".astro")] if p.endswith(".astro") else p
    if p.endswith("/index"):
        p = p[: -len("/index")]
    p = p or "/"
    p = re.sub(r"\[\.\.\.(\w+)\]", r"*\1", p)
    p = re.sub(r"\[(\w+)\]", r":\1", p)
    return p


def main() -> None:
    tracked, supplemental, self_excluded = measure.enumerate_files()
    py_files = [p for p in tracked if p.endswith(".py")]
    web_files = [
        p for p in tracked if Path(p).suffix in measure.WEB_CODE_EXT and not p.endswith(".css")
    ]

    entry_rows: list[dict] = []
    error_rows: list[dict] = []
    obs_rows: list[dict] = []
    schema_rows: list[dict] = []
    parse_issues: list[dict] = []

    # ---- Python ----
    py_rec_by_path = {}
    for rel in py_files:
        tree, src, err = py_tree(rel)
        cat = measure.category(rel)
        lines = len(src.splitlines())
        if tree is None:
            parse_issues.append({"path": rel, "error": err})
            continue
        code, _, _ = measure.py_code_lines(src)
        py_rec_by_path[rel] = {"lines": lines, "code_lines": code}
        for r in py_entrypoint_rows(rel, tree, src):
            entry_rows.append(
                {
                    **r,
                    "path": rel,
                    "lang": "python",
                    "category": cat,
                    "notes": "automated-scan; unreviewed",
                }
            )
        for r in py_error_rows(rel, tree, src):
            error_rows.append(
                {
                    **r,
                    "path": rel,
                    "lang": "python",
                    "category": cat,
                    "notes": "automated-scan; unreviewed",
                }
            )
        obs = py_observability(rel, tree, lines, code, cat)
        obs["exception_handlers"] = sum(
            1 for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)
        )
        obs["raise_statements"] = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Raise))
        obs["exit_calls"] = sum(
            1
            for r in py_error_rows(rel, tree, src)
            if r["kind"] in {"sys.exit", "os._exit", "exit", "quit"}
        )
        obs["method"] = "python-ast"
        obs_rows.append(obs)
        schema_rows.extend(py_schema_rows(rel, tree, cat))

    # ---- Web ----
    web_recs, _ = measure.web_measure(web_files)
    for rel in web_files:
        rec = web_recs[rel]
        cat = measure.category(rel)
        if rec.get("method") == "failed":
            parse_issues.append({"path": rel, "error": rec.get("error", "parser failed")})
            continue
        for r in rec.get("exports_detail", []):
            entry_rows.append(
                {
                    "path": rel,
                    "line": r["line"],
                    "kind": r["kind"],
                    "name": r["name"],
                    "signature": clip(r.get("signature", ""), 160),
                    "decorators": "",
                    "lang": "web",
                    "category": cat,
                    "notes": "automated-scan; unreviewed; approximate signature",
                }
            )
        if rel.startswith("app/src/pages/") and rel.endswith(".astro"):
            entry_rows.append(
                {
                    "path": rel,
                    "line": 1,
                    "kind": "route",
                    "name": route_pattern(rel),
                    "signature": f"GET {route_pattern(rel)}",
                    "decorators": "",
                    "lang": "web",
                    "category": cat,
                    "notes": "file-based route; automated-scan; unreviewed",
                }
            )
        for r in rec.get("errors", []):
            error_rows.append(
                {
                    "path": rel,
                    "line": r["line"],
                    "kind": r["kind"],
                    "detail": clip(r.get("detail", ""), 120),
                    "code": clip(r.get("code", ""), 140),
                    "lang": "web",
                    "category": cat,
                    "notes": "automated-scan; unreviewed",
                }
            )
        by_level = rec.get("log_by_level", {}) or {}
        obs_rows.append(
            {
                "path": rel,
                "lang": "web" if not rel.endswith(".astro") else "astro-frontmatter",
                "category": cat,
                "lines": rec.get("lines", 0),
                "code_lines": rec.get("code_lines", 0),
                "print_calls": 0,
                "logger_calls": max(0, rec.get("log_calls", 0) - by_level.get("console", 0)),
                "logging_module_calls": 0,
                "console_calls": sum(v for k, v in by_level.items() if k.startswith("console.")),
                "by_level": ";".join(f"{k}={v}" for k, v in sorted(by_level.items())),
                "exception_handlers": sum(1 for r in rec.get("errors", []) if r["kind"] == "catch"),
                "raise_statements": sum(1 for r in rec.get("errors", []) if r["kind"] == "throw"),
                "exit_calls": sum(1 for r in rec.get("errors", []) if r["kind"] == "process.exit"),
                "method": rec.get("method", ""),
            }
        )
        for s in rec.get("schemas", []):
            schema_rows.append(
                {
                    "path": rel,
                    "line": s["line"],
                    "name": s["name"],
                    "kind": s["kind"],
                    "field_count": s.get("field_count", 0),
                    "field_calls": "",
                    "lang": "web",
                    "category": cat,
                }
            )

    # ---- write CSVs ----
    def write(name: str, rows: list[dict], cols: list[str]) -> None:
        with (EVID / name).open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in sorted(rows, key=lambda r: (r.get("path", ""), r.get("line", 0))):
                w.writerow(r)

    write(
        "public-entrypoints.csv",
        entry_rows,
        ["path", "line", "lang", "category", "kind", "name", "signature", "decorators", "notes"],
    )
    write(
        "error-surfaces.csv",
        error_rows,
        ["path", "line", "lang", "category", "kind", "detail", "code", "notes"],
    )
    write(
        "observability.csv",
        obs_rows,
        [
            "path",
            "lang",
            "category",
            "lines",
            "code_lines",
            "print_calls",
            "logger_calls",
            "logging_module_calls",
            "console_calls",
            "by_level",
            "exception_handlers",
            "raise_statements",
            "exit_calls",
            "method",
        ],
    )
    write(
        "schema-declarations.csv",
        schema_rows,
        ["path", "line", "lang", "category", "kind", "name", "field_count", "field_calls"],
    )

    # ---- summary patch of inventory.json ----
    inv_path = EVID / "inventory.json"
    inv = json.loads(inv_path.read_text())
    kind_counts = Counter(r["kind"] for r in entry_rows)
    err_counts = Counter(r["kind"] for r in error_rows)
    schema_counts = Counter(r["kind"] for r in schema_rows)
    inv["supplemental_indexes"] = {
        "note": (
            "Mechanical, exhaustive indexes generated for all in-scope source files. "
            "Rows are automated scans and are NOT semantically reviewed; absence of a "
            "row is not proof of absence of behaviour (dynamic dispatch, runtime "
            "registration, framework magic are not resolved)."
        ),
        "public-entrypoints.csv": {
            "rows": len(entry_rows),
            "files_with_rows": len({r["path"] for r in entry_rows}),
            "by_kind": dict(kind_counts.most_common()),
        },
        "error-surfaces.csv": {
            "rows": len(error_rows),
            "files_with_rows": len({r["path"] for r in error_rows}),
            "by_kind": dict(err_counts.most_common()),
        },
        "observability.csv": {
            "rows": len(obs_rows),
            "totals": {
                "print_calls": sum(r["print_calls"] for r in obs_rows),
                "logger_calls": sum(r["logger_calls"] for r in obs_rows),
                "logging_module_calls": sum(r["logging_module_calls"] for r in obs_rows),
                "console_calls": sum(r["console_calls"] for r in obs_rows),
                "exception_handlers": sum(r["exception_handlers"] for r in obs_rows),
                "raise_statements": sum(r["raise_statements"] for r in obs_rows),
                "exit_calls": sum(r["exit_calls"] for r in obs_rows),
            },
            "files_with_zero_logging": sum(
                1
                for r in obs_rows
                if r["print_calls"] == 0
                and r["logger_calls"] == 0
                and r["logging_module_calls"] == 0
                and r["console_calls"] == 0
            ),
        },
        "schema-declarations.csv": {
            "rows": len(schema_rows),
            "by_kind": dict(schema_counts.most_common()),
        },
        "parse_issues": parse_issues,
    }
    inv_path.write_text(json.dumps(inv, indent=2) + "\n")

    # ---- harness scripts are already in evidence/measurement/ (this dir) ----
    meas_dir = SCRIPT_DIR
    (meas_dir / "README.md").write_text(
        "# Audit measurement tooling (not production code)\n\n"
        "Read-only harness used to produce the Phase 1 discovery artifacts for the\n"
        "master audit at HEAD 449b921d499a8c55ec1eacb1a423baa7632456d3.\n\n"
        "| script | role |\n|---|---|\n"
        "| `measure.py` | scope enumeration, Python `ast`/`tokenize` metrics, LOC, dead-code candidate grep, coverage/manifest inspection; writes `inventory.json`, `complexity.csv`, `full-file-tree.txt`, `raw-measurements.json` |\n"
        "| `indexes.py` | entrypoint/error/observability/schema indexes; patches `inventory.json`; copies these scripts |\n"
        "| `ts_measure.mjs` | TypeScript compiler AST parsing for `.ts/.tsx/.mjs` and `.astro` frontmatter (loaded read-only from `app/node_modules/typescript`) |\n\n"
        "Run from anywhere: `uv run python <repo>/docs/plans/master-audit-2026-11-23/evidence/measurement/measure.py`\n"
        "then the same for `indexes.py`. No absolute paths or installs are required: the scripts\n"
        "resolve the repo root with `git rev-parse --show-toplevel` and read measured content\n"
        "from a `git archive HEAD` snapshot.\n\n"
        "These files are audit evidence only: they do not import, modify or execute\n"
        "application code, and they are not part of the shipped package.\n"
    )

    print("public-entrypoints.csv rows:", len(entry_rows), dict(kind_counts.most_common()))
    print("error-surfaces.csv rows:", len(error_rows), dict(err_counts.most_common()))
    print(
        "observability.csv rows:",
        len(obs_rows),
        "print",
        sum(r["print_calls"] for r in obs_rows),
        "logger",
        sum(r["logger_calls"] for r in obs_rows),
        "logging-module",
        sum(r["logging_module_calls"] for r in obs_rows),
        "console",
        sum(r["console_calls"] for r in obs_rows),
    )
    print("schema-declarations.csv rows:", len(schema_rows), dict(schema_counts.most_common()))
    print("parse issues:", parse_issues)


if __name__ == "__main__":
    main()
