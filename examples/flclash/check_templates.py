#!/usr/bin/env python3
"""Check the credential-free FlClash examples without making network requests."""

from __future__ import annotations

import copy
import ipaddress
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parent
GROUP_NAMES = {
    "Identity", "Auto", "Proxy", "SelfHosted-Backup",
    "Subscription-Backup-1", "Subscription-Backup-2",
}
BUILTINS = {"DIRECT", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE"}
ANDROID_RULES = [
    "PROCESS-NAME,com.anthropic.claude,Identity",
    "PROCESS-NAME,com.android.vending,Identity",
    "PROCESS-NAME,com.google.android.apps.walletnfcrel,Identity",
]


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate mapping keys instead of silently keeping the last."""


def unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"Duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping
)


def load_template(platform):
    return yaml.load(
        (ROOT / f"{platform}.example.yaml").read_text(encoding="utf-8"),
        Loader=UniqueLoader,
    )


def rule_target(rule):
    fields = rule.split(",")
    return fields[-2] if fields[-1] == "no-resolve" else fields[-1]


class TemplateChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = {p: load_template(p) for p in ("macos", "android")}

    def test_no_nodes_or_subscription_credentials(self):
        for platform, doc in self.docs.items():
            with self.subTest(platform=platform):
                self.assertEqual(doc["proxies"], [])
                self.assertEqual(doc["proxy-providers"], {})
                groups = {g["name"]: g for g in doc["proxy-groups"]}
                self.assertEqual(set(groups), GROUP_NAMES)
                self.assertEqual(len(groups), len(doc["proxy-groups"]))
                for name, group in groups.items():
                    self.assertNotIn("use", group)
                    self.assertFalse(group.get("include-all"))
                    if name != "Proxy":
                        self.assertEqual(group["proxies"], ["REJECT"])

    def test_group_references_and_cycles(self):
        for platform, doc in self.docs.items():
            with self.subTest(platform=platform):
                groups = {g["name"]: g for g in doc["proxy-groups"]}
                visiting, visited = set(), set()

                def visit(name):
                    self.assertNotIn(name, visiting, "Strategy group cycle")
                    if name in visited:
                        return
                    visiting.add(name)
                    for target in groups[name]["proxies"]:
                        self.assertIn(target, GROUP_NAMES | BUILTINS)
                        if target in groups:
                            visit(target)
                    visiting.remove(name)
                    visited.add(name)

                for name in groups:
                    visit(name)

    def test_rule_targets(self):
        for platform, doc in self.docs.items():
            with self.subTest(platform=platform):
                for rule in doc["rules"]:
                    self.assertIsInstance(rule, str)
                    self.assertIn(rule_target(rule), GROUP_NAMES | BUILTINS)
                self.assertEqual(doc["rules"][-1], "MATCH,Proxy")

    def test_listener_and_dns_boundaries(self):
        for platform, doc in self.docs.items():
            with self.subTest(platform=platform):
                self.assertEqual(doc["mixed-port"], 7890)
                self.assertFalse(doc["allow-lan"])
                self.assertEqual(doc["bind-address"], "127.0.0.1")
                self.assertEqual(doc["mode"], "rule")
                self.assertFalse(doc["ipv6"])
                dns = doc["dns"]
                self.assertFalse(dns["ipv6"])
                self.assertTrue(dns["respect-rules"])
                self.assertEqual(dns["enhanced-mode"], "fake-ip")
                self.assertEqual(dns["listen"], "127.0.0.1:1053")
                self.assertTrue(all(s.endswith("#Identity") for s in dns["nameserver"]))
                self.assertTrue(all(s.endswith("#DIRECT") for s in dns["proxy-server-nameserver"]))
                self.assertNotIn("fallback", dns)
                self.assertEqual(dns["nameserver-policy"]["+.local"], "system")

    def test_no_personal_public_host_routes(self):
        for platform, doc in self.docs.items():
            with self.subTest(platform=platform):
                for rule in doc["rules"]:
                    fields = rule.split(",")
                    if fields[0] not in {"IP-CIDR", "IP-CIDR6"}:
                        continue
                    network = ipaddress.ip_network(fields[1], strict=False)
                    if network.num_addresses == 1:
                        self.assertFalse(network.network_address.is_global)

    def test_fixed_identity_and_manual_backups(self):
        for platform, doc in self.docs.items():
            with self.subTest(platform=platform):
                groups = {g["name"]: g for g in doc["proxy-groups"]}
                self.assertEqual(groups["Identity"]["type"], "select")
                self.assertEqual(groups["Identity"]["proxies"], ["REJECT"])
                self.assertEqual(groups["Auto"]["type"], "url-test")
                self.assertEqual(groups["Proxy"]["proxies"], [
                    "Auto", "SelfHosted-Backup", "Subscription-Backup-1", "Subscription-Backup-2",
                ])
                for name in GROUP_NAMES - {"Auto", "Proxy", "Identity"}:
                    self.assertEqual(groups[name]["type"], "select")

    def test_priority_of_local_and_personal_exceptions(self):
        for platform, doc in self.docs.items():
            with self.subTest(platform=platform):
                rules = doc["rules"]
                self.assertLess(
                    rules.index("IP-CIDR,100.64.0.0/10,Proxy,no-resolve"),
                    rules.index("GEOSITE,private,DIRECT"),
                )
                self.assertLess(
                    rules.index("DOMAIN-SUFFIX,kimi.com,Proxy"),
                    rules.index("GEOSITE,cn,DIRECT"),
                )
                self.assertIn("DOMAIN-SUFFIX,webshare.io,Identity", rules)
                self.assertIn("DOMAIN-SUFFIX,openai.com,Identity", rules)
                self.assertIn("DOMAIN-SUFFIX,anthropic.com,Identity", rules)

    def test_android_changes_are_limited_and_ordered(self):
        mac, android = self.docs["macos"], self.docs["android"]
        mac_process = [r for r in mac["rules"] if r.startswith("PROCESS-")]
        self.assertEqual(len(mac_process), 6)
        expected = []
        for rule in mac["rules"]:
            if rule == mac_process[0]:
                expected.extend(ANDROID_RULES)
            if rule in mac_process:
                continue
            if rule == "DOMAIN-SUFFIX,ntp.org,DIRECT":
                expected.append("DOMAIN,time.android.com,DIRECT")
            expected.append(rule)
        self.assertEqual(android["rules"], expected)
        for rule in ANDROID_RULES:
            self.assertLess(
                android["rules"].index(rule), android["rules"].index("GEOSITE,cn,DIRECT")
            )
        expected_dns = copy.deepcopy(mac["dns"])
        filters = expected_dns["fake-ip-filter"]
        filters.insert(filters.index("+.ntp.org"), "time.android.com")
        self.assertEqual(android["dns"], expected_dns)
        self.assertFalse(mac["tun"]["enable"])
        self.assertTrue(android["tun"]["enable"])

    def test_duplicate_yaml_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            yaml.load("port: 7890\nport: 1082\n", Loader=UniqueLoader)


class ChainChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = load_template("android-chain")
        cls.rules = cls.doc["rules"]
        cls.groups = {g["name"]: g for g in cls.doc["proxy-groups"]}

    def test_no_credentials_or_automatic_entry(self):
        self.assertEqual(self.doc["proxies"], [])
        self.assertEqual(self.doc["proxy-providers"], {})
        self.assertEqual(set(self.groups), {"Claude", "GPT", "FixedExit", "Entry"})
        self.assertEqual(len(self.groups), len(self.doc["proxy-groups"]))
        self.assertTrue(all(g["type"] == "select" for g in self.groups.values()))
        self.assertEqual(self.groups["Entry"]["proxies"], ["REJECT"])
        self.assertEqual(self.groups["FixedExit"]["proxies"], ["REJECT"])
        for name in ("Claude", "GPT"):
            self.assertEqual(self.groups[name]["proxies"], ["FixedExit", "Entry"])
        for rule in self.rules:
            self.assertIn(rule_target(rule), set(self.groups) | BUILTINS)
        self.assertEqual(self.rules[-1], "MATCH,FixedExit")

    def test_scoped_udp_and_tailnet_do_not_fall_through(self):
        rules = self.rules
        self.assertNotIn("NETWORK,UDP,REJECT", rules)
        udp_entry = rules.index("NETWORK,UDP,Entry")
        for rule in [
            "AND,((NETWORK,UDP),(PROCESS-NAME,com.anthropic.claude)),REJECT",
            "AND,((NETWORK,UDP),(DOMAIN-KEYWORD,claude)),REJECT",
            "AND,((NETWORK,UDP),(DOMAIN-KEYWORD,anthropic)),REJECT",
            "AND,((NETWORK,UDP),(DOMAIN-SUFFIX,clau.de)),REJECT",
            "AND,((NETWORK,UDP),(DOMAIN-SUFFIX,ts.net)),REJECT",
            "AND,((NETWORK,UDP),(IP-CIDR,100.64.0.0/10)),REJECT",
        ]:
            self.assertLess(rules.index(rule), udp_entry)
        self.assertLess(rules.index("AND,((NETWORK,UDP),(GEOSITE,cn)),DIRECT"), udp_entry)
        self.assertLess(udp_entry, rules.index("PROCESS-NAME,com.openai.chatgpt,GPT"))
        self.assertLess(
            rules.index("IP-CIDR,100.64.0.0/10,FixedExit,no-resolve"),
            rules.index("GEOSITE,private,DIRECT"),
        )
        self.assertLess(
            rules.index("DOMAIN-SUFFIX,ts.net,FixedExit"),
            rules.index("GEOSITE,private,DIRECT"),
        )

    def test_datadog_follows_claude_and_blocks_only_its_udp(self):
        host = "http-intake.logs.us5.datadoghq.com"
        rules = self.rules
        self.assertLess(
            rules.index(f"AND,((NETWORK,UDP),(DOMAIN,{host})),REJECT"),
            rules.index("NETWORK,UDP,Entry"),
        )
        self.assertLess(
            rules.index(f"DOMAIN,{host},Claude"),
            rules.index("DOMAIN-SUFFIX,datadoghq.com,FixedExit"),
        )
        for platform in ("macos", "android"):
            self.assertIn(f"DOMAIN,{host},Identity", load_template(platform)["rules"])

    def test_dns_and_listener_keep_explicit_boundaries(self):
        doc = self.doc
        self.assertFalse(doc["allow-lan"])
        self.assertEqual(doc["bind-address"], "127.0.0.1")
        self.assertFalse(doc["ipv6"])
        self.assertTrue(doc["tun"]["enable"])
        self.assertTrue(doc["tun"]["strict-route"])
        self.assertIn("IP-CIDR6,::/0,REJECT,no-resolve", self.rules)
        dns = doc["dns"]
        self.assertTrue(dns["respect-rules"])
        self.assertNotIn("fallback", dns)
        self.assertTrue(all(s.endswith("#FixedExit") for s in dns["nameserver"]))
        self.assertTrue(all(s.endswith("#DIRECT") for s in dns["proxy-server-nameserver"]))
        self.assertEqual(dns["nameserver-policy"]["+.lan"], "system")


if __name__ == "__main__":
    unittest.main(verbosity=2)
