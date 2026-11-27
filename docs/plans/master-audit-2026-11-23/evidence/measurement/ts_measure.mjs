// READ-ONLY measurement helper for the master audit (Phase 1 discovery).
// Uses the repo's own typescript compiler (app/node_modules/typescript) to AST-parse
// TS/TSX/MJS and the frontmatter block of .astro files.
// Emits JSON on stdout: { files: { <path>: {...} }, tsVersion, error }

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

// argv[2] = content root (pinned snapshot), argv[4] = module-resolution root
// (real worktree, where app/node_modules lives; git-archived snapshots cannot
// contain git-ignored node_modules).
const REPO = process.argv[2];
const MODULE_ROOT = process.argv[4] || REPO;
const inputList = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));

const require_ = createRequire(path.join(MODULE_ROOT, "app/package.json"));
let ts;
try {
  ts = require_("typescript");
} catch (e) {
  process.stdout.write(
    JSON.stringify({ error: "typescript-unavailable: " + String(e) }),
  );
  process.exit(0);
}

const NODE_BUILTINS = new Set([
  "assert",
  "async_hooks",
  "buffer",
  "child_process",
  "cluster",
  "console",
  "constants",
  "crypto",
  "dgram",
  "diagnostics_channel",
  "dns",
  "domain",
  "events",
  "fs",
  "http",
  "http2",
  "https",
  "inspector",
  "module",
  "net",
  "os",
  "path",
  "perf_hooks",
  "process",
  "punycode",
  "querystring",
  "readline",
  "repl",
  "stream",
  "string_decoder",
  "timers",
  "tls",
  "trace_events",
  "tty",
  "url",
  "util",
  "v8",
  "vm",
  "wasi",
  "worker_threads",
  "zlib",
]);

function isExternal(spec) {
  if (!spec) return false;
  if (spec.startsWith(".") || spec.startsWith("/")) return false;
  if (spec.startsWith("@/") || spec.startsWith("~/")) return false;
  if (spec.startsWith("node:") || spec.startsWith("bun:")) return false;
  const root = spec.split("/")[0];
  if (NODE_BUILTINS.has(root)) return false;
  return true;
}

const OWNERS = new Set([
  ts.SyntaxKind.IfStatement,
  ts.SyntaxKind.ForStatement,
  ts.SyntaxKind.ForInStatement,
  ts.SyntaxKind.ForOfStatement,
  ts.SyntaxKind.WhileStatement,
  ts.SyntaxKind.DoStatement,
  ts.SyntaxKind.SwitchStatement,
  ts.SyntaxKind.TryStatement,
  ts.SyntaxKind.CatchClause,
  ts.SyntaxKind.FunctionDeclaration,
  ts.SyntaxKind.FunctionExpression,
  ts.SyntaxKind.ArrowFunction,
  ts.SyntaxKind.MethodDeclaration,
  ts.SyntaxKind.Constructor,
  ts.SyntaxKind.GetAccessor,
  ts.SyntaxKind.SetAccessor,
  ts.SyntaxKind.ClassDeclaration,
  ts.SyntaxKind.ClassExpression,
  ts.SyntaxKind.ModuleDeclaration,
]);

const LOGGER_ROOTS = new Set(["console", "log", "logger", "LOGGER", "_log"]);

function maxNesting(sf) {
  let max = 0;
  const walk = (node, d) => {
    const nd = OWNERS.has(node.kind) ? d + 1 : d;
    if (nd > max) max = nd;
    ts.forEachChild(node, (c) => walk(c, nd));
  };
  walk(sf, 0);
  return max;
}

const hasModifier = (node, kind) => {
  const mods = ts.canHaveModifiers(node) ? ts.getModifiers(node) : undefined;
  return !!mods && mods.some((m) => m.kind === kind);
};
const isExported = (node) => hasModifier(node, ts.SyntaxKind.ExportKeyword);

const clip = (s, n = 160) => s.replace(/\s+/g, " ").trim().slice(0, n);
const lineOf = (sf, node) =>
  sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;

