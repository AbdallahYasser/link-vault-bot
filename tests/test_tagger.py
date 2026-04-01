from unittest.mock import patch, MagicMock
import pytest
from src.utils.key_rotator import KeyRotator


def test_key_rotator_current():
    kr = KeyRotator(["key1", "key2"], "Test")
    assert kr.current() == "key1"


def test_key_rotator_rotate():
    kr = KeyRotator(["key1", "key2"], "Test")
    kr.rotate()
    assert kr.current() == "key2"


def test_key_rotator_exhausted():
    kr = KeyRotator(["key1"], "Test")
    with pytest.raises(RuntimeError, match="exhausted"):
        kr.rotate()


def test_key_rotator_no_keys():
    kr = KeyRotator([], "Test")
    assert not kr.has_keys()
    with pytest.raises(RuntimeError, match="No API keys"):
        kr.current()
