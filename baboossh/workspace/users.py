from typing import TYPE_CHECKING, Protocol

from baboossh import User

if TYPE_CHECKING:
    class _Workspace(Protocol):
        options: dict[str, object]
        def unstore(self, data: dict[str, list[str]]) -> None: ...
        def set_option(self, option: str, value: str | None) -> None: ...

__all__ = ["UsersMixin"]


class UsersMixin:
    """`Workspace` methods for managing `User` objects."""

    def user_add(self: "_Workspace", name: str) -> None:
        """Add a :class:`User` to the workspace

        Args:
            name (str): The `User` 's username
        """

        User(name).save()

    def user_del(self: "_Workspace", name: str) -> bool:
        """Remove a :class:`User` from the workspace

        Args:
            name (str): The `User` 's username
        """

        user = User.find_one(name=name)
        if user is None:
            print("Could not find user.")
            return False
        if self.options["user"] == user:
            self.set_option("user", None)
        self.unstore(user.delete())
        return True
