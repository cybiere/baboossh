from baboossh import Endpoint, Tag


def make_tagged_endpoint(tagname="mytag", ip="1.2.3.4", port="22"):
    endpoint = Endpoint(ip, port)
    endpoint.save()
    endpoint.tag(tagname)
    return endpoint


def test_find_one_missing_tag_returns_none(workspace):
    assert Tag.find_one(name="doesnotexist") is None


def test_find_one_returns_matching_tag(workspace):
    make_tagged_endpoint("mytag")
    tag = Tag.find_one(name="mytag")
    assert tag is not None
    assert tag.name == "mytag"


def test_find_all_returns_all_tags(workspace):
    make_tagged_endpoint("tag1", ip="1.1.1.1")
    make_tagged_endpoint("tag2", ip="2.2.2.2")
    tags = Tag.find_all()
    names = sorted(tag.name for tag in tags)
    assert names == ["tag1", "tag2"]


def test_find_all_filtered_by_endpoint(workspace):
    endpoint1 = make_tagged_endpoint("tag1", ip="1.1.1.1")
    make_tagged_endpoint("tag2", ip="2.2.2.2")
    tags = Tag.find_all(endpoint=endpoint1)
    names = [tag.name for tag in tags]
    assert names == ["tag1"]


def test_delete_removes_tag_from_endpoint(workspace):
    endpoint = make_tagged_endpoint("mytag")
    tag = Tag.find_one(name="mytag")
    tag.delete()
    assert Tag.find_one(name="mytag") is None
    assert "mytag" not in endpoint.tags
