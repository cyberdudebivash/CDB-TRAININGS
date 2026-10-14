"""Reusable forensic primitives for the source PDFs.

Every function is deterministic and returns plain data (dicts/lists) so results can be
serialised to docs/audits/data/*.json and re-verified by anyone with the same PDFs.

Important limits (documented in docs/audits/SOURCE_FORENSICS_METHOD.md)
----------------------------------------------------------------------
* Source PDFs have no monospace font, so code regions are detected heuristically.  Parse
  failures are therefore *candidates* for defects and must be triaged by a human before being
  reported as defects.  Triage results live in docs/audits/data/code_triage.json.
* Section depth is approximated from outline bookmarks located in the text layer.
"""
from __future__ import annotations

import ast
import re
import textwrap
from collections import Counter, defaultdict
from dataclasses import dataclass

# --------------------------------------------------------------------------- text cleanup

PAGE_NO = re.compile(r"^\s*\d{1,5}\s*$")
ZW = dict.fromkeys(map(ord, "​‌‍⁠﻿"), None)  # zero-width chars from Google Docs


def clean_line(line: str) -> str:
    return line.translate(ZW).rstrip()


def norm_line(line: str) -> str:
    return re.sub(r"\s+", " ", clean_line(line)).strip()


def page_lines(pages: list[str]) -> list[tuple[int, str]]:
    """Flatten pages to (page_number, line) pairs, dropping bare page-number footers."""
    out = []
    for i, pg in enumerate(pages, start=1):
        for ln in pg.split("\n"):
            ln = clean_line(ln)
            if PAGE_NO.match(ln):
                continue
            out.append((i, ln))
    return out


# --------------------------------------------------------------------------- sections / depth


