import pytest
from server.app import verify_password


def test_verify_password():
    " Tests whether the function returns a correct password for predefined user account "
    username = "TEST"
    password = "123456"
    assert "TEST" == verify_password(username, password)


