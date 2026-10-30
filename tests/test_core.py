# -*- coding: utf-8 -*-
import json
import random
import tempfile
import unittest
from datetime import date
from pathlib import Path

from PIL import Image

from . import STATE, helpers


class HashingAndDuplicates(unittest.TestCase):
    def test_phash_survives_resize_but_differs_for_other_images(self):
        from dlm.imaging import phash_hex
        tmp = Path(tempfile.mkdtemp())
        helpers.make_image(tmp / "a.png", 1, (128, 128))
        helpers.make_image(tmp / "b.png", 2, (128, 128))
        a = Image.open(tmp / "a.png")
        small = a.resize((64, 64))
        ha, hs, hb = (int(phash_hex(x), 16) for x in (a, small, Image.open(tmp / "b.png")))
        self.assertLess(bin(ha ^ hs).count("1"), 12)
        self.assertGreater(bin(ha ^ hb).count("1"), 12)

    def test_star_clustering_does_not_chain(self):
        from dlm.dupes import cluster_by_phash
        # A~B и B~C, но A и C далеки: цепочка не должна склеиваться в одну группу
        a = 0
        b = 0b11111                       # 5 бит от A
        c = 0b11111 | (0b11111 << 5)      # 5 бит от B, 10 от A
        units = [{"phash": a, "size": 100}, {"phash": b, "size": 90}, {"phash": c, "size": 80}]
        groups = cluster_by_phash(units, 5)
        sizes = sorted(len(g) for g in groups)
        self.assertNotIn(3, sizes)

    def test_marks_are_stripped_and_planned(self):
        from dlm.constants import NOTFOUND_PREFIX, SITE_DELETED_PREFIX
        from dlm.mover import plan_moves, strip_marks
        self.assertEqual(strip_marks(NOTFOUND_PREFIX + SITE_DELETED_PREFIX + "x.jpg"), "x.jpg")
        tmp = Path(tempfile.mkdtemp())
        f = tmp / "x.jpg"
        f.write_bytes(b"1")
        plan = plan_moves(tmp, [(str(f), "not_found"), (str(f), "fav")])
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["new_name"], NOTFOUND_PREFIX + "x.jpg")
        self.assertTrue(f.exists(), "пробный режим ничего не меняет")


class Accounts(unittest.TestCase):
    def test_parse_account_levels(self):
        from dlm.account import parse_account
        self.assertEqual(parse_account({"level": 20, "level_string": "Member"}, "u")["tier"], "free")
        self.assertEqual(parse_account({"level": 30, "level_string": "Gold"}, "u")["tag_limit"], 6)
        self.assertEqual(parse_account({"level_string": "Platinum"}, "u")["tier"], "gold")
        self.assertEqual(parse_account({}, "u")["tier"], "unknown")

    def test_tag_limit_message_is_recognised(self):
        from dlm.net import TagLimitError, check_tag_limit
        body = json.dumps({"error": "PostQuery::TagLimitError", "message": "You cannot search for more than 2 tags at a time"})
        with self.assertRaises(TagLimitError):
            check_tag_limit(422, body)
        check_tag_limit(200, body)                       # при успехе ничего не происходит
        check_tag_limit(422, '{"message": "other"}')


