# -*- coding: utf-8 -*-
"""Каждая переводимая строка в коде должна иметь английский перевод с теми же подстановками."""

import ast
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "dlm"
CYR = re.compile("[А-Яа-яЁё]")


def code_keys():
    keys = {}
    for f in sorted(PKG.glob("*.py")):
        if f.name in ("i18n.py", "locale_en.py"):
            continue
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_" and n.args
                    and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)):
                if CYR.search(n.args[0].value):
                    keys.setdefault(n.args[0].value, f.name)
    return keys


def placeholders(s):
    return sorted(re.findall(r"\{\d+[^}]*\}|%d|%s", s))


class Catalog(unittest.TestCase):
    def test_every_string_is_translated(self):
        from dlm.locale_en import EN
        missing = [(f, k[:60]) for k, f in code_keys().items() if k not in EN]
        self.assertEqual(missing, [], "нет английского перевода")

    def test_no_stale_translations(self):
        from dlm.locale_en import EN
        keys = code_keys()
        stale = [k[:60] for k in EN if k not in keys]
        self.assertEqual(stale, [], "переводы без строки в коде")

    def test_placeholders_and_structure_match(self):
        from dlm.locale_en import EN
        bad = []
        for k, v in EN.items():
            if placeholders(k) != placeholders(v) or k.count("\n") != v.count("\n") or CYR.search(v):
                bad.append(k[:60])
        self.assertEqual(bad, [])

    def test_language_switch_by_environment(self):
        def run(lang):
            # На Windows вывод дочернего процесса по умолчанию не в UTF-8: задаём кодировку явно
            env = dict(os.environ, DLM_LANG=lang, PYTHONIOENCODING="utf-8")
            code = "from dlm.i18n import _, language; print(language(), _('Отмена'))"
            res = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), env=env, capture_output=True,
                                 text=True, encoding="utf-8")
            return res.stdout.strip()
        self.assertEqual(run("ru"), "ru Отмена")
        self.assertEqual(run("en"), "en Cancel")


if __name__ == "__main__":
    unittest.main()
