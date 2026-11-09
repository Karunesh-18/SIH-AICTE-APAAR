import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_JWT_SECRET, Settings


def test_default_secret_is_allowed_in_demo_mode():
    assert Settings(demo_mode=True, jwt_secret=DEFAULT_JWT_SECRET).demo_mode is True


def test_default_secret_is_refused_outside_demo_mode():
    with pytest.raises(ValidationError):
        Settings(demo_mode=False, jwt_secret=DEFAULT_JWT_SECRET)


def test_short_secret_is_refused_outside_demo_mode():
    with pytest.raises(ValidationError):
        Settings(demo_mode=False, jwt_secret="short")


def test_real_secret_is_accepted_outside_demo_mode():
    assert Settings(demo_mode=False, jwt_secret="x" * 40).demo_mode is False