function namedExportsOnly(sf) {
  const names = [];
  for (const stmt of sf.statements) {
    if (ts.isExportDeclaration(stmt)) {
      if (stmt.exportClause && ts.isNamedExports(stmt.exportClause)) {
        for (const el of stmt.exportClause.elements)
          names.push(el.name.getText(sf));
      } else if (!stmt.exportClause) {
        names.push("*");
      }
      continue;
    }
    if (ts.isExportAssignment(stmt)) {
      names.push("default");
      continue;
    }
    if (!isExported(stmt)) continue;
    if (ts.isVariableStatement(stmt)) {
      for (const d of stmt.declarationList.declarations) {
        if (ts.isIdentifier(d.name)) names.push(d.name.text);
      }
      continue;
    }
    if (
      ts.isFunctionDeclaration(stmt) ||
      ts.isClassDeclaration(stmt) ||
      ts.isInterfaceDeclaration(stmt) ||
      ts.isTypeAliasDeclaration(stmt) ||
      ts.isEnumDeclaration(stmt) ||
      ts.isModuleDeclaration(stmt)
    ) {
      const kw = hasModifier(stmt, ts.SyntaxKind.DefaultKeyword)
        ? "default"
        : null;
      names.push(kw || (stmt.name ? stmt.name.getText(sf) : "<anonymous>"));
    }
  }
  return names;
}

function collectImports(sf) {
  const specs = [];
  const walk = (node) => {
    if (ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) {
      if (node.moduleSpecifier && ts.isStringLiteralLike(node.moduleSpecifier))
        specs.push(node.moduleSpecifier.text);
    } else if (
      ts.isImportEqualsDeclaration(node) &&
      node.moduleReference &&
      ts.isExternalModuleReference(node.moduleReference)
    ) {
      const e = node.moduleReference.expression;
      if (e && ts.isStringLiteralLike(e)) specs.push(e.text);
    } else if (ts.isCallExpression(node)) {
      const head = node.expression;
      const isReq = ts.isIdentifier(head) && head.text === "require";
      const isDyn = head.kind === ts.SyntaxKind.ImportKeyword;
      if (
        (isReq || isDyn) &&
        node.arguments.length === 1 &&
        ts.isStringLiteralLike(node.arguments[0])
      ) {
        specs.push(node.arguments[0].text);
      }
    }
    ts.forEachChild(node, walk);
  };
  walk(sf);
  return specs;
}

function paramSig(sf, node) {
  const parts = node.parameters.map((p) => clip(p.getText(sf), 80));
  const ret =
    sf.text && node.type ? ": " + clip(node.type.getText(sf), 60) : "";
  return "(" + parts.join(", ") + ")" + ret;
}

