# -*- coding: utf-8 -*-
"""Окна программы: открываются без ошибок, в английском режиме в них нет русского текста. Пропускается без дисплея."""

import re
import tempfile
import time
import unittest
from pathlib import Path

try:
    import tkinter as tk
    _root = tk.Tk()
    _root.destroy()
    HAVE_DISPLAY = True
except Exception:
    HAVE_DISPLAY = False

from . import helpers

CYR = re.compile("[А-Яа-яЁё]")
ALLOWED = {"Язык / Language:"}          # единственная намеренно двуязычная подпись


def texts(widget):
    out = []
    for c in widget.winfo_children():
        for opt in ("text", "title"):
            try:
                out.append(str(c.cget(opt)))
            except tk.TclError:
                pass
        if c.winfo_class() == "Treeview":
            try:
                out += [str(c.heading(col)["text"]) for col in c["columns"]]
            except Exception:
                pass
        out += texts(c)
    return out


def pump(root, sec=1.2):
    end = time.time() + sec
    while time.time() < end:
        root.update()
        time.sleep(0.02)


@unittest.skipUnless(HAVE_DISPLAY, "нет дисплея (на Linux запустите через xvfb-run -a)")
class Windows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def english_clean(self, widget, where):
        from dlm.i18n import language
        if language() != "en":
            return
        leftovers = [t for t in texts(widget) if CYR.search(t) and t not in ALLOWED]
        self.assertEqual(leftovers, [], f"русский текст в английском режиме: {where}")

    def test_main_window_steps(self):
        from dlm import ui
        from PIL import Image
        folder = Path(tempfile.mkdtemp())
        Image.new("RGB", (32, 32), (9, 9, 9)).save(folder / "a.png")
        top = tk.Toplevel(self.root)
        app = ui.App(top)
        app.set_root(folder)
        from dlm import config
        self.addCleanup(config.set_developer_mode, False)
        for dev in (False, True):
            config.set_developer_mode(dev)
            for n in range(1, 7):
                app.show_step(n)
                top.update()
                self.english_clean(app.main, f"шаг {n}, разработчик: {dev}")
        top.destroy()

    def test_credentials_about_and_preview(self):
        from dlm import dialogs
        d = dialogs.CredentialsDialog(self.root, first_run=True)
        self.root.update()
        self.english_clean(d.win, "первый запуск")
        d.var_user.set("free_user")
        d.var_key.set("freekey")
        d.start_check()
        pump(self.root)
        self.assertEqual(str(d.btn_save["state"]), "normal")
        d.save()
        self.assertTrue(d.saved)
        a = dialogs.AboutDialog(self.root, "/tmp")
        self.root.update()
        self.english_clean(a.win, "О программе")
        a.win.destroy()
        plan = [{"src": "/x/a.jpg", "new_name": "notFound_a.jpg", "category": "not_found", "clash": True}]
        p = dialogs.MovePreview(self.root, plan)
        self.root.update()
        self.english_clean(p.win, "предпросмотр")
        p.win.destroy()

    def test_wrong_key_is_reported(self):
        from dlm import dialogs
        d = dialogs.CredentialsDialog(self.root, first_run=True)
        d.var_user.set("free_user")
        d.var_key.set("nope")
        d.start_check()
        pump(self.root)
        self.assertEqual(str(d.btn_save["state"]), "disabled")
        d.cancel()

    def test_browse_window_opens(self):
        from dlm import browse
        from dlm.bridges import BrowseServices
        from dlm.config import CONFIG
        from dlm.net import configure_session
        configure_session("gold_user", "goldkey")
        CONFIG["username"] = "gold_user"
        win = tk.Toplevel(self.root)
        bw = browse.BrowseWindow(win, BrowseServices(None, None))
        pump(win, 1.5)                                  # лента загружается сама, без нажатий
        self.assertTrue(bw.visible)
        self.english_clean(win, "лента")
        bw.close()

    def test_developer_switch_hides_service_ui(self):
        """По умолчанию служебного не видно; переключатель в «О программе» показывает его без перезапуска."""
        from dlm import config, dialogs, ui
        from dlm.i18n import _
        config.set_developer_mode(False)
        self.addCleanup(config.set_developer_mode, False)
        folder = Path(tempfile.mkdtemp())
        top = tk.Toplevel(self.root)
        app = ui.App(top)
        app.set_root(folder)
        app.show_step(4)
        top.update()
        self.assertNotIn(_("HTML-отчёт"), texts(app.main))
        about = dialogs.AboutDialog(self.root, "/tmp")
        self.root.update()
        self.assertFalse(about.dev_box.winfo_manager())
        self.english_clean(about.win, "О программе")
        about.switch.toggle()
        self.assertTrue(config.developer_mode())
        self.assertTrue(about.dev_box.winfo_manager())
        self.english_clean(about.win, "О программе, разработчик")
        pump(top, 0.3)
        self.assertIn(_("HTML-отчёт"), texts(app.main), "шаг перерисован сам")
        about.win.destroy()
        top.destroy()

    def test_step3_writes_report_only_for_developer(self):
        from dlm import config, ui
        from dlm.net import configure_session
        configure_session("gold_user", "goldkey")
        config.set_developer_mode(False)
        folder = Path(tempfile.mkdtemp())
        helpers.make_image(folder / "x.png", 77)
        top = tk.Toplevel(self.root)
        app = ui.App(top)
        app.set_root(folder)
        app.show_step(3)
        app.var_autonf.set(False)
        app.start_step3()
        pump(top, 3)
        self.assertFalse((app.svc_dir / "report.html").exists())
        top.destroy()

    def test_time_machine_in_window(self):
        from dlm import browse, config
        from dlm.bridges import BrowseServices
        from dlm.i18n import _
        from dlm.net import configure_session
        configure_session("gold_user", "goldkey")
        config.CONFIG["username"] = "gold_user"
        win = tk.Toplevel(self.root)
        bw = browse.BrowseWindow(win, BrowseServices(None, None), auto_load=False)
        bw.var_source.set(browse.SRC_TIME)
        bw.spin_from.delete(0, "end")
        bw.spin_from.insert(0, "2015")
        bw.spin_to.delete(0, "end")
        bw.spin_to.insert(0, "2012")                    # перепутанные годы не ломают выбор
        bw.on_source_changed()
        self.assertTrue(bw.spin_from.winfo_manager())
        pump(win, 1.5)
        self.assertTrue(bw.visible)
        self.assertTrue(all("2012" <= m[:4] <= "2015" for m in bw.months), bw.months)
        self.assertIn(_("Месяцы: {0}").format(", ".join(sorted(bw.months))), bw.lbl_status.cget("text"))
        first = bw.months
        bw.start_load(False)
        pump(win, 1.5)
        self.assertFalse(set(first) & set(bw.months), "новая загрузка - новые месяцы")
        self.assertEqual(bw.store.get_meta("time_years"), "2012,2015")
        self.english_clean(win, "машина времени")
        bw.close()

    def test_browse_feed_flow(self):
        """Показать ещё дописывает в конец, пропуск отменяется, режим разработчика меняет строку состояния."""
        from dlm import browse, config
        from dlm.bridges import BrowseServices
        from dlm.i18n import _
        from dlm.net import configure_session
        configure_session("gold_user", "goldkey")
        config.CONFIG["username"] = "gold_user"
        config.set_developer_mode(False)
        self.addCleanup(config.set_developer_mode, False)
        win = tk.Toplevel(self.root)
        bw = browse.BrowseWindow(win, BrowseServices(None, None), auto_load=False)
        bw.var_source.set(browse.SRC_POPULAR)
        bw.start_load(True)
        pump(win, 1.5)
        first = [v["id"] for v in bw.visible]
        self.assertTrue(first)
        self.assertNotIn(_("запросов").lower(), bw.lbl_status.cget("text").lower())
        bw.start_load(True, more=True)
        pump(win, 1.5)
        self.assertEqual([v["id"] for v in bw.visible][:len(first)], first, "экран не перемешан")
        self.assertGreater(len(bw.cands), 100)
        pid = first[0]
        bw.on_click(pid)
        bw.act_skip()
        self.assertNotIn(pid, [v["id"] for v in bw.visible])
        self.assertTrue(bw.store.signals())
        bw.act_undo()
        self.assertIn(pid, [v["id"] for v in bw.visible])
        self.assertEqual(bw.store.seen_map().get(pid), None)
        self.assertTrue(all(neg == 0 for _pos, neg in bw.store.signals().values()), "обучение тоже отменено")
        config.set_developer_mode(True)
        pump(win, 0.3)
        self.assertTrue(bw.btn_refresh.winfo_manager())
        bw.close()

    def test_random_viewer_opens(self):
        from dlm import random_viewer
        folder = Path(tempfile.mkdtemp())
        helpers.make_image(folder / "1.png", 1)
        helpers.make_image(folder / "2.png", 2)
        win = tk.Toplevel(self.root)
        random_viewer.Viewer(win, folder, None)
        pump(win, 0.8)
        self.english_clean(win, "просмотр")
        win.destroy()

    def test_dry_run_dialog_flow_in_step3(self):
        """Пробный режим в окне: после сверки показывается список, файлы не трогаются до подтверждения."""
        from dlm import ui, ui_step3
        from dlm.net import configure_session
        configure_session("gold_user", "goldkey")
        folder = Path(tempfile.mkdtemp())
        helpers.make_image(folder / "ghost.png", 99)
        top = tk.Toplevel(self.root)
        app = ui.App(top)
        app.set_root(folder)
        app.show_step(3)
        top.update()
        shown = []
        original = ui_step3.preview_moves
        ui_step3.preview_moves = lambda parent, plan, title=None: shown.append(plan) or False
        try:
            app.var_dry.set(True)
            app.var_autonf.set(True)            # пробный режим сильнее «переносить сразу»
            app.start_step3()
            pump(top, 4)
        finally:
            ui_step3.preview_moves = original
        self.assertEqual(len(shown), 1)
        self.assertEqual(len(shown[0]), 1)
        self.assertTrue((folder / "ghost.png").exists(), "после отказа файл на месте")
        top.destroy()


if __name__ == "__main__":
    unittest.main()
