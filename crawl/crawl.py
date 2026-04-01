import argparse
import hashlib
import json
import os
import re
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as html_to_markdown
from dotenv import load_dotenv


load_dotenv()


DOCS_DOCDATA_BASE = "https://resouces.modelscope.cn/document/docdata"
DEFAULT_DOCS_DOCDATA_VERSION = os.getenv("MODELSCOPE_DOCS_DOCDATA_VERSION", "2026-3-17_11-15-CN")


SOURCES = [
    {
        "name": "docs",
        "type": "web",
        "seeds": [
            "https://modelscope.cn/docs/home",
            "https://modelscope.cn/docs/overview",
        ],
        "allowed_domains": {"modelscope.cn", "www.modelscope.cn"},
        "include_prefixes": ["/docs"],
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_state(path: Path) -> Dict:
    if not path.exists():
        return {"pages": {}, "updated_at": now_iso()}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"pages": {}, "updated_at": now_iso()}


def save_state(path: Path, state: Dict) -> None:
    state["updated_at"] = now_iso()
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_url(url: str) -> str:
    clean, _ = urldefrag(url)
    parsed = urlparse(clean)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    if netloc == "www.modelscope.cn":
        netloc = "modelscope.cn"
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{scheme}://{netloc}{path}{query}"


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "index"


def file_path_for_url(output_root: Path, source_name: str, url: str) -> Path:
    parsed = urlparse(url)
    raw = f"{parsed.netloc}{parsed.path}"
    if parsed.query:
        raw += f"-{parsed.query}"
    name = slugify(raw)
    digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:10]
    return output_root / source_name / f"{name}-{digest}.md"


def docs_output_path_for_url(output_root: Path, url: str) -> Path:
    """按 docs 路由层级保存 markdown，例如 /docs/a/b -> data/raw/docs/a/b.md。"""
    rest = docs_rest_path(url)
    if not rest:
        return output_root / "docs" / "home.md"

    rel = Path(rest)
    if rel.name == "home":
        return output_root / "docs" / "home.md"

    return output_root / "docs" / rel.with_suffix(".md")


def fetch_title_mapping_origins(version: str, timeout: int) -> List[str]:
    mapping_url = f"{DOCS_DOCDATA_BASE}/{version}/dist/title-mapping.json"
    try:
        resp = requests.get(mapping_url, timeout=timeout)
        if resp.status_code >= 400:
            return []
        data = resp.json()
    except Exception:
        return []

    if not isinstance(data, dict):
        return []

    origins: List[str] = []
    seen: Set[str] = set()

    for val in data.values():
        if not isinstance(val, str):
            continue
        route = val.strip().strip("/")
        if not route:
            continue

        candidate = normalize_url(f"https://modelscope.cn/docs/{route}")
        if not is_valid_docs_origin(candidate):
            continue
        if candidate in seen:
            continue

        seen.add(candidate)
        origins.append(candidate)

    return origins


def allowed_url(url: str, allowed_domains: Set[str], include_prefixes: List[str]) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc.lower() not in allowed_domains:
        return False
    return any(parsed.path.startswith(prefix) for prefix in include_prefixes)


