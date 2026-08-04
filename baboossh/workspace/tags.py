from baboossh import Tag

__all__ = ["TagsMixin"]


class TagsMixin:
    """`Workspace` methods for managing `Tag` objects."""

    def tag_show(self, name: str) -> None:
        if name[0] == "!":
            name = name[1:]
        tag = Tag.find_one(name=name)
        if tag is None:
            print("No tag matching "+name)
            return
        print("Tag "+name+" members :")
        for endpoint in tag.endpoints:
            print(" - "+str(endpoint))

    def tag_del(self, name: str) -> None:
        if name[0] == "!":
            name = name[1:]
        tag = Tag.find_one(name=name)
        if tag is None:
            print("No tag matching "+name)
            return
        tag.delete()
        print("Tag "+name+" deleted")
