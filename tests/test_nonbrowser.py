from __future__ import annotations

import unittest
from unittest.mock import patch

import app as app_module
import rank_tracker


class RankTrackerTests(unittest.TestCase):
    def test_load_targets_and_find_keyword_url(self):
        targets = rank_tracker.load_targets()
        self.assertGreaterEqual(len(targets), 35)
        target = rank_tracker.load_test_target("SEO Consulting Services")
        self.assertEqual(target["target_url"], "https://tekglide.com/seo-consulting-services/")

    def test_global_positions(self):
        self.assertEqual(rank_tracker.global_position(1, 3), 3)
        self.assertEqual(rank_tracker.global_position(2, 5), 15)
        self.assertEqual(rank_tracker.global_position(3, 5), 25)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app_module.app.config.update(TESTING=True)
        cls.client = app_module.app.test_client()

    def setUp(self):
        with app_module._job_lock:
            app_module._job_state.update(
                running=False,
                progress=["Ready to check one keyword."],
                result=None,
                error=None,
            )

    def test_index_and_status_response(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        status = self.client.get("/api/status")
        self.assertEqual(status.status_code, 200)
        self.assertIn("running", status.get_json())
        self.assertIn("progress", status.get_json())

    def test_check_requires_all_confirmations(self):
        response = self.client.post(
            "/api/check",
            json={"keyword": "SEO Consulting Services", "checklist": {"vpn": True}},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("checklist", response.get_json()["error"].lower())

    def test_check_prevents_simultaneous_jobs(self):
        payload = {
            "keyword": "SEO Consulting Services",
            "checklist": {"vpn": True, "location": True, "captcha": True},
        }
        with patch.object(app_module, "_start_job"):
            first = self.client.post("/api/check", json=payload)
            second = self.client.post("/api/check", json=payload)
        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 409)


if __name__ == "__main__":
    unittest.main()
