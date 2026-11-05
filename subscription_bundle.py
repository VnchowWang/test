from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_GIST_BYTES = 32 * 1024 * 1024
PROXIES_FILE = "9929-proxies.yaml"
CLASH_FILE = "9929-flclash.yaml"
STATUS_FILE = "update-status.json"
GROUP_NAMES = ("9929 手动选择", "9929 自动测速", "9929 故障转移")
GIST_API = "https://api.github.com/gists"


class BundleError(Exception):
    """Only a fixed, credential-free code may cross the logging boundary."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class HTTPSRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme != "https":
            raise BundleError("insecure_redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def encode_yaml(value: dict) -> str:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False)


def load_selectors(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise BundleError("invalid_selectors") from None
    if not isinstance(data, dict) or data.get("version") != 1:
        raise BundleError("invalid_selectors")
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise BundleError("invalid_selectors")
    seen_ids, seen_sources, seen_output_names, seen_env = set(), set(), set(), set()
    count = 0
    for source in sources:
        if not isinstance(source, dict):
            raise BundleError("invalid_selectors")
        identifier, name, variable, nodes = (
            source.get("id"), source.get("name"), source.get("url_env"), source.get("nodes")
        )
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", identifier):
            raise BundleError("invalid_selectors")
        if not isinstance(name, str) or not name or name in seen_sources:
            raise BundleError("invalid_selectors")
        if not isinstance(variable, str) or not re.fullmatch(r"SOURCE_[A-Z0-9_]+", variable):
            raise BundleError("invalid_selectors")
        if identifier in seen_ids or variable in seen_env:
            raise BundleError("invalid_selectors")
        if not isinstance(nodes, list) or not nodes or any(not isinstance(n, str) or not n for n in nodes):
            raise BundleError("invalid_selectors")
        if len(nodes) != len(set(nodes)):
            raise BundleError("invalid_selectors")
        seen_ids.add(identifier)
        seen_sources.add(name)
        seen_env.add(variable)
        for node in nodes:
            output_name = f"{name} :: {node}"
            if output_name in seen_output_names or output_name in GROUP_NAMES:
                raise BundleError("invalid_selectors")
            seen_output_names.add(output_name)
        count += len(nodes)
    if data.get("expected_total") != count:
        raise BundleError("invalid_selectors")
    return data


def _read_response(response, limit: int) -> bytes:
    payload = response.read(limit + 1)
    if len(payload) > limit:
        raise BundleError("response_too_large")
    return payload


def fetch_subscription(url: str, timeout: float = 40) -> bytes:
    try:
        parts = urllib.parse.urlsplit(url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise BundleError("invalid_source_url")
        request = urllib.request.Request(
            url, headers={"User-Agent": "Clash.Meta/9929-subscription-bundle", "Accept": "application/yaml,text/yaml,*/*"}
        )
        opener = urllib.request.build_opener(HTTPSRedirectHandler())
        with opener.open(request, timeout=timeout) as response:
            return _read_response(response, MAX_SOURCE_BYTES)
    except BundleError:
        raise
    except urllib.error.HTTPError as error:
        raise BundleError(f"source_http_{error.code}") from None
    except Exception:
        # urllib exceptions can contain secret subscription URLs. Never preserve their text.
        raise BundleError("source_fetch_failed") from None


def parse_subscription(payload: bytes) -> list[dict]:
    if len(payload) > MAX_SOURCE_BYTES:
        raise BundleError("response_too_large")
    try:
        # Never log parser errors: a YAML exception can quote a password-bearing line.
        document = yaml.safe_load(payload.decode("utf-8-sig"))
    except Exception:
        raise BundleError("invalid_source_yaml") from None
    if not isinstance(document, dict) or not isinstance(document.get("proxies"), list):
        raise BundleError("missing_proxies_list")
    proxies = document["proxies"]
    if any(not isinstance(proxy, dict) or not isinstance(proxy.get("name"), str) for proxy in proxies):
        raise BundleError("invalid_proxy_entry")
    return proxies


def select_proxies(spec: dict, proxies: list[dict]) -> tuple[list[dict], dict]:
    report = {"source": spec["name"], "expected": len(spec["nodes"]), "matched": 0,
              "missing": [], "ambiguous": [], "invalid": [], "errors": []}
    indexed: dict[str, list[dict]] = {}
    for proxy in proxies:
        indexed.setdefault(proxy["name"], []).append(proxy)
    selected = []
    names = {proxy["name"]: f'{spec["name"]} :: {proxy["name"]}'
             for proxy in proxies if proxy["name"] in spec["nodes"]}
    for original_name in spec["nodes"]:
        matches = indexed.get(original_name, [])
        if not matches:
            report["missing"].append(original_name)
            continue
        if len(matches) != 1:
            report["ambiguous"].append(original_name)
            continue
        proxy = copy.deepcopy(matches[0])
        if (not isinstance(proxy.get("type"), str) or not proxy["type"]
                or not isinstance(proxy.get("server"), str) or not proxy["server"]
                or type(proxy.get("port")) is not int or not 1 <= proxy["port"] <= 65535):
            report["invalid"].append(original_name)
            continue
        # Preserve every protocol option. Only the display name and an explicitly
        # selected dialer-proxy reference are adjusted to avoid collisions.
        if "dialer-proxy" in proxy:
            dependency = proxy["dialer-proxy"]
            if not isinstance(dependency, str):
                report["invalid"].append(original_name)
                continue
            if dependency in names:
                proxy["dialer-proxy"] = names[dependency]
            elif dependency not in ("DIRECT", "REJECT"):
                report["invalid"].append(original_name)
                continue
        proxy["name"] = names[original_name]
        selected.append(proxy)
        report["matched"] += 1
    return selected, report


def build_config(proxies: list[dict]) -> dict:
    names = [proxy["name"] for proxy in proxies]
    return {
        "mixed-port": 7890,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "warning",
        "ipv6": False,
        "proxies": copy.deepcopy(proxies),
        "proxy-groups": [
            {"name": GROUP_NAMES[0], "type": "select", "proxies": [GROUP_NAMES[1], GROUP_NAMES[2], *names]},
            {"name": GROUP_NAMES[1], "type": "url-test", "proxies": names,
             "url": "https://www.gstatic.com/generate_204", "interval": 600, "tolerance": 100, "lazy": True},
            {"name": GROUP_NAMES[2], "type": "fallback", "proxies": names,
             "url": "https://www.gstatic.com/generate_204", "interval": 600, "lazy": True},
        ],
        "rules": [f"MATCH,{GROUP_NAMES[0]}"],
    }


def build_bundle(selectors: dict, environ=None, fetcher=None) -> tuple[dict | None, dict]:
    environ = os.environ if environ is None else environ
    fetcher = fetch_subscription if fetcher is None else fetcher
    status = {"schema_version": 1, "attempted_at": utc_now(), "result": "blocked",
              "expected_total": selectors["expected_total"], "matched_total": 0,
              "retained_previous": True, "published": False, "sources": []}
    all_selected = []
    for source in selectors["sources"]:
        report = {"source": source["name"], "expected": len(source["nodes"]), "matched": 0,
                  "missing": [], "ambiguous": [], "invalid": [], "errors": []}
        url = environ.get(source["url_env"], "").strip()
        if not url:
            report["errors"].append("missing_source_secret")
            status["sources"].append(report)
            continue
        try:
            proxies = parse_subscription(fetcher(url))
            selected, report = select_proxies(source, proxies)
            all_selected.extend(selected)
        except BundleError as error:
            report["errors"].append(error.code)
        except Exception:
            report["errors"].append("source_processing_failed")
        status["sources"].append(report)
    status["matched_total"] = sum(source["matched"] for source in status["sources"])
    complete = status["matched_total"] == selectors["expected_total"] and all(
        not (source["errors"] or source["missing"] or source["ambiguous"] or source["invalid"])
        for source in status["sources"]
    )
    if not complete:
        return None, status
    # Ensure all string values round-trip safely before any output or publication.
    try:
        files = {PROXIES_FILE: encode_yaml({"proxies": all_selected}),
                 CLASH_FILE: encode_yaml(build_config(all_selected))}
        for content in files.values():
            yaml.safe_load(content)
    except Exception:
        status["errors"] = ["serialization_failed"]
        return None, status
    status["result"] = "ready"
    return files, status


def gist_request(method: str, path: str, token: str, body=None):
    if not token or "\n" in token or "\r" in token:
        raise BundleError("missing_or_invalid_gist_token")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "9929-subscription-bundle"}
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(GIST_API + path, data=data, headers=headers, method=method)
    try:
        # Deliberately do not follow redirects with an Authorization header.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        opener = urllib.request.build_opener(NoRedirect())
        with opener.open(request, timeout=45) as response:
            payload = _read_response(response, MAX_GIST_BYTES)
        result = json.loads(payload)
        if not isinstance(result, dict):
            raise BundleError("invalid_gist_response")
        return result
    except BundleError:
        raise
    except urllib.error.HTTPError as error:
        raise BundleError(f"gist_http_{error.code}") from None
    except Exception:
        raise BundleError("gist_request_failed") from None


def verify_secret_gist(gist: dict, expected_id=None) -> None:
    if gist.get("public") is not False:
        raise BundleError("gist_must_be_secret")
    if expected_id is not None and gist.get("id") != expected_id:
        raise BundleError("unexpected_gist_id")
    owner = gist.get("owner", {}).get("login")
    if not isinstance(owner, str) or not re.fullmatch(r"[A-Za-z0-9-]+", owner):
        raise BundleError("invalid_gist_owner")


def publish_gist(files: dict, status: dict, token: str, gist_id: str | None, initialize=False, requester=None) -> dict:
    requester = gist_request if requester is None else requester
    if initialize:
        if gist_id:
            raise BundleError("initialize_requires_no_gist_id")
    else:
        if not gist_id or not re.fullmatch(r"[0-9a-fA-F]{20,64}", gist_id):
            raise BundleError("missing_or_invalid_gist_id")
        existing = requester("GET", f"/{gist_id}", token)
        verify_secret_gist(existing, gist_id)
    new_status = copy.deepcopy(status)
    new_status.update(result="published", published=True, retained_previous=False, publication_outcome="confirmed")
    payload = {"files": {name: {"content": content} for name, content in files.items()}}
    payload["files"][STATUS_FILE] = {"content": json.dumps(new_status, ensure_ascii=False, indent=2) + "\n"}
    if initialize:
        payload.update(public=False, description="AS9929 selected subscription (contains credentials; keep links private)")
    # A network failure after sending PATCH/POST cannot prove whether GitHub
    # committed it. Either version is complete; report this uncertainty honestly.
    status.update(publication_outcome="unknown", retained_previous=None)
    result = requester("POST" if initialize else "PATCH", "" if initialize else f"/{gist_id}", token, payload)
    verify_secret_gist(result, None if initialize else gist_id)
    identifier = result.get("id")
    if not isinstance(identifier, str) or not re.fullmatch(r"[0-9a-fA-F]{20,64}", identifier):
        raise BundleError("invalid_gist_response")
    owner = result["owner"]["login"]
    # GitHub response raw_url includes a commit revision, which would freeze updates.
    # These revision-free links always resolve the newest content of the same file.
    links = {"gist_id": identifier,
             "flclash_url": f"https://gist.githubusercontent.com/{owner}/{identifier}/raw/{CLASH_FILE}",
             "proxies_url": f"https://gist.githubusercontent.com/{owner}/{identifier}/raw/{PROXIES_FILE}"}
    status.update(new_status)
    return links


def run(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build 27 exact AS9929 selections; never print source URLs or node credentials.")
    parser.add_argument("command", choices=("build", "publish", "init-gist"))
    parser.add_argument("--selectors", type=Path, default=Path(__file__).with_name("selectors.json"))
    parser.add_argument("--output-dir", type=Path, default=Path(".private"))
    args = parser.parse_args(argv)
    status = {"schema_version": 1, "attempted_at": utc_now(), "result": "blocked", "published": False,
              "retained_previous": True, "errors": []}
    try:
        selectors = load_selectors(args.selectors)
        files, status = build_bundle(selectors)
        if files is None:
            atomic_write(args.output_dir / STATUS_FILE, json.dumps(status, ensure_ascii=False, indent=2) + "\n")
            print(f"Update blocked: {status['matched_total']}/{status['expected_total']} exact selections; previous subscription retained. See sanitized update-status.json.")
            return 1
        if args.command != "build":
            links = publish_gist(files, status, os.environ.get("GIST_TOKEN", ""),
                                 os.environ.get("GIST_ID") or None, initialize=args.command == "init-gist")
            atomic_write(args.output_dir / "subscription-links.json", json.dumps(links, indent=2) + "\n")
        # Do not overwrite either local credential-bearing output before all source
        # validation and (if requested) the remote update have succeeded.
        for filename, content in files.items():
            atomic_write(args.output_dir / filename, content)
        if args.command == "build":
            status.update(result="built", retained_previous=False)
        atomic_write(args.output_dir / STATUS_FILE, json.dumps(status, ensure_ascii=False, indent=2) + "\n")
        print(f"Update {status['result']}: {status['matched_total']}/{status['expected_total']} exact selections. Private files saved; no credentials or subscription links printed.")
        return 0
    except BundleError as error:
        status["result"] = "blocked"
        status.setdefault("errors", []).append(error.code)
        atomic_write(args.output_dir / STATUS_FILE, json.dumps(status, ensure_ascii=False, indent=2) + "\n")
        print(f"Update blocked ({error.code}); inspect sanitized update-status.json.")
        return 1
    except Exception:
        # This last boundary also suppresses secrets in filesystem/network/parser exceptions.
        status["result"] = "blocked"
        status.setdefault("errors", []).append("unexpected_error")
        try:
            atomic_write(args.output_dir / STATUS_FILE, json.dumps(status, ensure_ascii=False, indent=2) + "\n")
        except Exception:
            pass  # A read-only/full disk must not turn into a credential-bearing traceback.
        print("Update failed (unexpected_error); no exception details emitted.")
        return 1


if __name__ == "__main__":
    sys.exit(run())