class Config(unittest.TestCase):
    def test_key_fallback_to_config_without_keyring(self):
        from dlm import config
        config.CONFIG.clear()
        config.CONFIG["username"] = "someone"
        self.assertFalse(config.store_api_key("someone", "KEY"))
        self.assertEqual(config.CONFIG["api_key"], "KEY")
        self.assertEqual(config.get_credentials(), ("someone", "KEY"))

    def test_save_config_keeps_foreign_keys(self):
        from dlm import config, browse
        config.CONFIG.clear()
        browse.save_ratings({"g"})
        config.CONFIG["last_folder"] = "/x"
        config.save_config()
        disk = json.loads(config.CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertEqual(disk["browse_ratings"], "g")
        self.assertEqual(disk["last_folder"], "/x")

    def test_broken_config_is_kept_aside(self):
        from dlm import config
        config.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        config.CONFIG_PATH.write_text("{ not json", encoding="utf-8")
        self.assertEqual(config.load_config(), {})
        self.assertTrue(config.CONFIG_PATH.with_name("config.json.bad").exists())


class TasteModel(unittest.TestCase):
    def test_model_prefers_what_the_user_likes(self):
        from dlm import browse
        rng = random.Random(5)

        def post(liked):
            artist = f"a:{rng.choice(['fav1', 'fav2'] if liked and rng.random() < 0.7 else ['x%d' % rng.randrange(30)])}"
            toks = {artist, "r:g"}
            toks |= {f"t:tag{rng.randrange(40)}" for _ in range(4)}
            if liked and rng.random() < 0.5:
                toks.add("t:liked_tag")
            return toks

        favs = [post(True) for _ in range(300)]
        bg = [post(False) for _ in range(900)]
        weights, _ = browse.train(favs, bg)
        pos = [browse.score_tokens(post(True), weights) for _ in range(300)]
        neg = [browse.score_tokens(post(False), weights) for _ in range(300)]
        wins = sum(p > n for p, n in zip(pos, neg)) / 300
        self.assertGreater(wins, 0.7)

    def post(self, pid, artist="x", tags="", score=10, preview="p.jpg"):
        return {"id": pid, "rating": "g", "score": score, "fav_count": 0, "a": artist, "c": "", "s": "", "t": tags,
                "preview": preview, "ext": "jpg", "w": 1, "h": 1, "created": ""}

    def ctx(self, **kw):
        ctx = {"profile": None, "fav_ids": set(), "blocked": set(), "seen": {}, "ratings": set("gsqe"), "rng": random.Random(1)}
        ctx.update(kw)
        return ctx

    def profile(self, weights):
        return {"weights": weights, "bg_scores": [], "fav_scores": [0.0, 1.0, 2.0], "ignored": [], "fav_artists": ["known"]}

    def test_tag_count_alone_does_not_win(self):
        from dlm import browse
        weights = {f"t:w{i}": 0.3 for i in range(30)}
        weights["a:loved"] = 1.0
        many = {f"t:w{i}" for i in range(30)}
        self.assertGreater(browse.score_tokens(many, weights), browse.score_tokens({"a:loved"}, weights))
        self.assertLess(browse.taste_score(many, weights) / browse.taste_score({"a:loved"}, weights), 2.5)

    def test_decisions_change_the_order_without_a_profile(self):
        from dlm import browse
        posts = [self.post(1, "a1", score=50), self.post(2, "a2", score=5)]
        before, _s = browse.rank_and_filter(posts, self.ctx())
        self.assertEqual(before[0]["id"], 1)
        after, _s = browse.rank_and_filter(posts, self.ctx(signals={"a:a2": (3, 0), "a:a1": (0, 5)}))
        self.assertEqual(after[0]["id"], 2)

    def test_feed_is_diverse_and_fresh(self):
        from dlm import browse
        prof = self.profile({"a:star": 1.0, "a:other": 0.8, "t:good": 0.5})
        posts = [self.post(i, "star", "good") for i in range(1, 6)] + [self.post(9, "other", "good")]
        ranked, _s = browse.rank_and_filter(posts, self.ctx(profile=prof))
        self.assertLess([v["id"] for v in ranked].index(9), 3, "другой автор не ждёт в конце")
        fresh, _s = browse.rank_and_filter(posts, self.ctx(profile=prof, shown={ranked[0]["id"]: 3}))
        self.assertNotEqual(fresh[0]["id"], ranked[0]["id"])

    def test_post_without_thumbnail_is_dropped_and_new_artist_marked(self):
        from dlm import browse
        prof = self.profile({"a:known": 1.0})
        ranked, stats = browse.rank_and_filter([self.post(1, "known"), self.post(2, "fresh"), self.post(3, preview="")],
                                               self.ctx(profile=prof))
        self.assertEqual({v["id"]: v["new_author"] for v in ranked}, {1: False, 2: True})
        self.assertEqual(sum(stats.values()), 1)

    def test_match_percent_uses_favorites_and_old_profile_still_works(self):
        from dlm import browse
        prof = self.profile({"a:known": 1.0})
        ranked, _s = browse.rank_and_filter([self.post(1, "known")], self.ctx(profile=prof))
        self.assertAlmostEqual(ranked[0]["match"], 100 * 2 / 3, places=3)
        del prof["fav_scores"]
        prof["bg_scores"] = [0.0, 3.0]
        ranked, _s = browse.rank_and_filter([self.post(1, "known")], self.ctx(profile=prof))
        self.assertEqual(ranked[0]["match"], 50.0)

    def test_seeds_rotate_and_skip_blocked(self):
        from dlm import browse
        weights = {f"c:ch{i}": 1.0 - i / 100 for i in range(10)}
        weights["t:bad"] = -1.0
        first = browse.taste_seeds({"weights": weights}, {"c:ch0"}, 1)
        second = browse.taste_seeds({"weights": weights}, {"c:ch0"}, 2)
        self.assertEqual(first, ["ch1", "ch2", "ch3", "ch4"])
        self.assertEqual(second, ["ch5", "ch6", "ch7", "ch8"])


class TimeMachine(unittest.TestCase):
    TODAY = date(2026, 10, 30)

    def test_months_are_spread_past_only_and_do_not_repeat(self):
        from dlm import browse
        rng = random.Random(1)
        months, used = browse.pick_months(2010, 2026, set(), rng, today=self.TODAY)
        self.assertEqual(len(set(months)), browse.TIME_MONTHS)
        self.assertEqual(months, sorted(months), "по одному из каждой части промежутка")
        self.assertGreaterEqual(int(months[-1][:4]) - int(months[0][:4]), 8)
        seen = set(used)
        for _i in range(10):
            months, used = browse.pick_months(2024, 2024, set(used), rng, n=1, today=self.TODAY)
            self.assertNotIn(months[0], seen)
            seen.add(months[0])
        months, _used = browse.pick_months(2026, 2026, set(), rng, n=20, today=self.TODAY)
        self.assertTrue(all(m < "2026-10" for m in months), "будущего и текущего месяца нет")
        self.assertEqual(len(months), 9)

    def test_a_used_up_span_starts_over(self):
        from dlm import browse
        every = {f"2020-{m:02d}" for m in range(1, 13)}
        months, used = browse.pick_months(2020, 2020, every, random.Random(1), today=self.TODAY)
        self.assertEqual(len(months), browse.TIME_MONTHS)
        self.assertEqual(sorted(used), sorted(months))

    def test_month_range_handles_february_and_december(self):
        from dlm import browse
        self.assertEqual(browse.month_range("2024-02"), (date(2024, 2, 1), date(2024, 2, 29)))
        self.assertEqual(browse.month_range("2023-12"), (date(2023, 12, 1), date(2023, 12, 31)))

    def test_requests_ask_the_right_months_and_old_posts_are_not_punished(self):
        from dlm import browse, config
        from dlm.bridges import BrowseServices
        from dlm.net import configure_session
        configure_session("free_user", "freekey")
        config.CONFIG["username"] = "free_user"
        store = browse.Store(Path(tempfile.mkdtemp()) / "b.db")
        before = len(STATE.requests)
        prof = {"weights": {"c:char_1": 1.0, "s:series_1": 0.9, "t:tag_1": 0.8, "a:artist_1": 0.7}}
        opts = {"months": ["2012-02", "2019-07"]}
        cands, _c = browse.fetch_candidates(BrowseServices(None, None), store, browse.SRC_TIME, opts, prof)
        self.assertTrue(cands)
        seen = [q for _m, _p, q in STATE.requests[before:]]
        self.assertEqual([q["date"] for q in seen if "scale" in q], ["2012-02-01", "2019-07-01"])
        self.assertTrue(all(q["scale"] == "month" for q in seen if "scale" in q))
        tagged = [q["tags"] for q in seen if "tags" in q]
        self.assertTrue(any("date:2012-02-01..2012-02-29" in t for t in tagged), tagged)
        self.assertTrue(any("date:2019-07-01..2019-07-31" in t for t in tagged), tagged)
        with self.assertRaises(ValueError):
            browse.fetch_candidates(BrowseServices(None, None), store, browse.SRC_TIME, {"months": []}, prof)
        store.close()

    def test_months_are_mixed_in_the_ranking(self):
        from dlm import browse
        def post(pid, month):
            return {"id": pid, "rating": "g", "score": 10, "fav_count": 0, "a": f"a{pid}", "c": "", "s": "", "t": "",
                    "preview": "p", "ext": "jpg", "w": 1, "h": 1, "created": f"{month}-05"}
        posts = [post(i, "2012-01") for i in range(1, 5)] + [post(i, "2019-01") for i in range(5, 9)]
        ctx = {"profile": {"weights": {"r:g": 0.1}, "bg_scores": [], "fav_scores": [0.0], "ignored": [], "fav_artists": []},
               "fav_ids": set(), "blocked": set(), "seen": {}, "ratings": {"g"}, "rng": random.Random(1), "quality": 0.0}
        ranked, _s = browse.rank_and_filter(posts, ctx)
        self.assertEqual({v["created"][:4] for v in ranked[:2]}, {"2012", "2019"})


class ForYouFeed(unittest.TestCase):
    def services(self, user, key):
        from dlm import config
        from dlm.bridges import BrowseServices
        from dlm.net import configure_session
        configure_session(user, key)
        config.CONFIG["username"] = user
        return BrowseServices(None, None)

    def test_popular_asks_for_a_full_page_and_seeds_fit_free_tier(self):
        from dlm import browse
        tmp = Path(tempfile.mkdtemp())
        sv = self.services("free_user", "freekey")
        store = browse.Store(tmp / "b.db")
        before = len(STATE.requests)
        prof = {"weights": {"c:char_1": 1.0, "s:series_1": 1.0, "t:tag_1": 1.0, "a:artist_1": 1.0}}
        cands, cached = browse.fetch_candidates(sv, store, browse.SRC_FOR_YOU, {"page": 1}, prof)
        self.assertFalse(cached)
        self.assertGreater(len(cands), 100)
        seen = [q for _m, path, q in STATE.requests[before:]]
        self.assertEqual(seen[0]["limit"], str(browse.POPULAR_PER_PAGE))
        tagged = [q["tags"] for q in seen if "tags" in q]
        self.assertTrue(any("char_1" in t for t in tagged))
        self.assertTrue(browse.fetch_candidates(sv, store, browse.SRC_FOR_YOU, {"page": 1}, prof)[1], "второй раз из кэша")
        store.close()


if __name__ == "__main__":
    unittest.main()