def _norm_title(t: str) -> str:
    t = re.sub(r"[^\w\s.]", " ", t, flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip().lower()


@dataclass
class Section:
    level: int
    title: str
    page: int
    words: int = 0


def section_depth(pages: list[str], outline: list[dict]) -> list[Section]:
    """Approximate words per outline section.

    A section's body is the text from its heading (located in the page text) up to the next
    outline entry's heading.  When a heading cannot be located on its page the page start is
    used.  This is an approximation, but it is deterministic and good enough to separate
    one-sentence stubs from substantive lessons.
    """
    # Build a flat word-offset index per page.
    page_words = [len(re.findall(r"\w+", p)) for p in pages]
    secs: list[Section] = []
    entries = [o for o in outline if o["page"] and o["title"].strip()]
    entries.sort(key=lambda o: o["page"])  # stable: keeps document order within a page
    positions = []
    for o in entries:
        pg = pages[o["page"] - 1] if 0 < o["page"] <= len(pages) else ""
        needle = _norm_title(o["title"])[:40]
        hay = _norm_title(pg)
        idx = hay.find(needle) if needle else -1
        frac = idx / max(len(hay), 1) if idx >= 0 else 0.0
        positions.append((o["page"], frac))
    for i, o in enumerate(entries):
        pg, frac = positions[i]
        if i + 1 < len(entries):
            npg, nfrac = positions[i + 1]
        else:
            npg, nfrac = len(pages), 1.0
        if npg == pg:
            words = max(0, round((nfrac - frac) * page_words[pg - 1]))
        else:
            words = round((1 - frac) * page_words[pg - 1])
            words += sum(page_words[pg : npg - 1])
            words += round(nfrac * page_words[npg - 1])
        secs.append(Section(o["level"], o["title"], o["page"], words))
    return secs


def depth_profile(secs: list[Section]) -> dict:
    w = sorted(s.words for s in secs)
    n = len(w)
    if not n:
        return {"sections": 0}

    def pct(p):
        return w[min(n - 1, int(p * n))]

    return {
        "sections": n,
        "median_words": pct(0.5),
        "p25_words": pct(0.25),
        "p75_words": pct(0.75),
        "p90_words": pct(0.9),
        "share_under_40_words": round(sum(1 for x in w if x < 40) / n, 3),
        "share_under_100_words": round(sum(1 for x in w if x < 100) / n, 3),
        "share_over_400_words": round(sum(1 for x in w if x >= 400) / n, 3),
    }


# --------------------------------------------------------------------------- raw markdown leakage


def markdown_leakage(pages: list[str]) -> dict:
    txt = "\n".join(pages)
    return {
        "code_fences": len(re.findall(r"^\s*```", txt, flags=re.M)),
        "hr_dividers": len(re.findall(r"^\s*---+\s*$", txt, flags=re.M)),
        "bold_markers": len(re.findall(r"\*\*[^*\n]+\*\*", txt)),
        "atx_headers": len(re.findall(r"^\s*#{1,6}\s+\S", txt, flags=re.M)),
    }


# --------------------------------------------------------------------------- code extraction

PY_STRONG = re.compile(
    r"^\s*(def \w+\(|class \w+|import [\w., ]+$|from [\w.]+ import |@\w[\w.]*(\(.*\))?$|if __name__|"
    r"elif .+:$|else:$|try:$|except\b.*:$|finally:$|with .+:$|for .+ in .+:$|while .+:$|if .+:$|"
    r"return\b|raise\b|assert\b|yield\b|pass$|break$|continue$|async def |await |print\()"
)
PY_ASSIGN = re.compile(r"^\s*[A-Za-z_][\w.\[\]'\"]*\s*(=|\+=|-=|\*=|/=|:=)\s*\S")
PY_CALL = re.compile(r"^\s*[A-Za-z_][\w.]*\(.*\)\s*$")
PY_COMMENT = re.compile(r"^\s*#")
PY_CLOSER = re.compile(r"^\s*[)\]}],?\s*$")
PY_START = re.compile(r"^(def \w+\(|class \w+|import [\w., ]+$|from [\w.]+ import |@\w|if __name__)")
PROSE = re.compile(r"^[A-Z][a-z]+(?:\s+[\w'’,/()-]+){5,}[.:!?]?$")  # sentence-like


def looks_prose(line: str) -> bool:
    s = line.strip()
    if not s or s.startswith(("#", "●", "•", "-", "*", "✔", "✅", "❌", "⭐", "🔥", "📘", "🧪")):
        return s.startswith(("●", "•", "✔", "✅", "❌", "⭐", "🔥", "📘", "🧪"))
    if any(ch in s for ch in "(){}[]=") and not s.endswith("."):
        return False
    return bool(PROSE.match(s))


def looks_code_py(line: str) -> bool:
    return bool(
        PY_STRONG.match(line)
        or PY_ASSIGN.match(line)
        or PY_CALL.match(line)
        or PY_COMMENT.match(line)
        or PY_CLOSER.match(line)
    )


@dataclass
class CodeBlock:
    lang: str
    page: int
    first_line: str
    n_lines: int
    status: str  # PARSE_OK | PARSE_FAIL
    error: str = ""
    trimmed_lines: int = 0
    text: str = ""


def _try_parse_py(src: str) -> tuple[bool, str]:
    try:
        ast.parse(src)
        return True, ""
    except SyntaxError as exc:
        return False, f"{exc.msg} (line {exc.lineno})"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def _bracket_delta(line: str) -> int:
    """Net open brackets on a line, ignoring bracket characters inside simple string literals."""
    stripped = re.sub(r"(\"[^\"]*\"|'[^']*')", "", line)
    stripped = stripped.split("#", 1)[0]
    return sum(stripped.count(c) for c in "([{") - sum(stripped.count(c) for c in ")]}")


def extract_python_blocks(pages: list[str], min_lines: int = 3) -> list[CodeBlock]:
    """Heuristic Python block extraction.

    A block starts at a strong Python statement and continues over lines that look like code, or that
    are legitimately continuation lines (inside open brackets, inside a triple-quoted string, or after a
    trailing comma/backslash/operator).  Anything else (prose, headings, file labels) ends the block.
    """
    lines = page_lines(pages)
    blocks: list[CodeBlock] = []
    run: list[tuple[int, str]] = []
    depth = 0
    in_triple = False
    prev = ""

    def flush():
        nonlocal run, depth, in_triple, prev
        code = [(p, l) for p, l in run if l.strip()]
        run, depth, in_triple, prev = [], 0, False, ""
        if len(code) < min_lines:
            return
        if not any(PY_STRONG.match(l) or PY_ASSIGN.match(l) for _, l in code):
            return
        text_lines = [l for _, l in code]
        src = textwrap.dedent("\n".join(text_lines)) + "\n"
        ok, err = _try_parse_py(src)
        trimmed = 0
        while not ok and trimmed < 6 and len(text_lines) - trimmed > min_lines:
            trimmed += 1
            ok, err2 = _try_parse_py(textwrap.dedent("\n".join(text_lines[: len(text_lines) - trimmed])) + "\n")
            if ok:
                err = ""
                break
        blocks.append(
            CodeBlock("python", code[0][0], text_lines[0].strip()[:90], len(text_lines), "PARSE_OK" if ok else "PARSE_FAIL", "" if ok else err, trimmed if ok else 0, src)
        )

    for pg, ln in lines:
        if not ln.strip():
            continue
        if run:
            continuation = in_triple or depth > 0 or prev.rstrip().endswith((",", "\\", "(", "[", "{", "+", " and", " or"))
            if looks_code_py(ln) or continuation:
                run.append((pg, ln))
                if ln.count('"""') % 2 == 1 or ln.count("\'\'\'") % 2 == 1:
                    in_triple = not in_triple
                if not in_triple:
                    depth = max(0, depth + _bracket_delta(ln))
                prev = ln
                continue
            flush()
        if PY_START.match(ln.strip()) and not looks_prose(ln):
            run = [(pg, ln)]
            depth = max(0, _bracket_delta(ln))
            in_triple = ln.count('"""') % 2 == 1
            prev = ln
    flush()
    return blocks


JAVA_START = re.compile(
    r"^\s*(package [\w.]+;|import (static )?[\w.*]+;|public (final |abstract )?class \w+|class \w+|"
    r"public (static )?(void|int|String|boolean) \w+\(|@Test\b|@BeforeEach\b|@BeforeMethod\b|@Before\b|@After\w*\b)"
)
JAVA_CODEISH = re.compile(
    r"(;\s*$|\{\s*$|^\s*\}|^\s*@\w+|^\s*(public|private|protected|static|final|void|if|for|while|try|catch|return|new)\b|"
    r"^\s*//|\)\s*\{|^\s*[\w<>\[\], ?]+\s+\w+\s*=\s*.+;)"
)


def extract_java_blocks(pages: list[str], min_lines: int = 3) -> list[CodeBlock]:
    import javalang  # local import: optional dependency

    lines = page_lines(pages)
    blocks: list[CodeBlock] = []
    run: list[tuple[int, str]] = []
    gap = 0

    def try_parse(src: str) -> tuple[bool, str]:
        candidates = [src, f"class __W {{\n{src}\n}}", f"class __W {{ void __m() {{\n{src}\n}} }}"]
        last = ""
        for cand in candidates:
            try:
                javalang.parse.parse(cand)
                return True, ""
            except Exception as exc:  # noqa: BLE001
                last = f"{type(exc).__name__}: {exc}"[:160]
        return False, last

    def flush():
        nonlocal run
        code = [(p, l) for p, l in run if l.strip()]
        run = []
        if len(code) < min_lines:
            return
        text_lines = [l for _, l in code]
        src = textwrap.dedent("\n".join(text_lines)) + "\n"
        ok, err = try_parse(src)
        trimmed = 0
        while not ok and trimmed < 6 and len(text_lines) - trimmed > min_lines:
            trimmed += 1
            ok, err = try_parse(textwrap.dedent("\n".join(text_lines[: len(text_lines) - trimmed])) + "\n")
        blocks.append(
            CodeBlock("java", code[0][0], text_lines[0].strip()[:90], len(text_lines), "PARSE_OK" if ok else "PARSE_FAIL", "" if ok else err, trimmed if ok else 0, src)
        )

    for pg, ln in lines:
        if not ln.strip():
            gap += 1
            continue
        if run:
            if JAVA_CODEISH.search(ln) or ln.startswith(("  ", "\t")):
                run.append((pg, ln))
                gap = 0
                continue
            if looks_prose(ln) or gap > 3:
                flush()
                gap = 0
            else:
                run.append((pg, ln))
                continue
        if JAVA_START.match(ln) and not looks_prose(ln):
            run = [(pg, ln)]
            gap = 0
    flush()
    return blocks


# --------------------------------------------------------------------------- pattern scanners

# Unsupported / absolute marketing and outcome claims (case-insensitive).
CLAIM_PATTERNS = {
    "guarantee": r"\bguarantee[sd]?\b",
    "job_placement": r"\b(get(ting)? hired|job[- ]ready|job[- ]guarantee|land(ing)? (a |your )?(job|role)|placement)\b",
    "top_percent": r"\btop[- ]?(1|5|10)\s?%|\bfaang\b|\bbig tech\b|\bworld[- ]class\b|\bglobal(ly)? (no\.?\s?1|#1)\b",
    "salary": r"(\$\s?\d{2,3}\s?[kK]\b|₹\s?\d+\s?(LPA|lakh)|\bLPA\b|\bsalary\b|\bsalaries\b)",
    "percent_stat": r"\b\d{2,3}\s?(–|-|to)\s?\d{2,3}\s?%|\b\d{2,3}\s?%\s+(of|reduction|drop|increase|faster)",
    "expert_promise": r"\b(become|become an?|zero to) (an? )?(expert|master|hero|leader|architect)\b|\bzero\s*(→|->|to)\s*(hero|expert|leader|pro)\b",
    "certification_claim": r"\b(certificate|certification) (will|is) (valid|recognized|accepted)\b|\bindustry[- ]recognized\b",
    "internal_framework_branding": r"\bCDB[- ]?[A-Z0-9-]+\b|\bCyberDudeBivash\s+(\d+[- ]?(Phase|Step|Level)|Blueprint|Model|Method|Framework|Unified)",
}

# Technology-currency flags: pattern -> note.  Matches are *candidates*; each is triaged by hand
# before it appears as a finding (see docs/audits/TECHNICAL_GAP_MATRIX.md).
CURRENCY_PATTERNS = {
    "python2": (r"\bpython ?2(\.\d)?\b|\bprint\s+[\"'][^\"']+[\"']\s*$", "Python 2 reference/syntax"),
    "python_old_version": (r"\bpython ?3\.(6|7|8)\b", "Python <=3.8 is end-of-life"),
    "selenium3": (r"\bselenium ?(3|2)\.\d|\bfind_element_by_\w+\(|\bDesiredCapabilities\b", "Selenium 3 era API"),
    "java_old": (r"\bjava ?(6|7|8|11)\b|\bjdk ?(6|7|8|11)\b", "Older Java baseline referenced"),
    "log4j": (r"\blog4j ?(1|2)?\b", "log4j reference (verify version/security posture)"),
    "tf1": (r"\btensorflow ?(1\.\d|v1)\b|\btf\.Session\b|\btf\.placeholder\b", "TensorFlow 1.x API"),
    "openai_legacy": (r"\btext-davinci|\bgpt-3\b|\bopenai\.Completion\b|\bChatCompletion\.create\b|\bgpt-3\.5", "Legacy OpenAI models/APIs"),
    "langchain_legacy": (r"\bLLMChain\b|\bfrom langchain import\b|\binitialize_agent\b|\bConversationChain\b", "Deprecated LangChain APIs"),
    "angular_js": (r"\bangularjs\b|\bcreate-react-app\b|\bcomponentWillMount\b|\bReact\.createClass\b", "Deprecated front-end tooling/APIs"),
    "gcp_legacy": (r"\bcloud ?(datalab|functions 1st gen)\b|\bdataproc ?(1\.[0-3])\b|\bgsutil\b|\bcloud ?composer ?1\b|\bapp ?engine ?standard ?python ?2\b", "Legacy/superseded GCP tooling"),
    "tls_old": (r"\btls ?1\.[01]\b|\bssl ?v?[23]\b", "Deprecated TLS/SSL versions referenced"),
    "md5_sha1": (r"\b(md5|sha-?1)\b", "Weak hash referenced (check context: IOC hash vs. integrity use)"),
    "windows_old": (r"\bwindows ?(7|8|xp|server 2008|server 2012)\b|\bcentos ?(6|7|8)\b", "End-of-life OS referenced"),
    "kali_cmds": (r"\bmetasploit\b|\bmsfvenom\b|\bmimikatz\b|\bhydra\b|\bsqlmap\b|\bnmap -s[SUV]", "Offensive tooling reference (check ethical/authorised-use framing)"),
}

# Security anti-patterns in code regions only.
PY_SECURITY_PATTERNS = {
    "eval_exec": r"(?<![\w.])(eval|exec)\s*\(",  # excludes attribute calls such as model.eval() / app.exec()
    "shell_true": r"shell\s*=\s*True",
    "verify_false": r"verify\s*=\s*False",
    "pickle_load": r"\bpickle\.loads?\(",
    "yaml_unsafe": r"\byaml\.load\((?![^)]*Loader\s*=\s*(yaml\.)?SafeLoader)",
    "os_system": r"\bos\.system\(",
    "hardcoded_secret": r"(?i)\b(password|passwd|secret|api[_-]?key|token)\s*=\s*[\"'][^\"']{4,}[\"']",
    "md5_sha1_use": r"hashlib\.(md5|sha1)\(",
    "input_to_sql": r"(?i)(execute\(\s*f[\"']|execute\([\"'].*%s.*[\"']\s*%\s*\w|\"SELECT .*\"\s*\+\s*\w)",
    "bare_except": r"^\s*except\s*:",
    "debug_true": r"(?i)debug\s*=\s*True",
    "tmp_insecure": r"/tmp/",
    "ssh_autoadd_hostkey": r"AutoAddPolicy\(",
    "weak_default_password": r"(?i)password\s*=\s*[\"'](password\d*|admin\d*|pass\d*|123456|root|changeme)[\"']|[\"'](password123|admin123|pass123)[\"']",
}

SECRET_PATTERNS = {
    "aws_access_key": r"\bAKIA[0-9A-Z]{16}\b",
    "github_token": r"\bgh[pousr]_[A-Za-z0-9]{36,}\b",
    "private_key": r"-----BEGIN (RSA |EC |OPENSSH |DSA |)PRIVATE KEY-----",
    "slack_token": r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b",
    "google_api_key": r"\bAIza[0-9A-Za-z_-]{35}\b",
    "jwt": r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
    "generic_assignment": r"(?i)\b(api[_-]?key|secret|token|passwd|password)\b\s*[:=]\s*[\"']?[A-Za-z0-9_\-/+=]{20,}[\"']?",
}
PII_PATTERNS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    # international phone numbers with an explicit country code (low false-positive rate)
    "phone_with_country_code": r"(?<![\w.])\+\d{1,3}[ -]?\(?\d{2,5}\)?[ -]?\d{3,5}[ -]?\d{3,5}(?![\w])",
}
SYNTHETIC_EMAIL_DOMAINS = {
    "example.com", "example.org", "example.net", "example.test", "test.com", "email.com", "domain.com",
    "company.com", "mail.com", "yourcompany.com", "acme.com", "corp.com", "b.com", "x.com",
}
SYNTHETIC_EMAIL_LOCALS = {
    "user", "admin", "you", "target", "test", "demo", "qa", "a", "x", "email", "info", "support", "hello",
    "john", "jane", "alice", "bob", "name", "username", "your", "yourname", "someone", "sample", "foo", "bar",
}


