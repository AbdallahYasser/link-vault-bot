from src.services.duplicates import find_smart_duplicates, group_all_duplicates

LINKS = [
    {"id": 1, "title": "React Hooks Deep Dive", "description": "Learn about hooks", "tag": "dev/react", "url": "https://a.com", "platform": "article", "status": "unread"},
    {"id": 2, "title": "CSS Grid Tutorial", "description": "Master CSS grid layout", "tag": "dev/css", "url": "https://b.com", "platform": "article", "status": "unread"},
    {"id": 3, "title": "Python for Beginners", "description": "Introduction to Python", "tag": "dev/python", "url": "https://c.com", "platform": "article", "status": "unread"},
]


def test_find_smart_dup_same_title():
    result = find_smart_duplicates("React Hooks Deep Dive", "About hooks in React", LINKS)
    assert any(l["id"] == 1 for l in result)


def test_find_smart_dup_no_match():
    result = find_smart_duplicates("Cooking Pasta", "Italian recipes", LINKS)
    assert len(result) == 0


def test_group_all_duplicates_finds_pair():
    links = [
        {"id": 1, "title": "React Hooks Deep Dive", "description": "Learn hooks", "url": "https://a.com", "tag": "dev", "platform": "article", "status": "unread"},
        {"id": 2, "title": "React Hooks Deep Dive", "description": "Learn hooks in React", "url": "https://b.com", "tag": "frontend", "platform": "youtube", "status": "unread"},
        {"id": 3, "title": "Pasta Recipes", "description": "Italian food", "url": "https://c.com", "tag": "food", "platform": "article", "status": "unread"},
    ]
    groups = group_all_duplicates(links)
    assert len(groups) == 1
    ids = {l["id"] for l in groups[0]}
    assert ids == {1, 2}


def test_group_all_no_duplicates():
    assert group_all_duplicates(LINKS) == []
