from __future__ import annotations

import unittest
from unittest.mock import patch

from instagram_archive.graph_api import InstagramAPIError, InstagramGraphAPI


class GraphAPITests(unittest.TestCase):
    def test_collects_profile_and_paginates_media_without_mutating_input(self) -> None:
        first = {
            "business_discovery": {
                "id": "42",
                "username": "maysanchess",
                "followers_count": 123,
                "media": {
                    "data": [{"id": "a", "caption": "Primeira"}],
                    "paging": {"next": "https://graph.facebook.com/v26.0/next?after=x&access_token=leak"},
                },
            }
        }
        second = {"data": [{"id": "b", "media_type": "IMAGE"}]}
        client = InstagramGraphAPI("secret", "99")
        with patch.object(client, "_get", side_effect=[first, second]) as get:
            snapshot = client.collect("@MaysanChess")

        self.assertEqual(snapshot.profile["username"], "maysanchess")
        self.assertNotIn("media", snapshot.profile)
        self.assertEqual([item["id"] for item in snapshot.media], ["a", "b"])
        self.assertNotIn("access_token", get.call_args_list[1].args[0])

    def test_rejects_untrusted_pagination_host(self) -> None:
        client = InstagramGraphAPI("secret", "99")
        with self.assertRaisesRegex(InstagramAPIError, "insegura"):
            client._get_next("https://attacker.example/steal?access_token=secret")

    def test_validates_username_and_limit(self) -> None:
        client = InstagramGraphAPI("secret", "99")
        with self.assertRaises(ValueError):
            client.collect("bad/user")
        with self.assertRaises(ValueError):
            client.collect("maysanchess", max_media=0)


if __name__ == "__main__":
    unittest.main()