def mask_pii(value: str) -> str:
    """Irreversibly mask an e-mail address or phone number for evidence records."""
    if "@" in value:
        local, domain = value.split("@", 1)
        return f"{local[:1]}***@{domain}"
    digits = re.sub(r"\D", "", value)
    return f"+{digits[:2]}*****{digits[-2:]}" if len(digits) >= 6 else "***"


def classify_email(value: str) -> str:
    local, _, domain = value.lower().partition("@")
    if domain in SYNTHETIC_EMAIL_DOMAINS or local in SYNTHETIC_EMAIL_LOCALS or domain.endswith(".test"):
        return "synthetic_placeholder"
    return "review_needed"


def scan_pii(pages: list[str]) -> dict:
    """PII scan that NEVER stores raw values: only counts, page numbers and masked forms."""
    out: dict = {"email": {"total": 0, "synthetic_placeholder": 0, "review_needed": 0, "review_pages": [], "review_masked": []},
                 "phone_with_country_code": {"total": 0, "pages": [], "masked": []}}
    em = re.compile(PII_PATTERNS["email"])
    ph = re.compile(PII_PATTERNS["phone_with_country_code"])
    for i, pg in enumerate(pages, start=1):
        for m in em.finditer(pg):
            v = m.group(0)
            out["email"]["total"] += 1
            cls = classify_email(v)
            out["email"][cls] += 1
            if cls == "review_needed":
                out["email"]["review_pages"].append(i)
                masked = mask_pii(v)
                if masked not in out["email"]["review_masked"]:
                    out["email"]["review_masked"].append(masked)
        for m in ph.finditer(pg):
            out["phone_with_country_code"]["total"] += 1
            out["phone_with_country_code"]["pages"].append(i)
            masked = mask_pii(m.group(0))
            if masked not in out["phone_with_country_code"]["masked"]:
                out["phone_with_country_code"]["masked"].append(masked)
    out["email"]["review_pages"] = sorted(set(out["email"]["review_pages"]))[:40]
    out["email"]["review_masked"] = out["email"]["review_masked"][:20]
    out["phone_with_country_code"]["pages"] = sorted(set(out["phone_with_country_code"]["pages"]))[:40]
    out["phone_with_country_code"]["masked"] = out["phone_with_country_code"]["masked"][:20]
    return out


URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")


def _is_placeholder(token: str) -> bool:
    body = re.sub(r"^[A-Za-z]{2,5}_", "", token)
    return len(set(body.lower())) <= 3 or bool(re.search(r"(x{6,}|\*{4,}|your[_-]|example|changeme)", token, re.I))


def scan(pages: list[str], patterns: dict[str, str], flags=re.I, max_examples: int = 5, skip_placeholders: bool = False) -> dict:
    """Count matches per pattern and keep a few (page, snippet) examples."""
    result = {}
    compiled = {k: re.compile(v, flags | re.M) for k, v in patterns.items()}
    for key, rx in compiled.items():
        count = 0
        examples = []
        pages_hit = set()
        for i, pg in enumerate(pages, start=1):
            for m in rx.finditer(pg):
                if skip_placeholders and _is_placeholder(m.group(0)):
                    continue
                count += 1
                pages_hit.add(i)
                if len(examples) < max_examples:
                    s = max(0, m.start() - 50)
                    snippet = re.sub(r"\s+", " ", pg[s : m.end() + 70]).strip()
                    examples.append({"page": i, "snippet": snippet[:200]})
        result[key] = {"count": count, "pages": len(pages_hit), "examples": examples}
    return result


def scan_code_blocks(blocks: list[CodeBlock], patterns: dict[str, str]) -> dict:
    out = {}
    for key, pat in patterns.items():
        rx = re.compile(pat, re.M)
        hits = []
        for b in blocks:
            for m in rx.finditer(b.text):
                hits.append({"page": b.page, "snippet": re.sub(r"\s+", " ", b.text[max(0, m.start() - 30) : m.end() + 50]).strip()[:160]})
        out[key] = {"count": len(hits), "examples": hits[:5]}
    return out