def pick_main_html(soup: BeautifulSoup) -> str:
    selectors = [
        ".acss-1qikrnb",
        "main",
        "article",
        "#content",
        ".markdown-body",
        ".doc-content",
        ".content",
        "body",
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            return str(node)
    return str(soup)


def render_markdown(url: str, source_name: str, title: str, html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()
    main_html = pick_main_html(soup)
    body_md = html_to_markdown(main_html, heading_style="ATX", strip=["script", "style", "noscript"])
    body_md = re.sub(r"\n{3,}", "\n\n", body_md).strip()

    return (
        f"> Source URL: {url}\n"
        f"> Title: {title}\n"
        f"> Data Type: doc\n"
        f"> Source Group: {source_name}\n"
        f"> Crawled At: {now_iso()}\n\n"
        f"# {title}\n\n"
        f"{body_md}\n"
    )


def extract_main_markdown(markdown_doc: str) -> str:
    lines = markdown_doc.splitlines()
    body_lines: List[str] = []
    in_body = False
    for line in lines:
        if in_body:
            body_lines.append(line)
            continue
        if line.startswith("# "):
            in_body = True
            body_lines.append(line)
    return "\n".join(body_lines).strip()


def is_markdown_thin(markdown_doc: str, min_chars: int = 120) -> bool:
    body = extract_main_markdown(markdown_doc)
    compact = re.sub(r"\s+", "", body)
    return len(compact) < min_chars


def extract_links_from_markdown(base_url: str, markdown_text: str) -> List[str]:
    links: List[str] = []

    # Markdown links: [text](target)
    md_targets = re.findall(r"\[[^\]]*\]\(([^)]+)\)", markdown_text)
    # Bare URLs
    bare_urls = re.findall(r"https?://[^\s)>\]]+", markdown_text)

    for href in md_targets + bare_urls:
        href = href.strip()
        if not href:
            continue
        if href.startswith(("javascript:", "mailto:", "data:")):
            continue
        # 忽略文档正文中的相对 .md 链接（如 ./模型库介绍.md），它们不是站点真实 docs 路由
        if href.endswith(".md") and not href.startswith(("http://", "https://", "/")):
            continue
        absolute = normalize_url(urljoin(base_url, href))
        links.append(absolute)

    # 去重并保持顺序
    deduped: List[str] = []
    seen: Set[str] = set()
    for link in links:
        if link in seen:
            continue
        seen.add(link)
        deduped.append(link)
    return deduped


def resolve_image_target_url(target: str, docdata_url: str, source_url: str) -> str:
    target = (target or "").strip()
    if not target:
        return target

    if target.startswith(("http://", "https://", "data:")):
        return target

    if docdata_url:
        return urljoin(docdata_url, target)

    if source_url:
        return urljoin(source_url, target)

    return target


def absolutize_markdown_image_links(markdown_text: str, docdata_url: str, source_url: str) -> str:
    if not markdown_text:
        return markdown_text

    pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

    def _replace(match: re.Match) -> str:
        alt = match.group(1)
        raw_target = match.group(2).strip()
        resolved = resolve_image_target_url(raw_target, docdata_url=docdata_url, source_url=source_url)
        return f"![{alt}]({resolved})"

    return pattern.sub(_replace, markdown_text)


def clean_reader_content(content: str) -> str:
    """清洗 reader 返回的整页 markdown，尽量保留文档正文并去掉导航/页脚噪声。"""
    lines = [line.rstrip() for line in content.splitlines()]

    def is_noise_line(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if stripped.startswith("![Image") and "blob:http" in stripped:
            return True
        if stripped.startswith("[]("):
            return True
        if stripped.startswith("[Home](") or stripped.startswith("[Models](") or stripped.startswith("[Datasets]("):
            return True
        if stripped.startswith("[Studios](") or stripped.startswith("[Docs]("):
            return True
        if "Terms-and-Condition" in stripped or "Privacy-Policy" in stripped:
            return True
        if stripped == "Community" or stripped == "分享":
            return True
        return False

    # 1) 去掉明显噪声行
    filtered = [line for line in lines if not is_noise_line(line)]

    # 2) 截掉正文前导导航：优先从“在 Notebook 打开”或首个一级标题开始
    start_idx = 0
    for i, line in enumerate(filtered):
        s = line.strip()
        if s == "在 Notebook 打开" or s.startswith("# "):
            start_idx = i
            break

    core = filtered[start_idx:]

    # 3) 截掉页脚区域
    footer_markers = (
        "用户协议",
        "隐私政策",
        "开源行为准则",
        "space.bilibili.com",
        "xiaohongshu.com",
        "douyin.com",
        "zhihu.com",
    )
    end_idx = len(core)
    for i, line in enumerate(core):
        s = line.strip()
        if any(marker in s for marker in footer_markers):
            end_idx = i
            break

    cleaned = "\n".join(core[:end_idx]).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def docs_rest_path(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or ""
    if not path.startswith("/docs"):
        return ""
    rest = path[len("/docs"):].strip("/")
    return rest


def is_valid_docs_origin(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    if parsed.netloc.lower() != "modelscope.cn":
        return False

    path = parsed.path or ""
    if not (path == "/docs" or path.startswith("/docs/")):
        return False

    # 过滤包含编码片段的路径，避免中文路由或异常 URL 混入
    if "%" in path:
        return False

    # 排除资源文件、静态文件链接
    low = path.lower()
    if "/_resources/" in low:
        return False
    if re.search(r"\.(png|jpg|jpeg|gif|svg|webp|bmp|ico|pdf|zip|md)$", low):
        return False

    rest = path[len("/docs"):].strip("/")
    if not rest:
        return True

    # 只保留规范 slug 路由（英数和短横线），过滤中文目录名和异常片段
    segments = [seg for seg in rest.split("/") if seg]
    for seg in segments:
        try:
            seg.encode("ascii")
        except UnicodeEncodeError:
            return False
        if not re.fullmatch(r"[A-Za-z0-9_-]+", seg):
            return False

    return True


def normalize_discovered_docs_link(session: requests.Session, link: str, timeout: int) -> Optional[str]:
    """将发现到的 docs 链接归一化为可抓取原网址。"""
    nlink = normalize_url(link)
    parsed = urlparse(nlink)

    if parsed.netloc.lower() not in {"modelscope.cn", "www.modelscope.cn"}:
        return None
    if not (parsed.path or "").startswith("/docs"):
        return None

    path = parsed.path or ""
    need_redirect_resolution = False
    if path.lower().endswith(".md"):
        need_redirect_resolution = True
    if "%" in path:
        need_redirect_resolution = True
    try:
        path.encode("ascii")
    except UnicodeEncodeError:
        need_redirect_resolution = True

    if need_redirect_resolution:
        redirected = resolve_docs_origin_via_redirect(session, nlink, timeout)
        if redirected:
            return redirected
        return None

    return nlink if is_valid_docs_origin(nlink) else None


def build_docdata_candidates(url: str, version: str) -> List[str]:
    rest = docs_rest_path(url)
    base = f"{DOCS_DOCDATA_BASE}/{version}/dist"

    if not rest:
        return [
            f"{base}/home/home_CN.md",
            f"{base}/overview/overview_CN.md",
        ]

    if rest == "home":
        return [
            f"{base}/home/home_CN.md",
            f"{base}/overview/overview_CN.md",
            f"{base}/home_CN.md",
        ]

    parts = [p for p in rest.split("/") if p]
    leaf = parts[-1]
    rel = "/".join(parts)
    parent = "/".join(parts[:-1]) if len(parts) > 1 else ""
    parent_leaf = parts[-2] if len(parts) > 1 else leaf

    candidates = [
        f"{base}/{rel}/{leaf}_CN.md",
        f"{base}/{rel}_CN.md",
    ]

    # 常见别名：/xxx/index 对应 /xxx/xxx_CN.md
    if leaf == "index" and parent:
        candidates.append(f"{base}/{parent}/index_CN.md")
        candidates.append(f"{base}/{parent}/{parent_leaf}_CN.md")

    # 目录页常见命名：/a/b -> /a/a_CN.md（或 /a/b_CN.md）
    if parent:
        candidates.append(f"{base}/{parent}/{parent_leaf}_CN.md")

    # 大小写变体，覆盖例如 OFA-Tutorial 这类路由
    rel_lower = rel.lower()
    leaf_lower = leaf.lower()
    if rel_lower != rel or leaf_lower != leaf:
        candidates.append(f"{base}/{rel_lower}/{leaf_lower}_CN.md")
        candidates.append(f"{base}/{rel_lower}_CN.md")

    # 常见路由别名：quick-started -> quick-start
    if leaf.endswith("-started"):
        leaf_alias = f"{leaf[:-2]}"
        rel_alias = "/".join(parts[:-1] + [leaf_alias])
        candidates.append(f"{base}/{rel_alias}/{leaf_alias}_CN.md")
        candidates.append(f"{base}/{rel_alias}_CN.md")

    # 去重保持顺序
    deduped: List[str] = []
    seen: Set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        deduped.append(candidate)

    return deduped


def infer_docs_url_from_docdata_md(docdata_md_url: str) -> Optional[str]:
    """将 docdata 下的 md 文件路径推断为 /docs 路由。"""
    parsed = urlparse(docdata_md_url)
    marker = "/dist/"
    if marker not in parsed.path:
        return None

    rel = parsed.path.split(marker, 1)[1].strip("/")
    if not rel.lower().endswith(".md"):
        return None

    parts = [p for p in rel.split("/") if p]
    if not parts:
        return None

    filename = parts[-1]
    stem = filename[:-3]
    if stem.endswith("_CN"):
        stem = stem[:-3]
    elif stem.endswith("_EN"):
        stem = stem[:-3]

    parent = parts[:-1]
    if not parent:
        route_parts = [stem]
    elif stem == parent[-1]:
        route_parts = parent
    else:
        route_parts = parent + [stem]

    route = "/".join(route_parts).strip("/")
    if not route:
        inferred = "https://modelscope.cn/docs"
        return inferred if is_valid_docs_origin(inferred) else None
    inferred = f"https://modelscope.cn/docs/{route}"
    return inferred if is_valid_docs_origin(inferred) else None


def docs_url_candidate_from_docdata_md(docdata_md_url: str) -> Optional[str]:
    """从任意 docdata md 路径构造一个 docs 路由候选（可能含中文段）。"""
    parsed = urlparse(docdata_md_url)
    marker = "/dist/"
    if marker not in parsed.path:
        return None

    rel = parsed.path.split(marker, 1)[1].strip("/")
    if not rel.lower().endswith(".md"):
        return None

    parts = [p for p in rel.split("/") if p]
    if not parts:
        return None

    filename = parts[-1]
    stem = filename[:-3]
    if stem.endswith("_CN"):
        stem = stem[:-3]
    elif stem.endswith("_EN"):
        stem = stem[:-3]

    parent = parts[:-1]
    if parent and stem == parent[-1]:
        route_parts = parent
    else:
        route_parts = parent + [stem]

    route = "/".join(route_parts).strip("/")
    if not route:
        return "https://modelscope.cn/docs"
    return f"https://modelscope.cn/docs/{route}"


def resolve_docs_origin_via_redirect(session: requests.Session, candidate_url: str, timeout: int) -> Optional[str]:
    try:
        resp = session.get(candidate_url, timeout=min(timeout, 8), allow_redirects=True)
    except Exception:
        return None

    if resp.status_code >= 400:
        return None

    final_url = normalize_url(resp.url)
    if is_valid_docs_origin(final_url):
        return final_url
    return None


def has_child_origin(url: str, all_origins: Set[str]) -> bool:
    base = url.rstrip("/") + "/"
    for other in all_origins:
        if other != url and other.startswith(base):
            return True
    return False


def fetch_docdata_markdown(session: requests.Session, url: str, timeout: int, version: str) -> Optional[Tuple[str, str, List[str]]]:
    for md_url in build_docdata_candidates(url, version):
        try:
            resp = session.get(md_url, timeout=timeout)
        except Exception:
            continue

        if resp.status_code != 200:
            continue

        content = resp.content.decode("utf-8", errors="replace").strip()
        if not content or len(re.sub(r"\s+", "", content)) < 80:
            continue

        # 图片相对路径统一转为绝对链接：优先 DocData URL，回退 Source URL。
        content = absolutize_markdown_image_links(content, docdata_url=md_url, source_url=url)

        title = "Untitled"
        first_h1 = re.search(r"^#\s+(.+)$", content, flags=re.MULTILINE)
        if first_h1:
            title = first_h1.group(1).strip()

        links = extract_links_from_markdown(url, content)

        # 解析 docdata 里的相对 md 链接，转成 docs 路由继续抓取
        md_targets = re.findall(r"\[[^\]]*\]\(([^)]+\.md)\)", content)
        for target in md_targets:
            target = target.strip()
            if not target:
                continue
            if target.startswith(("http://", "https://")):
                resolved = target
            else:
                resolved = urljoin(md_url, target)
            inferred = infer_docs_url_from_docdata_md(resolved)
            if inferred:
                links.append(normalize_url(inferred))
                continue

            candidate = docs_url_candidate_from_docdata_md(resolved)
            if candidate:
                redirected = resolve_docs_origin_via_redirect(session, candidate, timeout)
                if redirected:
                    links.append(normalize_url(redirected))

        # 去重保持顺序
        deduped_links: List[str] = []
        seen_links: Set[str] = set()
        for link in links:
            if link in seen_links:
                continue
            seen_links.add(link)
            deduped_links.append(link)

        doc = (
            f"> Source URL: {url}\n"
            f"> Title: {title}\n"
            f"> Data Type: doc\n"
            f"> Source Group: docs_docdata\n"
            f"> Crawled By: docs_docdata\n"
            f"> DocData URL: {md_url}\n"
            f"> Crawled At: {now_iso()}\n\n"
            f"{content}\n"
        )
        return title, doc, deduped_links

    return None


def discover_docs_origins(
    session: requests.Session,
    seeds: List[str],
    timeout: int,
    max_depth: int,
    max_pages: int,
    docdata_version: str,
    reader_timeout: int = 8,
    all_discovered_links: Optional[Set[str]] = None,
    raw_discovered_links: Optional[Set[str]] = None,
) -> List[str]:
    """第一阶段：发现 docs 原始页面 URL（/docs/*）。"""
    allowed_domains = {"modelscope.cn", "www.modelscope.cn"}
    include_prefixes = ["/docs"]

    queue = deque((normalize_url(seed), 0) for seed in seeds)
    visited: Set[str] = set()
    origins: List[str] = []
    origin_set: Set[str] = set()

    while queue and len(origins) < max_pages:
        current_url, depth = queue.popleft()
        if current_url in visited:
            continue
        visited.add(current_url)

        if not allowed_url(current_url, allowed_domains, include_prefixes):
            continue

        if current_url not in origin_set:
            origin_set.add(current_url)
            origins.append(current_url)

        if depth >= max_depth:
            continue

        discovered_links: List[str] = []

        # reader 导航抽取：用于补齐 docdata 中未显式给出的 docs 路由
        try:
            reader_result = fetch_reader_markdown(session, current_url, min(timeout, reader_timeout))
            if reader_result is not None:
                _, _, reader_links = reader_result
                discovered_links.extend(reader_links)
        except BaseException:
            pass

        # docs 原网址发现以 docdata 链接图为主
        docdata_result = fetch_docdata_markdown(session, current_url, timeout, docdata_version)
        if docdata_result is not None:
            _, _, md_links = docdata_result
            if md_links:
                discovered_links.extend(md_links)
        else:
            # 极少数页面未命中 docdata 时，再回退到静态 HTML 链接
            try:
                resp = session.get(current_url, timeout=timeout)
                if resp.status_code < 400:
                    discovered_links.extend(extract_links(current_url, resp.text))
            except Exception:
                pass

        for link in discovered_links:
            normalized_link = normalize_discovered_docs_link(session, link, timeout)
            if normalized_link is None:
                continue
            if not allowed_url(normalized_link, allowed_domains, include_prefixes):
                continue

            if raw_discovered_links is not None:
                # raw_discovered_links 也只保留有效 docs 路由，避免索引污染
                raw_discovered_links.add(normalized_link)

            if all_discovered_links is not None:
                all_discovered_links.add(normalized_link)
            if normalized_link not in visited:
                queue.append((normalized_link, depth + 1))

        time.sleep(0.05)

    return origins


def save_docs_discovery_report(
    reports_root: Path,
    origins: List[str],
    mapped: List[str],
    failed: List[str],
    version: str,
    discovered_links: List[str],
    raw_discovered_links: List[str],
    title_mapping_origins: List[str],
) -> None:
    report = {
        "updated_at": now_iso(),
        "docdata_version": version,
        "title_mapping_origins_count": len(title_mapping_origins),
        "raw_discovered_links_count": len(raw_discovered_links),
        "discovered_links_count": len(discovered_links),
        "total_origins": len(origins),
        "mapped_count": len(mapped),
        "failed_count": len(failed),
        "title_mapping_origins": title_mapping_origins,
        "raw_discovered_links": raw_discovered_links,
        "discovered_links": discovered_links,
        "origins": origins,
        "mapped_origins": mapped,
        "failed_origins": failed,
    }
    ensure_dir(reports_root)
    report_path = reports_root / "docs_links_index.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def save_docs_mapping_report(reports_root: Path, mappings: List[Dict]) -> None:
    payload = {
        "updated_at": now_iso(),
        "count": len(mappings),
        "items": mappings,
    }
    ensure_dir(reports_root)
    (reports_root / "docs_url_to_md_map.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_docs_fetch_report(reports_root: Path, rows: List[Dict]) -> None:
    payload = {
        "updated_at": now_iso(),
        "count": len(rows),
        "items": rows,
    }
    ensure_dir(reports_root)
    (reports_root / "docs_fetch_report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    def fetch_reader_links(session: requests.Session, url: str, timeout: int) -> List[str]:
        """用于链接发现：提取 reader 的完整 Markdown 链接，不做正文清洗。"""
        reader_url = f"https://r.jina.ai/http://{url}"
        try:
            resp = session.get(reader_url, timeout=timeout)
        except Exception:
            return []

        if resp.status_code >= 400:
            return []

        text = resp.text
        md_match = re.search(r"Markdown Content:\s*(.*)$", text, flags=re.DOTALL)
        if not md_match:
            return []

        content = md_match.group(1).strip()
        if not content:
            return []

        return extract_links_from_markdown(url, content)


def fetch_reader_markdown(session: requests.Session, url: str, timeout: int) -> Optional[Tuple[str, str, List[str]]]:
    reader_url = f"https://r.jina.ai/http://{url}"
    try:
        resp = session.get(reader_url, timeout=timeout)
    except Exception:
        return None

    if resp.status_code >= 400:
        return None

    text = resp.text
    title_match = re.search(r"^Title:\s*(.*)$", text, flags=re.MULTILINE)
    md_match = re.search(r"Markdown Content:\s*(.*)$", text, flags=re.DOTALL)
    if not md_match:
        return None

    title = (title_match.group(1).strip() if title_match else "Untitled") or "Untitled"
    content = md_match.group(1).strip()
    content = clean_reader_content(content)
    if not content:
        return None

    discovered_links = extract_links_from_markdown(url, content)

    doc = (
        f"> Source URL: {url}\n"
        f"> Title: {title}\n"
        f"> Data Type: doc\n"
        f"> Source Group: reader_fallback\n"
        f"> Crawled By: reader_fallback\n"
        f"> Crawled At: {now_iso()}\n\n"
        f"# {title}\n\n"
        f"{content}\n"
    )
    return title, doc, discovered_links


def fetch_page(session: requests.Session, url: str, page_state: Optional[Dict], timeout: int) -> Tuple[Optional[requests.Response], str]:
    headers: Dict[str, str] = {}
    if page_state:
        if page_state.get("etag"):
            headers["If-None-Match"] = page_state["etag"]
        if page_state.get("last_modified"):
            headers["If-Modified-Since"] = page_state["last_modified"]

    try:
        response = session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    except Exception as exc:
        return None, f"request_error: {exc}"

    if response.status_code == 304:
        return response, "not_modified"
    if response.status_code >= 400:
        return None, f"http_{response.status_code}"

    content_type = response.headers.get("Content-Type", "")
    if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
        return None, f"skip_content_type: {content_type}"

    return response, "ok"


def extract_links(base_url: str, html_text: str) -> List[str]:
    soup = BeautifulSoup(html_text, "html.parser")
    links: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href:
            continue
        links.append(normalize_url(urljoin(base_url, href)))
    return links


def crawl_web_source(
    source: Dict,
    output_root: Path,
    reports_root: Path,
    state: Dict,
    timeout: int,
    max_depth: int,
    max_pages: int,
) -> Dict[str, int]:
    stats = {"fetched": 0, "updated": 0, "skipped": 0, "errors": 0}

    session = requests.Session()
    session.headers.update({
        "User-Agent": "ModelScopeCrawler/1.0 (+https://github.com/modelscope)",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    docs_docdata_version = os.getenv("MODELSCOPE_DOCS_DOCDATA_VERSION", DEFAULT_DOCS_DOCDATA_VERSION)

    ensure_dir(output_root / source["name"])

    if source.get("name") == "docs":
        # 0) 主发现源：title-mapping.json
        title_mapping_origins = fetch_title_mapping_origins(docs_docdata_version, timeout)

        # 第一阶段：先发现 docs 原网址
        discovered_links_set: Set[str] = set()
        raw_discovered_links_set: Set[str] = set()
        discovered_origins = discover_docs_origins(
            session=session,
            seeds=source["seeds"],
            timeout=timeout,
            max_depth=max_depth,
            max_pages=max_pages,
            docdata_version=docs_docdata_version,
            all_discovered_links=discovered_links_set,
            raw_discovered_links=raw_discovered_links_set,
        )

        # 合并主发现源 + 补充发现源，优先使用 title-mapping
        docs_origins: List[str] = []
        seen_origins: Set[str] = set()
        for u in title_mapping_origins + discovered_origins:
            if not is_valid_docs_origin(u):
                continue
            if u in seen_origins:
                continue
            seen_origins.add(u)
            docs_origins.append(u)

        mapped_origins: List[str] = []
        failed_origins: List[str] = []
        skipped_origins: List[str] = []
        mapping_rows: List[Dict] = []
        fetch_rows: List[Dict] = []
        all_origins_set = set(docs_origins)
        title_mapping_set = set(title_mapping_origins)
        discovered_origins_set = set(discovered_origins)

        # 第二阶段：逐个 origin 映射并抓取 docdata markdown（只抓 md 源）
        for current_url in docs_origins:
            direct_md = fetch_docdata_markdown(session, current_url, timeout, docs_docdata_version)
            if direct_md is None:
                # 目录节点通常用于导航而非正文页面，缺失 docdata 时按跳过处理。
                if has_child_origin(current_url, all_origins_set):
                    stats["skipped"] += 1
                    skipped_origins.append(current_url)
                    fetch_rows.append(
                        {
                            "docs_url": current_url,
                            "status": "skipped",
                            "reason": "index_node_no_docdata",
                            "updated_at": now_iso(),
                        }
                    )
                # title-mapping 中可能存在未发布/已下线路由，避免将其算作真实错误。
                elif current_url in title_mapping_set and current_url not in discovered_origins_set:
                    stats["skipped"] += 1
                    skipped_origins.append(current_url)
                    fetch_rows.append(
                        {
                            "docs_url": current_url,
                            "status": "skipped",
                            "reason": "title_mapping_orphan",
                            "updated_at": now_iso(),
                        }
                    )
                elif current_url not in title_mapping_set:
                    stats["skipped"] += 1
                    skipped_origins.append(current_url)
                    fetch_rows.append(
                        {
                            "docs_url": current_url,
                            "status": "skipped",
                            "reason": "discovered_unmapped",
                            "updated_at": now_iso(),
                        }
                    )
                else:
                    stats["errors"] += 1
                    failed_origins.append(current_url)
                    fetch_rows.append(
                        {
                            "docs_url": current_url,
                            "status": "failed",
                            "reason": "docdata_not_found",
                            "updated_at": now_iso(),
                        }
                    )
                continue

            title, markdown, _ = direct_md
            digest = sha256_text(markdown)
            out_path = docs_output_path_for_url(output_root, current_url)
            page_state = state["pages"].get(current_url)
            previous_digest = page_state.get("hash") if page_state else None

            docdata_url = ""
            for line in markdown.splitlines():
                if line.startswith("> DocData URL: "):
                    docdata_url = line.replace("> DocData URL: ", "", 1).strip()
                    break

            if previous_digest != digest:
                ensure_dir(out_path.parent)
                out_path.write_text(markdown, encoding="utf-8")
                stats["updated"] += 1

            state["pages"][current_url] = {
                "hash": digest,
                "file": str(out_path).replace("\\", "/"),
                "etag": None,
                "last_modified": None,
                "last_crawled": now_iso(),
                "source": source["name"],
            }
            stats["fetched"] += 1
            mapped_origins.append(current_url)
            mapping_rows.append(
                {
                    "docs_url": current_url,
                    "docdata_url": docdata_url,
                    "local_file": str(out_path).replace("\\", "/"),
                    "status": "mapped",
                    "updated_at": now_iso(),
                }
            )
            fetch_rows.append(
                {
                    "docs_url": current_url,
                    "docdata_url": docdata_url,
                    "status": "fetched",
                    "reason": "ok",
                    "updated_at": now_iso(),
                }
            )

            if stats["fetched"] >= max_pages:
                break

            time.sleep(0.05)

        save_docs_discovery_report(
            reports_root=reports_root,
            origins=docs_origins,
            mapped=mapped_origins,
            failed=failed_origins,
            version=docs_docdata_version,
            discovered_links=sorted(discovered_links_set),
            raw_discovered_links=sorted(raw_discovered_links_set),
            title_mapping_origins=title_mapping_origins,
        )
        save_docs_mapping_report(reports_root, mapping_rows)
        save_docs_fetch_report(reports_root, fetch_rows)

        return stats

    queue = deque((normalize_url(seed), 0) for seed in source["seeds"])
    visited: Set[str] = set()

    while queue and stats["fetched"] < max_pages:
        current_url, depth = queue.popleft()
        if current_url in visited:
            continue
        visited.add(current_url)

        if not allowed_url(current_url, source["allowed_domains"], source["include_prefixes"]):
            stats["skipped"] += 1
            continue

        # docs 优先尝试官方 docdata markdown，质量通常优于动态页面渲染抓取
        if source.get("name") == "docs":
            direct_md = fetch_docdata_markdown(session, current_url, timeout, docs_docdata_version)
            if direct_md is not None:
                title, markdown, discovered_links = direct_md
                digest = sha256_text(markdown)
                out_path = file_path_for_url(output_root, source["name"], current_url)
                page_state = state["pages"].get(current_url)
                previous_digest = page_state.get("hash") if page_state else None

                if previous_digest != digest:
                    ensure_dir(out_path.parent)
                    out_path.write_text(markdown, encoding="utf-8")
                    stats["updated"] += 1

                state["pages"][current_url] = {
                    "hash": digest,
                    "file": str(out_path).replace("\\", "/"),
                    "etag": None,
                    "last_modified": None,
                    "last_crawled": now_iso(),
                    "source": source["name"],
                }
                stats["fetched"] += 1

                if depth < max_depth:
                    for link in discovered_links:
                        if link not in visited:
                            queue.append((link, depth + 1))

                time.sleep(0.1)
                continue

        page_state = state["pages"].get(current_url)
        response, result = fetch_page(session, current_url, page_state, timeout)

        if result == "not_modified":
            if page_state:
                page_state["last_crawled"] = now_iso()
            stats["fetched"] += 1
            continue

        if result != "ok" or response is None:
            stats["errors"] += 1
            continue

        final_url = normalize_url(response.url)
        if final_url != current_url and final_url not in visited:
            current_url = final_url

        html_text = response.text
        soup = BeautifulSoup(html_text, "html.parser")
        title = (soup.title.string or "Untitled").strip() if soup.title else "Untitled"

        markdown = render_markdown(current_url, source["name"], title, html_text)
        discovered_links = extract_links(current_url, html_text)

        # docs 等 SPA 页面可能返回空壳 HTML，正文过短时使用 reader 兜底
        if is_markdown_thin(markdown):
            reader_result = fetch_reader_markdown(session, current_url, timeout)
            if reader_result is not None:
                title, markdown, reader_links = reader_result
                if reader_links:
                    discovered_links.extend(reader_links)

        digest = sha256_text(markdown)
        out_path = file_path_for_url(output_root, source["name"], current_url)

        previous_digest = page_state.get("hash") if page_state else None
        if previous_digest != digest:
            ensure_dir(out_path.parent)
            out_path.write_text(markdown, encoding="utf-8")
            stats["updated"] += 1

        state["pages"][current_url] = {
            "hash": digest,
            "file": str(out_path).replace("\\", "/"),
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
            "last_crawled": now_iso(),
            "source": source["name"],
        }

        stats["fetched"] += 1

        if depth < max_depth:
            for link in discovered_links:
                if link not in visited:
                    queue.append((link, depth + 1))

        time.sleep(0.2)

    return stats


def github_headers() -> Dict[str, str]:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ModelScopeCrawler/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_get_json(session: requests.Session, url: str, timeout: int) -> Optional[Dict]:
    try:
        resp = session.get(url, timeout=timeout)
        if resp.status_code >= 400:
            return None
        return resp.json()
    except Exception:
        return None


def fetch_github_markdown(session: requests.Session, raw_url: str, timeout: int) -> Optional[str]:
    try:
        resp = session.get(raw_url, timeout=timeout)
        if resp.status_code >= 400:
            return None
        return resp.text
    except Exception:
        return None


def crawl_github_org_source(source: Dict, output_root: Path, state: Dict, timeout: int, max_repos: int) -> Dict[str, int]:
    stats = {"fetched": 0, "updated": 0, "skipped": 0, "errors": 0}
    org = source["org"]
    base_dir = output_root / source["name"]
    ensure_dir(base_dir)

    session = requests.Session()
    session.headers.update(github_headers())

    repos_url = f"https://api.github.com/orgs/{org}/repos?per_page={max_repos}&sort=updated"
    repos = github_get_json(session, repos_url, timeout)
    if not repos:
        stats["errors"] += 1
        return stats

    for repo in repos[:max_repos]:
        repo_name = repo.get("name")
        default_branch = repo.get("default_branch", "main")
        if not repo_name:
            continue

        tree_url = f"https://api.github.com/repos/{org}/{repo_name}/git/trees/{default_branch}?recursive=1"
        tree = github_get_json(session, tree_url, timeout)
        if not tree or "tree" not in tree:
            stats["errors"] += 1
            continue

        md_paths = []
        for item in tree["tree"]:
            path = item.get("path", "")
            item_type = item.get("type", "")
            if item_type != "blob":
                continue
            low = path.lower()
            if not low.endswith(".md"):
                continue
            if low.startswith("docs/") or low.startswith("doc/") or low.startswith("readme"):
                md_paths.append(path)

        for md_path in md_paths[:200]:
            file_url = f"https://raw.githubusercontent.com/{org}/{repo_name}/{default_branch}/{md_path}"
            page_key = normalize_url(file_url)
            content = fetch_github_markdown(session, file_url, timeout)
            if content is None:
                stats["errors"] += 1
                continue

            title = f"{org}/{repo_name} - {md_path}"
            markdown = (
                f"> Source URL: {file_url}\n"
                f"> Title: {title}\n"
                f"> Data Type: doc\n"
                f"> Source Group: {source['name']}\n"
                f"> Crawled At: {now_iso()}\n\n"
                f"# {title}\n\n"
                f"{content.strip()}\n"
            )

            digest = sha256_text(markdown)
            out_file = base_dir / f"{slugify(org + '-' + repo_name + '-' + md_path)}.md"
            prev = state["pages"].get(page_key)
            prev_hash = prev.get("hash") if prev else None

            if prev_hash != digest:
                out_file.write_text(markdown, encoding="utf-8")
                stats["updated"] += 1

            state["pages"][page_key] = {
                "hash": digest,
                "file": str(out_file).replace("\\", "/"),
                "last_crawled": now_iso(),
                "source": source["name"],
            }
            stats["fetched"] += 1

    return stats


def run_once(args: argparse.Namespace) -> Dict[str, Dict[str, int]]:
    output_root = Path(args.output_dir)
    ensure_dir(output_root)
    reports_root = Path(args.reports_dir)
    ensure_dir(reports_root)
    state_file = Path(args.state_file)
    ensure_dir(state_file.parent)

    state = load_state(state_file)
    source_stats: Dict[str, Dict[str, int]] = {}

    selected = {s.strip() for s in args.sources.split(",") if s.strip()} if args.sources else set()

    for source in SOURCES:
        if selected and source["name"] not in selected:
            continue
        print(f"\n=== Crawling source: {source['name']} ===")
        if source["type"] == "web":
            stats = crawl_web_source(
                source=source,
                output_root=output_root,
                reports_root=reports_root,
                state=state,
                timeout=args.timeout,
                max_depth=args.max_depth,
                max_pages=args.max_pages_per_source,
            )
        else:
            stats = crawl_github_org_source(
                source=source,
                output_root=output_root,
                state=state,
                timeout=args.timeout,
                max_repos=args.github_max_repos,
            )

        source_stats[source["name"]] = stats
        print(f"fetched={stats['fetched']} updated={stats['updated']} skipped={stats['skipped']} errors={stats['errors']}")

    save_state(state_file, state)
    return source_stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl ModelScope and GitHub docs into markdown with incremental updates")
    parser.add_argument("--output-dir", default="data/raw", help="Markdown output root directory")
    parser.add_argument("--reports-dir", default="data", help="Report output directory")
    parser.add_argument("--state-file", default="data/crawl_state.json", help="Crawler state json path")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    parser.add_argument("--max-depth", type=int, default=2, help="Max link depth for web sources")
    parser.add_argument("--max-pages-per-source", type=int, default=120, help="Max pages per web source per round")
    parser.add_argument("--github-max-repos", type=int, default=40, help="Max GitHub repos to inspect per round")
    parser.add_argument("--sources", default="docs", help="Comma-separated source names, default: docs")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval-minutes", type=int, default=180, help="Loop interval in minutes")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.loop:
        run_once(args)
        return

    while True:
        started = now_iso()
        print(f"\n[{started}] Starting crawler round...")
        run_once(args)
        print(f"Round finished. Sleeping {args.interval_minutes} minutes.")
        time.sleep(max(1, args.interval_minutes) * 60)


if __name__ == "__main__":
    main()
