from baboossh import User


class UsersMixin:
    """`Workspace` methods for managing `User` objects."""

    def user_add(self, name):
        """Add a :class:`User` to the workspace

        Args:
            name (str): The `User` 's username
        """

        User(name).save()

    def user_del(self, name):
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