# --------------------------------------------------------------------------- duplication


def line_fingerprints(pages: list[str], min_len: int = 50) -> dict[str, list[int]]:
    """normalised long line -> pages where it occurs."""
    fp: dict[str, list[int]] = defaultdict(list)
    for i, pg in enumerate(pages, start=1):
        for ln in pg.split("\n"):
            n = norm_line(ln)
            if len(n) >= min_len:
                fp[n.lower()].append(i)
    return fp


def intra_duplication(fp: dict[str, list[int]]) -> dict:
    total = sum(len(v) for v in fp.values())
    repeated_occ = sum(len(v) for v in fp.values() if len(v) > 1)
    top = sorted(((len(v), k, v[:6]) for k, v in fp.items() if len(v) > 1), reverse=True)[:8]
    return {
        "long_lines_total": total,
        "long_lines_in_repeats": repeated_occ,
        "share_repeated": round(repeated_occ / max(total, 1), 3),
        "top_repeated": [{"count": c, "text": k[:140], "pages": pg} for c, k, pg in top],
    }


def cross_duplication(fps: dict[str, dict[str, list[int]]]) -> list[dict]:
    """Pairwise overlap of long lines between documents (by shared normalised lines)."""
    names = sorted(fps)
    rows = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            sa, sb = set(fps[a]), set(fps[b])
            shared = sa & sb
            if not shared:
                continue
            rows.append(
                {
                    "a": a,
                    "b": b,
                    "shared_long_lines": len(shared),
                    "share_of_a": round(len(shared) / max(len(sa), 1), 4),
                    "share_of_b": round(len(shared) / max(len(sb), 1), 4),
                    "examples": [s[:120] for s in sorted(shared, key=len, reverse=True)[:3]],
                }
            )
    rows.sort(key=lambda r: -r["shared_long_lines"])
    return rows


