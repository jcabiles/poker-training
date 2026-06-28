import subprocess
import sys


def test_domain_has_no_web_or_db_imports():
    """The pure domain core must not pull in web/DB frameworks.

    Run in a fresh subprocess so sys.modules isn't polluted by other tests.
    """
    code = (
        "import importlib, sys\n"
        "mods = ['app.domain.spot','app.domain.action','app.domain.evaluation',"
        "'app.domain.leaks','app.domain.srs','app.domain.content','app.domain.providers',"
        "'app.domain.scenarios','app.domain.grading','app.domain.hand_rank','app.domain.archetypes']\n"
        "for m in mods:\n"
        "    importlib.import_module(m)\n"
        "banned = [b for b in ('fastapi','starlette','sqlmodel','sqlalchemy') if b in sys.modules]\n"
        "assert not banned, 'domain imported: ' + repr(banned)\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
