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


def legacy_selectors():
    """A v1 manifest without node_order remains supported after live additions."""
    return {
        "version": 1, "expected_total": 27,
        "sources": [
            {"id": identifier, "name": name, "url_env": variable,
             "nodes": [f"{identifier} original node {number + 1}" for number in range(count)]}
            for identifier, name, variable, count in (
                ("first", "First source", "SOURCE_FIRST", 14),
                ("speedy", "Speedy source", "SOURCE_SPEEDY", 8),
                ("muacloud", "Mua source", "SOURCE_MUACLOUD", 3),
                ("fourth", "Fourth source", "SOURCE_FOURTH", 2),
            )
        ],
    }


def output_names(selectors):
    return [f'{source["name"]} :: {name}'
            for source in selectors["sources"] for name in source["nodes"]]


def combined_selectors():
    selectors = legacy_selectors()
    original_order = output_names(selectors)
    # One recommendation belongs to an existing source, so source order alone
    # would incorrectly put it ahead of the remaining original selections.
    source = selectors["sources"][0]
    source["nodes"].append("new recommendation in original source")
    additions = [f'{source["name"]} :: {source["nodes"][-1]}']
    for index, count in enumerate((2, 2, 1, 1, 1)):
        spec = {"id": f"added_{index}", "name": f"Added source {index}",
                "url_env": f"SOURCE_ADDED_{index}",
                "nodes": [f"new node {number}" for number in range(count)]}
        selectors["sources"].append(spec)
        additions.extend(f'{spec["name"]} :: {name}' for name in spec["nodes"])
    selectors.update(expected_total=35, node_order=original_order + additions)
    return selectors


