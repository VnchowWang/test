from __future__ import annotations

import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

import subscription_bundle as bundle

ROOT = Path(__file__).resolve().parents[1]
GIST_ID = "a" * 32
OWNER = "test-owner"
TOKEN = "fake-gist-token-for-unit-tests"
SECRET_MARKER = "never-emit-this-source-secret"


def fixtures():
    selectors = bundle.load_selectors(ROOT / "selectors.json")
    environ, payloads, originals = {}, {}, {}
    for index, spec in enumerate(selectors["sources"]):
        url = f"https://provider-{index}.example.invalid/subscription?token={SECRET_MARKER}"
        environ[spec["url_env"]] = url
        proxies = []
        for number, name in enumerate(spec["nodes"]):
            proxy = {
                "name": name, "type": ("ss", "trojan", "anytls", "vless")[index],
                "server": f"rotated-{number}.example.invalid", "port": 10000 + number,
                "password": f"fake-node-password-{index}-{number}", "udp": True,
                "client-fingerprint": "chrome", "skip-cert-verify": False,
                "reality-opts": {"public-key": "fake-public-key", "short-id": "abcd"},
                "ws-opts": {"path": "/credential-sensitive-path", "headers": {"Host": "edge.example.invalid"}},
                "alpn": ["h2", "http/1.1"], "unknown-future-option": {"nested": [1, False, "kept"]},
            }
            proxies.append(proxy)
        originals[spec["id"]] = proxies
        # An attractive extra candidate must never enter the result.
        extras = [{"name": "unselected replacement", "type": "ss", "server": "unselected.example.invalid",
                   "port": 443, "password": "fake-extra-password"}]
        payloads[url] = yaml.safe_dump({"proxies": proxies + extras}, allow_unicode=True).encode("utf-8")
    return selectors, environ, payloads, originals


