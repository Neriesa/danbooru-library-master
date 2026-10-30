# -*- coding: utf-8 -*-
"""Шаг 3: сверка с Danbooru."""

import tkinter as tk


from .config import developer_mode, get_credentials
from .dialogs import preview_moves
from .mover import move_marked, plan_moves
from .net import STOP
from .site import build_results, check_against_danbooru, pending_moves, write_html_report
from .theme import BG, FG, MUTED, RED, TEAL
from .i18n import _


class Step3Mixin:
    # ---------- шаг 3 ----------
    def render_step_3(self):
        f = tk.Frame(self.main, bg=BG)
        f.pack(fill="both", expand=True)
        tk.Label(f, text=_("Сверка с Danbooru"), font=("Arial", 15, "bold"), fg=FG, bg=BG).pack(pady=6)
        tk.Label(f, text=_("Читается список вашего Избранного, затем каждый уникальный MD5 из папки проверяется "
                         "(сначала по списку, потом запросом к сайту).\nНайденные файлы не трогаются."),
                 fg=MUTED, bg=BG, font=("Arial", 10), justify="center").pack()
        opts = tk.Frame(f, bg=BG)
        opts.pack(pady=4)
        self.var_full3 = tk.BooleanVar(value=False)
        self.var_recheck = tk.BooleanVar(value=False)
        self.var_autonf = tk.BooleanVar(value=True)
        self.check(opts, self.var_full3, _("Полностью перечитать список Избранного (медленнее)"))
        self.check(opts, self.var_recheck, _("Перепроверить ранее «не найденные»"))
        self.var_dry = tk.BooleanVar(value=False)
        self.check(opts, self.var_autonf, _("Сразу переносить «не найденные» и «удалённые на сайте» в other/ "
                                          "с пометкой notFound_ / siteDeleted_ "
                                          "(можно вернуть на шаге 4)"))
        self.check(opts, self.var_dry, _("Пробный режим: ничего не переносить, а после сверки показать список "
                                       "и спросить подтверждение"))
        btns = tk.Frame(f, bg=BG)
        btns.pack(pady=6)
        self.btn_start3 = self.button(btns, _("Запустить сверку"), self.start_step3, "#009688", bold=True)
        self.button(btns, _("Остановить"), STOP.set, RED)
        self.button(btns, _("К результатам ➔"), lambda: self.goto_step(4), TEAL)
        self.make_progress_widgets(f)

    def offer_moves(self):
        """Пробный режим: показываем, что будет перенесено, и переносим только после подтверждения."""
        plan = plan_moves(self.root_path, pending_moves(self.db, self.root_path))
        if not plan:
            self.say(_("Переносить нечего."))
            return
        if not preview_moves(self.root, plan):
            self.say(_("Перенос отменён: файлы остались на местах."))
            return
        items = [(p["src"], p["category"]) for p in plan]
        self.start_worker(lambda: move_marked(self.db, self.root_path, items, self.say, self.progress),
                          lambda st: self.finish_action(st, _("Перенос завершён")))

    def start_step3(self):
        if self.busy:
            return
        user, _key = get_credentials()
        full, recheck = self.var_full3.get(), self.var_recheck.get()
        dry = self.var_dry.get()
        auto_nf = self.var_autonf.get() and not dry
        self.btn_start3.config(state="disabled")

        def work():
            check_against_danbooru(self.db, self.root_path, user, full, recheck, auto_nf,
                                   self.say, self.progress)
            if developer_mode():
                rp = write_html_report(self.svc_dir, build_results(self.db, self.root_path))
                self.say(_("HTML-отчёт сохранён: {0}").format(rp))

        def done(status):
            self.btn_start3.config(state="normal")
            self.progress(1, 1, {"ok": _("Сверка завершена. Откройте шаг 4."), "cancelled": _("Остановлено"),
                                 "error": _("Ошибка (см. журнал)")}[status])
            if dry and status == "ok":
                self.offer_moves()

        self.start_worker(work, done)
