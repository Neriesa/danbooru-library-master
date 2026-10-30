# -*- coding: utf-8 -*-
"""Весь путь: сканирование папки, сверка с (поддельным) Danbooru, пробный режим, перенос, откат, Favorites."""

import tempfile
import unittest
from pathlib import Path

from . import STATE, helpers


class SiteFlow(unittest.TestCase):
    def setUp(self):
        from dlm import config
        from dlm.db import LibraryDB
        from dlm.net import configure_session
        self.root = Path(tempfile.mkdtemp())
        self.db = LibraryDB(self.root / "lib.db")
        configure_session("gold_user", "goldkey")
        config.CONFIG["username"] = "gold_user"
        md5 = {}
        for name, seed in (("fav", 11), ("notfav", 12), ("missing", 13), ("deleted", 14)):
            md5[name] = helpers.make_image(self.root / f"{name}.png", seed)
        (self.root / "fav_copy.png").write_bytes((self.root / "fav.png").read_bytes())
        helpers.add_post(STATE, 5001, md5["fav"])
        helpers.add_post(STATE, 5002, md5["notfav"])
        helpers.add_post(STATE, 5003, md5["deleted"], deleted=True)
        self.md5 = md5
        for user in STATE.favs:                            # каждый тест начинает с чистого избранного
            STATE.favs[user] = set(range(1, 61))
        STATE.favs["gold_user"].add(5001)

    def tearDown(self):
        self.db.close()

    def check(self, auto):
        from dlm.site import check_against_danbooru
        check_against_danbooru(self.db, self.root, "gold_user", True, False, auto, helpers.say, helpers.progress)

    def categories(self):
        from dlm.site import build_results
        return {Path(r["filepath"]).name: r["category"] for r in build_results(self.db, self.root)}

    def test_duplicates_are_found_and_not_deleted(self):
        from dlm.dupes import find_duplicate_groups, scan_library
        scan_library(self.db, self.root, helpers.say, helpers.progress)
        groups = find_duplicate_groups(self.db, 5, False, helpers.say)
        exact = [g for g in groups if g["kind"] == "exact"]
        self.assertEqual(len(exact), 1)
        self.assertEqual(sorted(Path(m["path"]).name for m in exact[0]["members"]), ["fav.png", "fav_copy.png"])
        self.assertTrue((self.root / "fav_copy.png").exists())

    def test_check_and_dry_run_then_move_and_undo(self):
        from dlm.constants import NOTFOUND_PREFIX, OTHER_DIR, SITE_DELETED_PREFIX
        from dlm.mover import move_marked, plan_moves, undo_moves
        from dlm.site import pending_moves
        self.check(auto=False)                                   # пробный режим: ничего не переносится
        cats = self.categories()
        self.assertEqual(cats["fav.png"], "fav")
        self.assertEqual(cats["notfav.png"], "not_fav")
        self.assertEqual(cats["missing.png"], "not_found")
        self.assertEqual(cats["deleted.png"], "deleted")
        self.assertTrue((self.root / "missing.png").exists())
        todo = pending_moves(self.db, self.root)
        self.assertEqual(len(todo), 2)
        plan = plan_moves(self.root, todo)
        self.assertEqual({p["new_name"] for p in plan}, {NOTFOUND_PREFIX + "missing.png", SITE_DELETED_PREFIX + "deleted.png"})
        move_marked(self.db, self.root, todo, helpers.say, helpers.progress)
        self.assertTrue((self.root / OTHER_DIR / (NOTFOUND_PREFIX + "missing.png")).exists())
        self.assertFalse((self.root / "missing.png").exists())
        self.assertTrue((self.root / "fav.png").exists(), "найденные файлы не трогаются")
        restored, _ = undo_moves(self.db, "move_notfound", helpers.say)
        self.assertEqual(restored, 2)
        self.assertTrue((self.root / "missing.png").exists())

    def test_auto_move_after_check(self):
        from dlm.constants import NOTFOUND_PREFIX, OTHER_DIR
        self.check(auto=True)
        self.assertTrue((self.root / OTHER_DIR / (NOTFOUND_PREFIX + "missing.png")).exists())

    def test_free_account_can_run_the_check(self):
        from dlm.net import configure_session
        configure_session("free_user", "freekey")
        self.check(auto=False)
        self.assertEqual(self.categories()["missing.png"], "not_found")

    def test_add_and_remove_favorites(self):
        from dlm.actions import add_favorites_batch, remove_favorites_batch
        from dlm.constants import TRASH_DIR
        self.check(auto=False)
        added, already, failed = add_favorites_batch(self.db, [5002], helpers.say, helpers.progress)[:3]
        self.assertEqual((added, failed), (1, 0))
        self.assertIn(5002, STATE.favs["gold_user"])
        remove_favorites_batch(self.db, self.root, [(5001, self.md5["fav"])], helpers.say, helpers.progress)
        self.assertNotIn(5001, STATE.favs["gold_user"])
        trash = {p.name for p in (self.root / TRASH_DIR).iterdir()}
        self.assertTrue(any(n.startswith("5001") for n in trash), trash)
        self.assertFalse((self.root / "fav.png").exists())
        self.assertFalse((self.root / "fav_copy.png").exists(), "копии файла уходят вместе с ним")


class BrowseFallback(unittest.TestCase):
    def test_free_account_gets_simplified_query_and_gold_does_not(self):
        from dlm import browse
        from dlm.bridges import BrowseServices
        from dlm.config import CONFIG
        from dlm.net import configure_session
        store = browse.Store(Path(tempfile.mkdtemp()) / "b.db")
        opts = {"tag": "artist_3", "period": browse.PERIODS[1], "pages": 1}
        for user, key, simplified in (("free_user", "freekey", True), ("gold_user", "goldkey", False)):
            configure_session(user, key)
            CONFIG["username"] = user
            sv = BrowseServices(None, None)
            cands, _ = browse.fetch_candidates(sv, store, browse.SRC_BEST, opts, None, refresh=True)
            self.assertTrue(cands)
            self.assertEqual(bool(sv.last_note), simplified, user)


class AccountCheck(unittest.TestCase):
    def test_verify_credentials(self):
        from dlm.account import AccountError, verify_credentials
        self.assertEqual(verify_credentials("gold_user", "goldkey")["tier"], "gold")
        self.assertEqual(verify_credentials("free_user", "freekey")["tier"], "free")
        with self.assertRaises(AccountError) as ctx:
            verify_credentials("free_user", "wrong")
        self.assertEqual(ctx.exception.kind, "auth")


if __name__ == "__main__":
    unittest.main()
