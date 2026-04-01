from src.utils.url_normalizer import normalize


def test_youtube_short():
    assert normalize("https://youtu.be/dQw4w9WgXcQ") == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

def test_youtube_watch_strips_extras():
    url = "https://www.youtube.com/watch?v=abc123&utm_source=share&feature=web"
    assert normalize(url) == "https://www.youtube.com/watch?v=abc123"

def test_strips_utm():
    url = "https://example.com/article?utm_source=twitter&utm_medium=social"
    assert "utm_source" not in normalize(url)

def test_strips_trailing_slash():
    assert normalize("https://example.com/article/") == "https://example.com/article"

def test_www_removed():
    assert "www." not in normalize("https://www.example.com/page")

def test_same_url_normalizes_equal():
    a = normalize("https://youtu.be/abc123")
    b = normalize("https://www.youtube.com/watch?v=abc123&utm_source=share")
    assert a == b