// ---- detailed export / entrypoint records -----------------------------------
function collectExportDetail(sf) {
  const rows = [];
  for (const stmt of sf.statements) {
    if (ts.isExportDeclaration(stmt)) {
      const from = stmt.moduleSpecifier
        ? stmt.moduleSpecifier.getText(sf).replace(/['"]/g, "")
        : "";
      if (stmt.exportClause && ts.isNamedExports(stmt.exportClause)) {
        for (const el of stmt.exportClause.elements) {
          rows.push({
            name: el.name.getText(sf),
            kind: "re-export",
            line: lineOf(sf, el),
            signature: from ? `from '${from}'` : "",
          });
        }
      } else {
        rows.push({
          name: "*",
          kind: "star-re-export",
          line: lineOf(sf, stmt),
          signature: from ? `from '${from}'` : "",
        });
      }
      continue;
    }
    if (ts.isExportAssignment(stmt)) {
      const e = stmt.expression;
      rows.push({
        name: "default",
        kind: "default-export",
        line: lineOf(sf, stmt),
        signature: clip(e.getText(sf), 100),
      });
      continue;
    }
    if (!isExported(stmt)) continue;
    const isDefault = hasModifier(stmt, ts.SyntaxKind.DefaultKeyword);
    if (ts.isFunctionDeclaration(stmt)) {
      rows.push({
        name: isDefault
          ? "default"
          : stmt.name
            ? stmt.name.text
            : "<anonymous>",
        kind: hasModifier(stmt, ts.SyntaxKind.AsyncKeyword)
          ? "async-function"
          : "function",
        line: lineOf(sf, stmt),
        signature:
          (stmt.name ? stmt.name.text : "default") + paramSig(sf, stmt),
      });
    } else if (ts.isClassDeclaration(stmt)) {
      rows.push({
        name: isDefault
          ? "default"
          : stmt.name
            ? stmt.name.text
            : "<anonymous>",
        kind: "class",
        line: lineOf(sf, stmt),
        signature: clip(
          "class " +
            (stmt.name ? stmt.name.text : "") +
            (stmt.heritageClauses
              ? " " +
                stmt.heritageClauses
                  .map((h) => clip(h.getText(sf), 80))
                  .join(" ")
              : "") +
            ` {${stmt.members.length} members}`,
          160,
        ),
      });
    } else if (ts.isInterfaceDeclaration(stmt)) {
      rows.push({
        name: stmt.name.text,
        kind: "interface",
        line: lineOf(sf, stmt),
        signature: clip(
          "interface " +
            stmt.name.text +
            (stmt.heritageClauses
              ? " " +
                stmt.heritageClauses
                  .map((h) => clip(h.getText(sf), 60))
                  .join(" ")
              : "") +
            ` {${stmt.members.length} members}`,
          160,
        ),
      });
    } else if (ts.isTypeAliasDeclaration(stmt)) {
      rows.push({
        name: stmt.name.text,
        kind: "type-alias",
        line: lineOf(sf, stmt),
        signature: clip(
          "type " + stmt.name.text + " = " + stmt.type.getText(sf),
          160,
        ),
      });
    } else if (ts.isEnumDeclaration(stmt)) {
      rows.push({
        name: stmt.name.text,
        kind: "enum",
        line: lineOf(sf, stmt),
        signature: `enum ${stmt.name.text} {${stmt.members.length} members}`,
      });
    } else if (ts.isModuleDeclaration(stmt)) {
      rows.push({
        name: stmt.name.getText(sf),
        kind: "namespace",
        line: lineOf(sf, stmt),
        signature: "",
      });
    } else if (ts.isVariableStatement(stmt)) {
      for (const d of stmt.declarationList.declarations) {
        if (!ts.isIdentifier(d.name)) continue;
        let sig = "";
        if (d.type) sig = ": " + clip(d.type.getText(sf), 80);
        else if (d.initializer) {
          const init = d.initializer;
          if (ts.isArrowFunction(init) || ts.isFunctionExpression(init))
            sig = paramSig(sf, init);
          else sig = "= " + clip(init.getText(sf), 80);
        }
        rows.push({
          name: d.name.text,
          kind: ts.isArrowFunction(d.initializer || {})
            ? "arrow-function"
            : "const",
          line: lineOf(sf, d),
          signature: sig,
        });
      }
    }
  }
  return rows;
}

// ---- error surfaces ---------------------------------------------------------
function collectErrors(sf) {
  const rows = [];
  const walk = (node) => {
    if (ts.isCatchClause(node)) {
      const param = node.variableDeclaration
        ? node.variableDeclaration.getText(sf)
        : "(no binding)";
      const first = node.block.statements.length
        ? clip(node.block.statements[0].getText(sf), 120)
        : "(empty)";
      rows.push({
        line: lineOf(sf, node),
        kind: "catch",
        detail: `catch ${clip(param, 40)}`,
        code: first,
      });
    } else if (ts.isThrowStatement(node)) {
      rows.push({
        line: lineOf(sf, node),
        kind: "throw",
        detail: clip(node.expression.getText(sf), 120),
        code: clip(node.getText(sf), 140),
      });
    } else if (ts.isCallExpression(node)) {
      const head = node.expression;
      const callee = ts.isPropertyAccessExpression(head)
        ? head.name.text
        : ts.isIdentifier(head)
          ? head.text
          : "";
      const base =
        ts.isPropertyAccessExpression(head) && ts.isIdentifier(head.expression)
          ? head.expression.text
          : "";
      if ((base === "process" || base === "Deno") && callee === "exit") {
        rows.push({
          line: lineOf(sf, node),
          kind: "process.exit",
          detail: node.arguments.map((a) => clip(a.getText(sf), 60)).join(", "),
          code: clip(node.getText(sf), 140),
        });
      }
      if (base === "process" && (callee === "abort" || callee === "on")) {
        rows.push({
          line: lineOf(sf, node),
          kind: "process." + callee,
          detail: "",
          code: clip(node.getText(sf), 120),
        });
      }
    }
    ts.forEachChild(node, walk);
  };
  walk(sf);
  return rows;
}

// ---- logging ----------------------------------------------------------------
function collectLogs(sf) {
  const byLevel = {};
  let total = 0;
  const walk = (node) => {
    if (ts.isCallExpression(node)) {
      const head = node.expression;
      if (
        ts.isPropertyAccessExpression(head) &&
        ts.isIdentifier(head.expression)
      ) {
        const root = head.expression.text;
        if (LOGGER_ROOTS.has(root)) {
          const key = root + "." + head.name.text;
          byLevel[key] = (byLevel[key] || 0) + 1;
          total++;
        }
      }
    }
    ts.forEachChild(node, walk);
  };
  walk(sf);
  return { total, byLevel };
}

// ---- schema declarations ----------------------------------------------------
const ZOD_RE =
  /\bz\.(object|strictObject|array|enum|union|string|number|boolean|literal|record|tuple|null|optional)\b/;

function zodBaseCall(expr) {
  let cur = expr;
  for (let i = 0; i < 12 && cur; i++) {
    if (ts.isCallExpression(cur)) {
      const callee = cur.expression;
      if (
        ts.isPropertyAccessExpression(callee) &&
        ts.isIdentifier(callee.expression) &&
        callee.expression.text === "z"
      ) {
        return { call: cur, method: callee.name.text };
      }
      cur = callee;
    } else if (ts.isPropertyAccessExpression(cur)) {
      cur = cur.expression;
    } else {
      return null;
    }
  }
  return null;
}

function collectSchemas(sf) {
  const rows = [];
  const walk = (node) => {
    if (ts.isInterfaceDeclaration(node)) {
      const fields = node.members.filter((m) => m.name).length;
      rows.push({
        name: node.name.text,
        kind: "interface",
        line: lineOf(sf, node),
        field_count: fields,
      });
    } else if (ts.isTypeAliasDeclaration(node)) {
      let fields = 0;
      if (ts.isTypeLiteralNode(node.type))
        fields = node.type.members.filter((m) => m.name).length;
      rows.push({
        name: node.name.text,
        kind: "type-alias",
        line: lineOf(sf, node),
        field_count: fields,
      });
    } else if (ts.isEnumDeclaration(node)) {
      rows.push({
        name: node.name.text,
        kind: "enum",
        line: lineOf(sf, node),
        field_count: node.members.length,
      });
    } else if (ts.isVariableDeclaration(node) && node.initializer) {
      const z = zodBaseCall(node.initializer);
      if (z && ZOD_RE.test(z.call.expression.getText(sf))) {
        let fields = 0;
        const arg = z.call.arguments[0];
        if (arg && ts.isObjectLiteralExpression(arg))
          fields = arg.properties.length;
        rows.push({
          name:
            node.name && ts.isIdentifier(node.name)
              ? node.name.text
              : "<pattern>",
          kind: "zod-" + z.method,
          line: lineOf(sf, node),
          field_count: fields,
        });
      }
    }
    ts.forEachChild(node, walk);
  };
  walk(sf);
  return rows;
}

function countCodeLines(text) {
  let code = 0,
    comment = 0,
    blank = 0,
    inBlock = false;
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (inBlock) {
      comment++;
      if (line.includes("*/")) inBlock = false;
      continue;
    }
    if (line === "") {
      blank++;
      continue;
    }
    if (line.startsWith("//")) {
      comment++;
      continue;
    }
    if (line.startsWith("/*")) {
      comment++;
      if (!line.includes("*/")) inBlock = true;
      continue;
    }
    code++;
  }
  return { code, comment, blank };
}

function analyze(sf, out) {
  const ex = namedExportsOnly(sf);
  const im = collectImports(sf);
  out.exported_names = ex;
  out.exported_symbols = ex.length;
  out.exports_detail = collectExportDetail(sf);
  out.external_import_names = Array.from(new Set(im.filter(isExternal))).sort();
  out.external_imports = out.external_import_names.length;
  out.internal_imports = im.filter((s) => !isExternal(s)).length;
  out.max_nesting = maxNesting(sf);
  out.errors = collectErrors(sf);
  const logs = collectLogs(sf);
  out.log_calls = logs.total;
  out.log_by_level = logs.byLevel;
  out.schemas = collectSchemas(sf);
}

function parseFile(relPath, kind) {
  const abs = path.join(REPO, relPath);
  const text = fs.readFileSync(abs, "utf8");
  const totalLines = text.split("\n").length - (text.endsWith("\n") ? 1 : 0);
  const loc = countCodeLines(text);

  const out = {
    path: relPath,
    lines: totalLines,
    code_lines: loc.code,
    comment_lines: loc.comment,
    blank_lines: loc.blank,
    method: "",
    limitations: "",
    exported_symbols: 0,
    exported_names: [],
    exports_detail: [],
    external_imports: 0,
    external_import_names: [],
    internal_imports: 0,
    max_nesting: null,
    parse_errors: [],
    parse_ok: true,
    errors: [],
    log_calls: 0,
    log_by_level: {},
    schemas: [],
  };

  if (kind === "astro") {
    // .astro cannot be parsed by the TS compiler: we measure the frontmatter
    // script (leading `---` fence) with the real TS parser; template markup is
    // not analyzed.
    const lines = text.split("\n");
    let start = -1,
      end = -1;
    if (lines[0] !== undefined && lines[0].trim() === "---") {
      start = 1;
      for (let i = 1; i < lines.length; i++) {
        if (lines[i].trim() === "---") {
          end = i;
          break;
        }
      }
    }
    const fm =
      start >= 0 && end > start ? lines.slice(start, end).join("\n") : "";
    out.method = "astro-frontmatter-ts-parse+lexical-template";
    out.limitations =
      "template markup/expressions not AST-analyzed; frontmatter only";
    out.frontmatter_lines = fm ? fm.split("\n").length : 0;
    if (fm) {
      const sf = ts.createSourceFile(
        relPath + ".__fm.ts",
        fm,
        ts.ScriptTarget.Latest,
        true,
        ts.ScriptKind.TS,
      );
      out.parse_errors = sf.parseDiagnostics.map((d) =>
        ts.flattenDiagnosticMessageText(d.messageText, " "),
      );
      out.parse_ok = out.parse_errors.length === 0;
      analyze(sf, out);
      for (const r of out.exports_detail) r.line += start;
      for (const r of out.errors) r.line += start;
      for (const r of out.schemas) r.line += start;
    }
    return out;
  }

  const scriptKind = relPath.endsWith(".tsx")
    ? ts.ScriptKind.TSX
    : relPath.endsWith(".jsx")
      ? ts.ScriptKind.JSX
      : relPath.endsWith(".mjs") ||
          relPath.endsWith(".js") ||
          relPath.endsWith(".cjs")
        ? ts.ScriptKind.JS
        : ts.ScriptKind.TS;
  out.method = "typescript-compiler-ast";
  out.limitations =
    "nesting = max AST block-owner depth from file root (functions/classes count as 1 level); not cyclomatic complexity";
  const sf = ts.createSourceFile(
    relPath,
    text,
    ts.ScriptTarget.Latest,
    true,
    scriptKind,
  );
  out.parse_errors = sf.parseDiagnostics.map((d) =>
    ts.flattenDiagnosticMessageText(d.messageText, " "),
  );
  out.parse_ok = out.parse_errors.length === 0;
  analyze(sf, out);
  return out;
}

const result = { files: {}, tsVersion: ts.version, error: null };
for (const entry of inputList) {
  try {
    result.files[entry.path] = parseFile(entry.path, entry.kind);
  } catch (e) {
    result.files[entry.path] = {
      path: entry.path,
      error: String(e),
      parse_ok: false,
      method: "failed",
      errors: [],
      exports_detail: [],
      schemas: [],
      log_calls: 0,
      log_by_level: {},
    };
  }
}
process.stdout.write(JSON.stringify(result));
