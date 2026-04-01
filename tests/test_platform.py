from src.utils.platform import detect


def test_youtube():
    assert detect("https://www.youtube.com/watch?v=abc") == "youtube"
    assert detect("https://youtu.be/abc") == "youtube"

def test_instagram():
    assert detect("https://www.instagram.com/reel/abc") == "instagram"

def test_tiktok():
    assert detect("https://www.tiktok.com/@user/video/123") == "tiktok"

def test_twitter():
    assert detect("https://twitter.com/user/status/123") == "twitter"
    assert detect("https://x.com/user/status/123") == "twitter"

def test_reddit():
    assert detect("https://www.reddit.com/r/python/comments/abc") == "reddit"

def test_article_fallback():
    assert detect("https://someblog.com/post/123") == "article"
    assert detect("https://medium.com/@user/post") == "medium"
