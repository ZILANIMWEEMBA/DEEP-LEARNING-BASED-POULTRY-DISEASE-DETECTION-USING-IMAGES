from streamlit.testing.v1 import AppTest

from pathlib import Path

ROOT_APP = str(Path(__file__).resolve().parents[1] / "frontend" / "app.py")


def test_login_and_register_render_without_errors():
    at = AppTest.from_file(ROOT_APP, default_timeout=30).run()
    assert not at.exception and "Poultry Health Support" in at.title[0].value
    at.session_state["page"] = "register"
    at.run()
    assert not at.exception


def test_unauthenticated_cannot_reach_protected_page():
    at = AppTest.from_file(ROOT_APP, default_timeout=30)
    at.session_state["page"] = "admin_dashboard"
    at.run()
    assert not at.exception and "Poultry Health Support" in at.title[0].value  # shown login instead