def fixtures(selectors=None):
    selectors = legacy_selectors() if selectors is None else copy.deepcopy(selectors)
    environ, payloads, originals = {}, {}, {}
    for index, spec in enumerate(selectors["sources"]):
        url = f"https://provider-{index}.example.invalid/subscription?token={SECRET_MARKER}"
        environ[spec["url_env"]] = url
        proxies = []
        for number, name in enumerate(spec["nodes"]):
            proxy = {
                "name": name, "type": ("ss", "trojan", "anytls", "vless")[index % 4],
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
        groups = config["proxy-groups"]
        self.assertEqual([group["name"] for group in groups[:3]],
                         ["9929 手动选择", "9929 自动测速", "9929 故障转移"])
        self.assertEqual([group["type"] for group in groups[:3]], ["select", "url-test", "fallback"])
        self.assertEqual(config["rules"][-2:], ["GEOIP,CN,DIRECT", "MATCH,9929 手动选择"])
        self.assertEqual(config["proxies"], yaml.safe_load(files[bundle.PROXIES_FILE])["proxies"])
        self.assertFalse(config["allow-lan"])
        self.assertNotIn("tun", config)
        self.assertTrue(config["dns"]["enable"])
        self.assertEqual(config["dns"]["enhanced-mode"], "fake-ip")
        self.assertTrue(config["sniffer"]["enable"])
        names = [proxy["name"] for proxy in config["proxies"]]
        self.assertEqual(names, output_names(self.selectors))
        self.assertEqual(groups[0]["proxies"], ["9929 自动测速", "9929 故障转移", *names])
        for group in groups[1:3]:
            self.assertEqual(group["proxies"], names)
        for group in groups[3:]:
            self.assertEqual(group["type"], "select")
            self.assertEqual(group["proxies"], ["9929 手动选择", "9929 自动测速", "9929 故障转移", *names])

    def test_35_node_global_order_with_recommendation_in_original_source(self):
        selectors, environ, payloads, originals = fixtures(combined_selectors())
        self.assertEqual(len(selectors["sources"]), 9)
        self.assertNotEqual(selectors["node_order"], output_names(selectors))
        files, status = bundle.build_bundle(selectors, environ, payloads.__getitem__)
        self.assertEqual(status["matched_total"], 35)
        self.assertEqual(status["result"], "ready")
        expected_order = selectors["node_order"]
        self.assertEqual(expected_order[:27], output_names(legacy_selectors()))
        self.assertEqual(len(expected_order[27:]), 8)
        proxies = yaml.safe_load(files[bundle.PROXIES_FILE])["proxies"]
        self.assertEqual([proxy["name"] for proxy in proxies], expected_order)
        config = yaml.safe_load(files[bundle.CLASH_FILE])
        self.assertEqual(config["proxies"], proxies)
        for group in config["proxy-groups"]:
            self.assertEqual([name for name in group["proxies"] if name in expected_order], expected_order)
        # Reordering must leave every source protocol field intact.
        for source in selectors["sources"]:
            for original in originals[source["id"]]:
                expected = copy.deepcopy(original)
                expected["name"] = f'{source["name"]} :: {original["name"]}'
                self.assertEqual(next(proxy for proxy in proxies if proxy["name"] == expected["name"]), expected)

    def test_node_order_is_independent_of_source_iteration_order(self):
        selectors, environ, payloads, _ = fixtures(combined_selectors())
        selectors["sources"].reverse()
        files, _ = bundle.build_bundle(selectors, environ, payloads.__getitem__)
        self.assertEqual([proxy["name"] for proxy in yaml.safe_load(files[bundle.PROXIES_FILE])["proxies"]],
                         selectors["node_order"])


class RoutingTests(unittest.TestCase):
    def setUp(self):
        selectors, environ, payloads, _ = fixtures(combined_selectors())
        files, _ = bundle.build_bundle(selectors, environ, payloads.__getitem__)
        self.config = yaml.safe_load(files[bundle.CLASH_FILE])

    def domain_policy(self, host, domestic=False):
        """Evaluate only the relevant domain and final policy semantics locally."""
        for rule in self.config["rules"]:
            fields = rule.split(",")
            kind = fields[0]
            if kind == "DOMAIN" and host == fields[1]:
                return fields[2]
            if kind == "DOMAIN-SUFFIX" and (host == fields[1] or host.endswith("." + fields[1])):
                return fields[2]
            if kind == "GEOIP" and fields[1] == "CN" and domestic:
                return fields[2]
            if kind == "MATCH":
                return fields[1]
        self.fail("missing final policy")

    def test_service_groups_and_representative_domains(self):
        cases = {
            "Netflix": ("netflix.com", "api.netflix.com", "video.nflxvideo.net"),
            "Disney+": ("disneyplus.com", "www.disneyplus.com", "disney.api.edge.bamgrid.com",
                        "disney.playback.edge.bamgrid.com", "www.disneyaccount.com", "cdn.registerdisney.go.com"),
            "OpenAI": ("chatgpt.com", "api.openai.com", "cdn.oaistatic.com", "openaicom.imgix.net",
                       "auth0.openai.com", "ab.oaistatsig.com", "openaiassets.blob.core.windows.net"),
            "Claude": ("claude.ai", "api.anthropic.com", "claude.com", "artifacts.claudeusercontent.com",
                       "widget.claudemcpcontent.com", "sso.claude.com"),
            "YouTube": ("youtube.com", "www.youtube.com", "r1.googlevideo.com", "youtubei.googleapis.com"),
            "Telegram": ("t.me", "api.telegram.org"),
            "Apple": ("www.apple.com", "icloud.com"),
            "Microsoft": ("login.microsoftonline.com", "office.com"),
        }
        groups = {group["name"]: group for group in self.config["proxy-groups"]}
        self.assertEqual(set(groups), {"9929 手动选择", "9929 自动测速", "9929 故障转移", *cases})
        for service, hosts in cases.items():
            self.assertEqual(groups[service]["type"], "select")
            self.assertEqual(groups[service]["proxies"][0], "9929 手动选择")
            for host in hosts:
                with self.subTest(service=service, host=host):
                    self.assertEqual(self.domain_policy(host), service)
                    self.assertEqual(self.domain_policy(host, domestic=True), service)

    def test_exact_hosts_on_shared_domains_do_not_capture_unrelated_traffic(self):
        for host in ("storage.googleapis.com", "googleapis.com", "sub.youtubei.googleapis.com",
                     "other.imgix.net", "sub.openaicom.imgix.net", "unrelated.cloudfront.net",
                     "cdn.akamaized.net", "other.api.edge.bamgrid.com", "notnetflix.com",
                     "netflix.com.example.invalid"):
            with self.subTest(host=host):
                self.assertEqual(self.domain_policy(host), "9929 手动选择")
        self.assertEqual(self.domain_policy("unrelated.example.cn", domestic=True), "DIRECT")

    def test_service_rules_precede_every_direct_rule_and_final_match(self):
        rules = self.config["rules"]
        service_indices, direct_indices = [], []
        for index, rule in enumerate(rules):
            fields = rule.split(",")
            if fields[0] in ("DOMAIN", "DOMAIN-SUFFIX") and fields[2] != "DIRECT":
                service_indices.append(index)
            if len(fields) > 2 and fields[2] == "DIRECT":
                direct_indices.append(index)
            self.assertNotIn(fields[0], ("GEOSITE", "RULE-SET"))
        self.assertTrue(service_indices)
        self.assertTrue(direct_indices)
        self.assertLess(max(service_indices), min(direct_indices))
        self.assertEqual(rules[-2:], ["GEOIP,CN,DIRECT", "MATCH,9929 手动选择"])
        self.assertEqual(sum(rule.startswith("MATCH,") for rule in rules), 1)
        forbidden = {"cloudfront.net", "akamaized.net", "googleapis.com", "imgix.net", "bamgrid.com"}
        for rule in rules:
            fields = rule.split(",")
            if fields[0] in ("DOMAIN", "DOMAIN-SUFFIX"):
                self.assertNotIn(fields[1], forbidden)

    def test_lan_and_private_address_rules_use_no_resolve(self):
        rules = self.config["rules"]
        for network in ("10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16",
                        "172.16.0.0/12", "192.168.0.0/16"):
            self.assertIn(f"IP-CIDR,{network},DIRECT,no-resolve", rules)
        for network in ("::1/128", "fc00::/7", "fe80::/10"):
            self.assertIn(f"IP-CIDR6,{network},DIRECT,no-resolve", rules)
        for rule in rules:
            if rule.startswith(("IP-CIDR,", "IP-CIDR6,")):
                self.assertTrue(rule.endswith(",no-resolve"))
                self.assertIn(rule.split(",")[2], ("DIRECT", "Telegram"))
        self.assertEqual(self.domain_policy("localhost"), "DIRECT")
        self.assertEqual(self.domain_policy("printer.local"), "DIRECT")
        self.assertEqual(self.domain_policy("router.lan"), "DIRECT")

    def test_native_telegram_dc_ips_are_routed_without_broad_cloud_ranges(self):
        import ipaddress
        networks = [ipaddress.ip_network(rule.split(",")[1]) for rule in self.config["rules"]
                    if rule.startswith(("IP-CIDR,", "IP-CIDR6,")) and rule.split(",")[2] == "Telegram"]
        for value in ("149.154.167.51", "91.108.5.10", "2001:b28:f23d::1"):
            address = ipaddress.ip_address(value)
            self.assertTrue(any(address.version == n.version and address in n for n in networks))
        for value in ("8.8.8.8", "91.108.32.1", "2001:4860:4860::8888", "192.168.2.1"):
            address = ipaddress.ip_address(value)
            self.assertFalse(any(address.version == n.version and address in n for n in networks))

    def test_all_group_and_rule_targets_exist(self):
        groups = self.config["proxy-groups"]
        node_names = {proxy["name"] for proxy in self.config["proxies"]}
        group_names = {group["name"] for group in groups}
        self.assertEqual(len(group_names), len(groups))
        self.assertFalse(node_names & group_names)
        available = node_names | group_names | {"DIRECT", "REJECT"}
        for group in groups:
            self.assertNotIn(group["name"], group["proxies"])
            self.assertEqual(len(group["proxies"]), len(set(group["proxies"])))
            self.assertTrue(set(group["proxies"]) <= available)
        for rule in self.config["rules"]:
            fields = rule.split(",")
            self.assertIn(fields[1] if fields[0] == "MATCH" else fields[2], available)


class SelectorOrderingTests(unittest.TestCase):
    def load(self, selectors):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "selectors.json"
            path.write_text(json.dumps(selectors), encoding="utf-8")
            return bundle.load_selectors(path)

    def test_optional_order_and_legacy_source_order_load(self):
        for selectors in (legacy_selectors(), combined_selectors()):
            with self.subTest(ordered="node_order" in selectors):
                self.assertEqual(self.load(selectors), selectors)

    def test_malformed_order_is_rejected_by_loader_and_direct_build_before_fetch(self):
        selectors = combined_selectors()
        order = selectors["node_order"]
        invalid_orders = {
            "null": None, "string": order[0], "mapping": {"node": order[0]},
            "empty": [], "missing": order[:-1], "extra": order + ["Unknown :: node"],
            "duplicate": order[:-1] + [order[0]],
            "unknown": order[:-1] + ["Unknown :: node"],
            "bare_name": order[:-1] + ["new node 0"],
            "non_string": order[:-1] + [42], "nested": order[:-1] + [[order[-1]]],
        }
        for label, invalid_order in invalid_orders.items():
            with self.subTest(label=label):
                invalid = copy.deepcopy(selectors)
                invalid["node_order"] = invalid_order
                with self.assertRaises(bundle.BundleError) as context:
                    self.load(invalid)
                self.assertEqual(context.exception.code, "invalid_selectors")
                fetcher = mock.Mock()
                files, status = bundle.build_bundle(invalid, {}, fetcher)
                fetcher.assert_not_called()
                self.assertIsNone(files)
                self.assertEqual(status["errors"], ["invalid_selectors"])
                self.assertEqual(status["result"], "blocked")
                self.assertFalse(status["published"])
                self.assertTrue(status["retained_previous"])

    def test_direct_build_rejects_invalid_count_and_duplicate_output_names(self):
        wrong_count = legacy_selectors()
        wrong_count["expected_total"] = 26
        duplicate = legacy_selectors()
        duplicate["sources"][0]["nodes"][1] = duplicate["sources"][0]["nodes"][0]
        for invalid in (wrong_count, duplicate, None, [], {"version": 1}):
            with self.subTest(invalid=invalid):
                fetcher = mock.Mock()
                files, status = bundle.build_bundle(invalid, {}, fetcher)
                self.assertIsNone(files)
                self.assertEqual(status["errors"], ["invalid_selectors"])
                fetcher.assert_not_called()


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

    def test_invalid_order_keeps_both_previous_outputs_and_never_publishes(self):
        for filename in (bundle.PROXIES_FILE, bundle.CLASH_FILE):
            (self.output / filename).write_text("LAST_KNOWN_GOOD", encoding="utf-8")
        invalid = copy.deepcopy(self.selectors)
        invalid["node_order"] = output_names(invalid)[:-1]
        # Exercise build_bundle's own guard even if a caller bypasses the loader.
        with mock.patch.object(bundle, "load_selectors", return_value=invalid), \
             mock.patch.object(bundle, "fetch_subscription") as fetcher, \
             mock.patch.object(bundle, "publish_gist") as publisher, \
             contextlib.redirect_stdout(io.StringIO()):
            result = bundle.run(["publish", "--output-dir", str(self.output)])
        self.assertEqual(result, 1)
        fetcher.assert_not_called()
        publisher.assert_not_called()
        for filename in (bundle.PROXIES_FILE, bundle.CLASH_FILE):
            self.assertEqual((self.output / filename).read_text(encoding="utf-8"), "LAST_KNOWN_GOOD")
        status = json.loads((self.output / bundle.STATUS_FILE).read_text(encoding="utf-8"))
        self.assertEqual(status["errors"], ["invalid_selectors"])
        self.assertTrue(status["retained_previous"])
        self.assertFalse(status["published"])

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
