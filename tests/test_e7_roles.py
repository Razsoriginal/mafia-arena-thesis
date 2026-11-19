"""E7-R1: one key per role, no silent fallback, no borrowing across roles
(master brief SS7.7). A role is configured only by its own three
variables; a missing one is an error, never a fallback to another role."""
import os
import unittest
from unittest.mock import patch

from src import roles


class TestRoles(unittest.TestCase):
    def test_role_reads_only_its_own_variables(self):
        env = {"Reviewer_Base_Url": "https://r.example/v1", "Reviewer_API_Key": "k-r",
               "Reviewer_Model": "fam/rev", "Monitor_API_Key": "k-m"}
        with patch.dict(os.environ, env, clear=True):
            c = roles.role_config("Reviewer")
        self.assertEqual((c.base_url, c.api_key, c.model), ("https://r.example/v1", "k-r", "fam/rev"))

    def test_missing_key_is_an_error_not_a_fallback(self):
        env = {"Monitor_Base_Url": "https://m.example/v1", "Monitor_Model": "fam/mon",
               "Aicredits_API_Key": "k-backbone", "LLM_API_KEY": "k-legacy", "Reviewer_API_Key": "k-r"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(roles.RoleNotConfigured) as cm:
                roles.role_config("Monitor")
        self.assertIn("Monitor_API_Key", str(cm.exception))
        self.assertNotIn("k-", str(cm.exception))

    def test_two_roles_may_not_share_a_key(self):
        env = {}
        for r in ("BackboneB", "Monitor"):
            env.update({f"{r}_Base_Url": "https://x.example/v1", f"{r}_API_Key": "same-key", f"{r}_Model": "m"})
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(roles.RoleNotConfigured):
                roles.assert_distinct_keys(["BackboneB", "Monitor"])

    def test_unknown_role_is_refused(self):
        with self.assertRaises(ValueError):
            roles.role_config("Whatever")

    def test_repr_never_shows_the_key(self):
        env = {"Author_Base_Url": "https://a.example/v1", "Author_API_Key": "sk-secret-123", "Author_Model": "m"}
        with patch.dict(os.environ, env, clear=True):
            c = roles.role_config("Author")
        self.assertNotIn("sk-secret-123", repr(c))
        self.assertNotIn("sk-secret-123", str(c))


if __name__ == "__main__":
    unittest.main()
