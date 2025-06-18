from io import StringIO

from django.core.management import call_command


def test_passes_django_check_command():
    out = StringIO()
    err = StringIO()
    result = call_command("check", stdout=out, stderr=err)
    assert result is None
    assert out.getvalue() == "System check identified no issues (0 silenced).\n"
    assert err.getvalue() == ""
