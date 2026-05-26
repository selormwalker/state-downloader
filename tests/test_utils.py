import pytest
from api.info import detect_platform, fmt_duration, fmt_size

def test_detect_platform():
    assert detect_platform("https://www.youtube.com/watch?v=abc") == "YouTube"
    assert detect_platform("https://instagram.com/p/abc") == "Instagram"
    assert detect_platform("https://unknown.com") == "Social Media"

def test_fmt_duration():
    assert fmt_duration(65) == "1:05"
    assert fmt_duration(3665) == "1:01:05"
    assert fmt_duration(None) is None

def test_fmt_size():
    assert fmt_size(1024) == "1.0 KB"
    assert fmt_size(1024 * 1024) == "1.0 MB"
    assert fmt_size(None) is None