def gist(private=True):
    return {"id": GIST_ID, "public": not private, "owner": {"login": OWNER}}


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.selectors, self.environ, self.payloads, self.originals = fixtures()

    def build(self):
        return bundle.build_bundle(self.selectors, self.environ, self.payloads.__getitem__)

    def test_exact_27_and_all_four_sources(self):
        self.assertEqual([len(s["nodes"]) for s in self.selectors["sources"]], [14, 8, 3, 2])
        files, status = self.build()
        proxies = yaml.safe_load(files[bundle.PROXIES_FILE])["proxies"]
        self.assertEqual(len(proxies), 27)
        self.assertEqual(status["matched_total"], 27)
        self.assertEqual(status["result"], "ready")
        self.assertTrue(all("unselected replacement" not in p["name"] for p in proxies))

    def test_every_protocol_field_and_new_server_preserved(self):
        files, _ = self.build()
        output = yaml.safe_load(files[bundle.PROXIES_FILE])["proxies"]
        expected = []
        for source in self.selectors["sources"]:
            for original in self.originals[source["id"]]:
                node = copy.deepcopy(original)
                node["name"] = f'{source["name"]} :: {original["name"]}'
                expected.append(node)
        self.assertEqual(output, expected)
        self.assertTrue(output[0]["server"].startswith("rotated-"))

    def test_renamed_node_is_missing_without_replacement(self):
        source = self.selectors["sources"][0]
        url = self.environ[source["url_env"]]
        content = yaml.safe_load(self.payloads[url])
        content["proxies"][0]["name"] += " renamed"
        self.payloads[url] = yaml.safe_dump(content).encode()
        files, status = self.build()
        self.assertIsNone(files)
        self.assertEqual(status["matched_total"], 26)
        self.assertEqual(status["sources"][0]["missing"], [source["nodes"][0]])
        self.assertTrue(status["retained_previous"])

    def test_duplicate_exact_name_is_ambiguous(self):
        source = self.selectors["sources"][0]
        url = self.environ[source["url_env"]]
        content = yaml.safe_load(self.payloads[url])
        content["proxies"].append(copy.deepcopy(content["proxies"][0]))
        self.payloads[url] = yaml.safe_dump(content).encode()
        files, status = self.build()
        self.assertIsNone(files)
        self.assertEqual(status["sources"][0]["ambiguous"], [source["nodes"][0]])

    def test_same_node_name_from_two_sources_stays_distinct(self):
        source = self.selectors["sources"][1]
        first_name = self.selectors["sources"][0]["nodes"][0]
        old_name = source["nodes"][0]
        source["nodes"][0] = first_name
        url = self.environ[source["url_env"]]
        content = yaml.safe_load(self.payloads[url])
        next(p for p in content["proxies"] if p["name"] == old_name)["name"] = first_name
        self.payloads[url] = yaml.safe_dump(content, allow_unicode=True).encode()
        files, _ = self.build()
        names = [p["name"] for p in yaml.safe_load(files[bundle.PROXIES_FILE])["proxies"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(sum(name.endswith(" :: " + first_name) for name in names), 2)

    def test_fetch_failure_never_exposes_url_or_exception(self):
        def fail(_url):
            raise RuntimeError("Network error at " + _url)
        files, status = bundle.build_bundle(self.selectors, self.environ, fail)
        serialized = json.dumps(status, ensure_ascii=False)
        self.assertIsNone(files)
        self.assertNotIn(SECRET_MARKER, serialized)
        self.assertNotIn("https://", serialized)
        self.assertTrue(all(s["errors"] == ["source_processing_failed"] for s in status["sources"]))

    def test_missing_secret_is_explicit(self):
        del self.environ["SOURCE_MUACLOUD"]
        files, status = self.build()
        self.assertIsNone(files)
        self.assertEqual(status["sources"][2]["errors"], ["missing_source_secret"])

    def test_invalid_port_blocks_entire_publication(self):
        url = self.environ["SOURCE_SPEEDY"]
        content = yaml.safe_load(self.payloads[url])
        content["proxies"][0]["port"] = True
        self.payloads[url] = yaml.safe_dump(content).encode()
        files, status = self.build()
        self.assertIsNone(files)
        self.assertEqual(len(status["sources"][1]["invalid"]), 1)

    def test_dialer_reference_is_rebound_and_unselected_dependency_blocks(self):
        source = self.selectors["sources"][0]
        proxies = copy.deepcopy(self.originals[source["id"]])
        proxies[0]["dialer-proxy"] = proxies[1]["name"]
        selected, report = bundle.select_proxies(source, proxies)
        self.assertEqual(selected[0]["dialer-proxy"], selected[1]["name"])
        self.assertFalse(report["invalid"])
        proxies[0]["dialer-proxy"] = "unselected dependency"
        _, report = bundle.select_proxies(source, proxies)
        self.assertEqual(report["invalid"], [proxies[0]["name"]])

    def test_complete_flclash_groups_and_match(self):
        files, _ = self.build()
        config = yaml.safe_load(files[bundle.CLASH_FILE])
        self.assertEqual([group["type"] for group in config["proxy-groups"]], ["select", "url-test", "fallback"])
        self.assertEqual(config["rules"], [f"MATCH,{bundle.GROUP_NAMES[0]}"])
        self.assertEqual(config["proxies"], yaml.safe_load(files[bundle.PROXIES_FILE])["proxies"])
        self.assertFalse(config["allow-lan"])
        names = {proxy["name"] for proxy in config["proxies"]}
        for group in config["proxy-groups"][1:]:
            self.assertEqual(set(group["proxies"]), names)


class ParserAndNetworkTests(unittest.TestCase):
    def test_yaml_error_is_sanitized(self):
        with self.assertRaises(bundle.BundleError) as context:
            bundle.parse_subscription(b"proxies: [password: never-emit-me")
        self.assertEqual(str(context.exception), "invalid_source_yaml")

    def test_unsafe_yaml_tags_are_rejected(self):
        with self.assertRaises(bundle.BundleError):
            bundle.parse_subscription(b"!!python/object/apply:os.system ['echo should-not-run']")

    def test_non_clash_payload_is_rejected(self):
        with self.assertRaises(bundle.BundleError) as context:
            bundle.parse_subscription(b"c3M6Ly9ub3QtYS1DbGFzaC1ZQU1M")
        self.assertEqual(str(context.exception), "missing_proxies_list")

    def test_http_and_userinfo_source_urls_rejected_without_network(self):
        with mock.patch.object(bundle.urllib.request, "build_opener") as opener:
            for url in ("http://example.invalid/token", "https://user:password@example.invalid/subscription"):
                with self.assertRaises(bundle.BundleError) as context:
                    bundle.fetch_subscription(url)
                self.assertEqual(str(context.exception), "invalid_source_url")
            opener.assert_not_called()

    def test_download_size_is_bounded(self):
        response = mock.Mock()
        response.read.return_value = b"12345"
        with self.assertRaises(bundle.BundleError) as context:
            bundle._read_response(response, 4)
        self.assertEqual(str(context.exception), "response_too_large")
        response.read.assert_called_once_with(5)

    def test_downgrade_redirect_is_rejected(self):
        handler = bundle.HTTPSRedirectHandler()
        with self.assertRaises(bundle.BundleError):
            handler.redirect_request(None, None, 302, "", {}, "http://example.invalid/token")


class PublicationAndRetentionTests(unittest.TestCase):
    def setUp(self):
        self.selectors, self.environ, self.payloads, _ = fixtures()
        self.files, self.status = bundle.build_bundle(self.selectors, self.environ, self.payloads.__getitem__)
        private_root = ROOT / ".private" / "tests"
        private_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=private_root)
        self.output = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def test_secret_gist_atomic_update_and_revision_free_links(self):
        requester = mock.Mock(side_effect=[gist(), gist()])
        links = bundle.publish_gist(self.files, self.status, TOKEN, GIST_ID, requester=requester)
        self.assertEqual(requester.call_args_list[0].args[:2], ("GET", f"/{GIST_ID}"))
        patch = requester.call_args_list[1].args
        self.assertEqual(patch[:2], ("PATCH", f"/{GIST_ID}"))
        self.assertEqual(set(patch[3]["files"]), {bundle.PROXIES_FILE, bundle.CLASH_FILE, bundle.STATUS_FILE})
        uploaded_status = json.loads(patch[3]["files"][bundle.STATUS_FILE]["content"])
        self.assertTrue(uploaded_status["published"])
        self.assertNotIn(SECRET_MARKER, json.dumps(uploaded_status))
        self.assertEqual(links["flclash_url"], f"https://gist.githubusercontent.com/{OWNER}/{GIST_ID}/raw/{bundle.CLASH_FILE}")
        self.assertTrue(self.status["published"])

    def test_public_gist_refused_before_patch(self):
        requester = mock.Mock(return_value=gist(private=False))
        with self.assertRaises(bundle.BundleError) as context:
            bundle.publish_gist(self.files, self.status, TOKEN, GIST_ID, requester=requester)
        self.assertEqual(str(context.exception), "gist_must_be_secret")
        self.assertEqual(requester.call_count, 1)

    def test_bootstrap_explicitly_creates_secret_gist(self):
        requester = mock.Mock(return_value=gist())
        bundle.publish_gist(self.files, self.status, TOKEN, None, initialize=True, requester=requester)
        args = requester.call_args.args
        self.assertEqual(args[:2], ("POST", ""))
        self.assertIs(args[3]["public"], False)

    def test_no_gist_id_cannot_accidentally_create_new_gist(self):
        requester = mock.Mock()
        with self.assertRaises(bundle.BundleError):
            bundle.publish_gist(self.files, self.status, TOKEN, None, requester=requester)
        requester.assert_not_called()

    def test_missing_node_keeps_previous_local_files_and_never_publishes(self):
        for filename in (bundle.PROXIES_FILE, bundle.CLASH_FILE):
            (self.output / filename).write_text("LAST_KNOWN_GOOD", encoding="utf-8")
        failed_status = copy.deepcopy(self.status)
        failed_status.update(result="blocked", matched_total=0)
        with mock.patch.object(bundle, "build_bundle", return_value=(None, failed_status)), \
             mock.patch.object(bundle, "publish_gist") as publisher, \
             contextlib.redirect_stdout(io.StringIO()):
            result = bundle.run(["publish", "--output-dir", str(self.output)])
        self.assertEqual(result, 1)
        publisher.assert_not_called()
        for filename in (bundle.PROXIES_FILE, bundle.CLASH_FILE):
            self.assertEqual((self.output / filename).read_text(encoding="utf-8"), "LAST_KNOWN_GOOD")
        self.assertFalse(json.loads((self.output / bundle.STATUS_FILE).read_text(encoding="utf-8"))["published"])

    def test_cli_publication_failure_keeps_previous_local_files(self):
        (self.output / bundle.CLASH_FILE).write_text("LAST_KNOWN_GOOD", encoding="utf-8")
        console = io.StringIO()
        with mock.patch.object(bundle, "build_bundle", return_value=(self.files, self.status)), \
             mock.patch.object(bundle, "publish_gist", side_effect=bundle.BundleError("gist_http_401")), \
             contextlib.redirect_stdout(console):
            result = bundle.run(["publish", "--output-dir", str(self.output)])
        self.assertEqual(result, 1)
        self.assertEqual((self.output / bundle.CLASH_FILE).read_text(), "LAST_KNOWN_GOOD")
        self.assertNotIn(SECRET_MARKER, console.getvalue())
        self.assertIn("gist_http_401", console.getvalue())

    def test_cli_success_writes_both_outputs(self):
        with mock.patch.object(bundle, "build_bundle", return_value=(self.files, self.status)), \
             contextlib.redirect_stdout(io.StringIO()):
            result = bundle.run(["build", "--output-dir", str(self.output)])
        self.assertEqual(result, 0)
        for name in self.files:
            self.assertEqual((self.output / name).read_text(encoding="utf-8"), self.files[name])

    def test_transport_failure_after_patch_reports_unknown_outcome(self):
        requester = mock.Mock(side_effect=[gist(), bundle.BundleError("gist_request_failed")])
        with self.assertRaises(bundle.BundleError):
            bundle.publish_gist(self.files, self.status, TOKEN, GIST_ID, requester=requester)
        self.assertEqual(self.status["publication_outcome"], "unknown")
        self.assertIsNone(self.status["retained_previous"])
        self.assertFalse(self.status["published"])

    def test_missing_token_is_rejected_without_network(self):
        with mock.patch.object(bundle.urllib.request, "build_opener") as opener:
            with self.assertRaises(bundle.BundleError) as context:
                bundle.gist_request("POST", "", "", {})
            self.assertEqual(str(context.exception), "missing_or_invalid_gist_token")
            opener.assert_not_called()

    def test_bad_selector_count_blocks_before_fetch(self):
        invalid = copy.deepcopy(self.selectors)
        invalid["expected_total"] = 26
        path = self.output / "bad-selectors.json"
        path.write_text(json.dumps(invalid), encoding="utf-8")
        with self.assertRaises(bundle.BundleError) as context:
            bundle.load_selectors(path)
        self.assertEqual(str(context.exception), "invalid_selectors")

    def test_unexpected_exception_text_is_never_printed(self):
        output = io.StringIO()
        with mock.patch.object(bundle, "build_bundle", side_effect=RuntimeError(SECRET_MARKER)), \
             contextlib.redirect_stdout(output):
            result = bundle.run(["build", "--output-dir", str(self.output)])
        self.assertEqual(result, 1)
        self.assertNotIn(SECRET_MARKER, output.getvalue())


if __name__ == "__main__":
    unittest.main()