def heading_overlap(outlines: dict[str, list[dict]]) -> list[dict]:
    """Share of normalised heading titles that also occur in another document."""
    norm = lambda t: re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)).strip().lower()  # noqa: E731
    sets = {k: {norm(o["title"]) for o in v if len(norm(o["title"])) >= 12} for k, v in outlines.items()}
    rows = []
    names = sorted(sets)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            shared = sets[a] & sets[b]
            if len(shared) >= 5:
                rows.append({"a": a, "b": b, "shared_headings": len(shared), "examples": sorted(shared, key=len, reverse=True)[:4]})
    rows.sort(key=lambda r: -r["shared_headings"])
    return rows


# --------------------------------------------------------------------------- pedagogy signals

SIGNALS = {
    "lab_heading": r"\blab\b",
    "quiz_or_exam": r"\b(quiz|exam|test your|knowledge check|mcq|multiple choice|assessment)\b",
    "answer_key": r"\b(answer key|answers?:|solution:|expected (output|result))\b",
    "learning_objective": r"\b(learning objectives?|you will learn|by the end|outcomes?)\b",
    "capstone": r"\bcapstone\b",
    "rubric": r"\brubric\b|\bgrading criteria\b|\bpass (mark|score|criteria)\b",
    "prerequisite": r"\bprerequisites?\b",
    "reference_or_citation": r"\b(references?|sources?|further reading|bibliography)\b",
    "verification_step": r"\b(verify|validation|expected output|you should see|success criteria)\b",
    "troubleshooting": r"\b(troubleshoot\w*|common (mistakes|errors|pitfalls))\b",
    "disclaimer_legal": r"\b(authorized|authorised|legal|lawful|permission|consent|ethic\w+)\b",
    "interview": r"\binterview\b",
}


def pedagogy_signals(outline: list[dict], pages: list[str]) -> dict:
    heads = " \n".join(o["title"] for o in outline)
    body = "\n".join(pages)
    res = {}
    for k, pat in SIGNALS.items():
        rx = re.compile(pat, re.I)
        res[k] = {"in_headings": len(rx.findall(heads)), "in_body": len(rx.findall(body))}
    return res


def top_urls(pages: list[str], limit: int = 40) -> dict:
    c: Counter = Counter()
    for pg in pages:
        for m in URL_RE.finditer(pg):
            c[m.group(0).rstrip(".,;")] += 1
    domains = Counter(re.sub(r"^https?://([^/]+).*", r"\1", u).lower() for u in c.elements())
    return {"distinct_urls": len(c), "top_domains": domains.most_common(15), "sample": sorted(c)[:limit]}


# --------------------------------------------------------------------------- mandated-topic coverage probes
# Keyword probes derived from the task directive, section 7 (one block per course).  A count of zero is a
# *definitive* coverage gap; a non-zero count only shows the term is mentioned - depth is judged separately
# (see section-depth profile and manual sampling in docs/audits/TECHNICAL_GAP_MATRIX.md).
COVERAGE_PROBES: dict[str, dict[str, str]] = {
    "SRC-AI-BUNDLE": {
        "ml_fundamentals": r"\bsupervised\b|\bgradient descent\b|\boverfitting\b",
        "model_evaluation": r"\bprecision\b.*\brecall\b|\bconfusion matrix\b|\bcross[- ]validation\b|\bROC\b",
        "rag": r"\bRAG\b|retrieval[- ]augmented",
        "embeddings": r"\bembeddings?\b",
        "retrieval_evaluation": r"recall@|precision@|\bMRR\b|\bnDCG\b|\bRAGAS\b|faithfulness|context (precision|recall)",
        "reranking": r"\brerank",
        "tool_calling_structured_output": r"tool calling|function calling|structured output|JSON schema",
        "agent_workflows": r"\bagentic\b|\bagent\b",
        "context_engineering": r"context engineering|context window management",
        "mcp": r"Model Context Protocol|\bMCP\b",
        "prompt_injection": r"prompt injection",
        "owasp_llm_top10": r"OWASP",
        "mitre_atlas": r"MITRE ATLAS|\bATLAS\b",
        "nist_ai_rmf": r"NIST AI RMF|AI Risk Management Framework",
        "iso_42001": r"42001",
        "eu_ai_act": r"EU AI Act",
        "llm_eval_suite": r"eval(uation)? (suite|harness|set)|golden (set|dataset)|regression test",
        "observability_tracing": r"observability|tracing|OpenTelemetry|LangSmith|Langfuse",
        "cost_latency": r"\blatency\b|token cost|cost per",
        "human_approval": r"human[- ]in[- ]the[- ]loop|human approval",
    },
    "SRC-PY-HANDBOOK": {
        "type_hints": r"type hints?|\bmypy\b|from typing import|-> ?\w+:",
        "packaging_pyproject": r"pyproject\.toml|setuptools|\bwheel\b|pip install -e",
        "virtualenv": r"\bvenv\b|virtualenv",
        "dependency_locking": r"\bpoetry\b|\buv (pip|sync|add|run)\b|pip-tools|requirements\.txt|pip freeze",
        "pytest": r"\bpytest\b",
        "unittest_mock": r"unittest\.mock|\bmock\b|monkeypatch",
        "logging": r"\blogging\b",
        "async": r"\basyncio\b|async def",
        "secure_coding": r"\bbandit\b|secure coding|sql injection|\bpip-audit\b|\bsafety check\b",
        "sql_parameterization": r"parameteri[sz]ed|placeholders?|VALUES ?\(\?|=\s*\?\s*[\"']?,\s*\(",
        "database": r"sqlalchemy|sqlite3|psycopg",
        "profiling": r"cProfile|timeit|profil(e|ing)\b|line_profiler",
        "ci_cd": r"GitHub Actions|CI/CD|pre-commit",
        "linting_formatting": r"\bruff\b|flake8|\bblack\b|pylint",
        "docs_tooling": r"\bsphinx\b|mkdocs|docstring",
        "python_version_policy": r"python ?3\.(9|10|11|12|13|14)",
    },
    "SRC-PY-AUTOMATION": {
        "scheduling": r"\bcron\b|apscheduler|\bschedule\b|systemd timer|task scheduler",
        "browser_automation": r"playwright|selenium",
        "idempotency": r"idempoten",
        "retry_backoff": r"backoff|\bretry\b",
        "secrets_handling": r"dotenv|secrets? manager|keyring|vault",
        "config_management": r"pydantic[- ]settings|\bconfig(uration)? (file|management)|yaml\.safe_load",
        "monitoring_alerting": r"monitoring|alerting|prometheus|healthcheck",
        "pytest": r"\bpytest\b",
        "docker": r"\bdocker(file)?\b",
        "ci_cd": r"GitHub Actions|CI/CD|jenkins",
        "type_hints": r"from typing import|-> ?\w+:",
        "audit_logging": r"audit (log|trail)",
        "file_locking_atomic": r"atomic|tempfile|os\.replace|flock",
    },
    "SRC-JAVA-AUTOTEST": {
        "junit5": r"JUnit ?5|jupiter",
        "testng": r"\bTestNG\b",
        "selenium": r"\bSelenium\b",
        "selenium4_features": r"Selenium ?4|relative locator|BiDi|Selenium Manager",
        "playwright_java": r"\bPlaywright\b",
        "rest_assured": r"REST ?Assured",
        "maven_gradle": r"\bMaven\b|\bGradle\b|pom\.xml",
        "ci_integration": r"\bJenkins\b|GitHub Actions|GitLab CI|CI/CD",
        "parallel_execution": r"parallel (execution|tests)|ThreadLocal|Selenium Grid",
        "flaky_tests": r"\bflaky\b|flakiness",
        "test_data": r"data[- ]driven|DataProvider|@ParameterizedTest",
        "reporting": r"\bAllure\b|ExtentReports?",
        "page_object": r"page object",
        "docker_testcontainers": r"\bDocker\b|Testcontainers",
        "java_17_21": r"Java ?(17|21|25)\b",
    },
    "SRC-OSINT-STARTER": {},  # image-only PDF: probes run on visually-transcribed notes, see audit
    "SRC-GCP-DATAENG": {
        "iam_least_privilege": r"\bIAM\b|least[- ]privilege|service accounts?",
        "cloud_storage": r"Cloud Storage|\bGCS\b",
        "bigquery": r"\bBigQuery\b",
        "partition_cluster": r"partition(ing|ed)|cluster(ing|ed)",
        "pubsub": r"Pub/?Sub",
        "dataflow_beam": r"\bDataflow\b|Apache Beam",
        "composer_airflow": r"\bComposer\b|\bAirflow\b",
        "dataform_dbt": r"\bDataform\b|\bdbt\b",
        "data_quality": r"data quality|great expectations|assertions?",
        "terraform": r"\bTerraform\b",
        "cost_controls": r"cost|budget|slot|on-demand|quota",
        "dlp_cmek_vpcsc": r"\bDLP\b|\bCMEK\b|VPC[- ]SC|VPC Service Controls",
        "dataplex_catalog": r"\bDataplex\b|Data Catalog",
        "biglake_iceberg": r"\bBigLake\b|\bIceberg\b",
        "datastream_cdc": r"Datastream|\bCDC\b",
        "certification_alignment": r"Professional Data Engineer|certification exam",
        "free_tier_sandbox": r"free tier|sandbox|\$300|free credit|emulator",
        "cleanup_teardown": r"clean ?up|tear ?down|delete (the )?(project|resources?)",
    },
    "SRC-FRONTEND-ONBOARD": {
        "html_semantics": r"semantic html|<(main|nav|article|section|header|footer)\b",
        "css_layout": r"\bflexbox\b|\bCSS grid\b|media quer|container quer",
        "typescript": r"\bTypeScript\b",
        "react": r"\bReact\b",
        "nextjs": r"Next\.js",
        "accessibility_wcag": r"\bWCAG\b|\baria-|screen reader",
        "security_xss_csp": r"\bXSS\b|\bCSP\b|Content[- ]Security[- ]Policy|\bCSRF\b",
        "testing": r"\bJest\b|\bVitest\b|Testing Library|Playwright|Cypress",
        "performance_cwv": r"Core Web Vitals|\bLCP\b|\bINP\b|\bCLS\b",
        "git_workflow": r"pull request|git rebase|git branch|conventional commits",
        "code_review": r"code review",
        "dependency_security": r"npm audit|dependabot|lockfile|package-lock",
        "api_integration": r"\bfetch\(|axios|REST API|GraphQL",
        "auth_concepts": r"\bOAuth\b|\bJWT\b|\bOIDC\b|session cookie|httpOnly",
        "error_handling": r"error boundar|try/catch|error handling",
    },
    "SRC-SOC-PLAYBOOK": {
        "sigma": r"\bSigma\b",
        "siem_query_languages": r"\bSPL\b|\bKQL\b|ES\|QL|Lucene|\bEQL\b",
        "windows_event_ids": r"\b46(24|25|88|72|48)\b|Event ?ID",
        "sysmon": r"\bSysmon\b",
        "mitre_attack": r"MITRE|ATT&CK",
        "detection_engineering": r"detection engineering",
        "threat_hunting": r"hunt",
        "case_management": r"case management|TheHive",
        "malware_analysis": r"malware analysis|sandbox|\bYARA\b",
        "log_normalization": r"normali[sz]|parsing|\bECS\b|\bOCSF\b|\bCIM\b",
        "evidence_handling": r"chain of custody|evidence|forensic",
        "reporting": r"executive (summary|report)|incident report",
        "test_datasets": r"dataset|replay|atomic red team|synthetic",
        "ir_nist_800_61": r"800-61",
    },
    "SRC-MEGA-P1": {
        "mitre_attack": r"MITRE|ATT&CK",
        "nist_csf": r"NIST (CSF|Cybersecurity Framework)|\bCSF\b",
        "owasp": r"OWASP",
        "iso_27001": r"27001",
        "zero_trust": r"zero trust",
        "sigma_yara": r"\bSigma\b|\bYARA\b",
        "siem": r"\bSIEM\b",
        "lab_environment_spec": r"VirtualBox|VMware|Docker|vagrant|snapshot",
        "legal_authorisation": r"authori[sz]ed|written permission|rules of engagement|scope of work",
        "answer_keys": r"answer key|solution:",
    },
    "SRC-MEGA-P2": {
        "mitre_attack": r"MITRE|ATT&CK",
        "nist_csf": r"NIST (CSF|Cybersecurity Framework)|\bCSF\b",
        "owasp": r"OWASP",
        "supply_chain_slsa": r"\bSLSA\b|SBOM|sigstore|cosign",
        "cloud_security": r"\bAWS\b|\bAzure\b|\bGCP\b",
        "cti_stix": r"\bSTIX\b|\bTAXII\b",
        "lab_environment_spec": r"VirtualBox|VMware|Docker|vagrant|snapshot",
        "legal_authorisation": r"authori[sz]ed|written permission|rules of engagement|scope of work",
        "answer_keys": r"answer key|solution:",
    },
}


def coverage(pages: list[str], probes: dict[str, str]) -> dict:
    out = {}
    for name, pat in probes.items():
        rx = re.compile(pat, re.I)
        pages_hit = 0
        total = 0
        first = None
        for i, pg in enumerate(pages, start=1):
            n = len(rx.findall(pg))
            if n:
                total += n
                pages_hit += 1
                first = first or i
        status = "ABSENT" if total == 0 else ("MENTIONED_ONLY" if pages_hit < 5 else "PRESENT_BY_KEYWORD")
        out[name] = {"mentions": total, "pages_with_mention": pages_hit, "first_page": first, "status": status}
    return out
