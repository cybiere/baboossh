from typing import Self, TYPE_CHECKING

from baboossh import Db

if TYPE_CHECKING:
    from baboossh import Endpoint

__all__ = ["Tag"]

class Tag():

    """A tag to apply on endpoints to target them as groups.

    Attributes:
        name (str): the tag name
        endpoints ([:class:`.Endpoint`,...]): the Endpoints tagged with the tag.
    """

    def __init__(self, name: str) -> None:
        from baboossh import Endpoint
        self.name = name
        self.endpoints = []
        cursor = Db.get().cursor()
        for row in cursor.execute('SELECT endpoint FROM tags WHERE name=?', (self.name, )):
            self.endpoints.append(Endpoint.find_one(endpoint_id=row[0]))

    def delete(self) -> None:
        """Delete a Tag from the :class:`.Workspace`"""

        for endpoint in self.endpoints:
            if endpoint is not None:
                endpoint.untag(self.name)

    @classmethod
    def find_all(cls, endpoint: "Endpoint | None" = None) -> list[Self]:
        """Find all Tags corresponding to criteria

        Args:
            endpoint (:class:`.Endpoint`):
                the `Endpoint` the tags are in

        Returns:
            A list of all `Tag` s in the :class:`.Workspace` matching the criteria
        """

        ret = []
        cursor = Db.get().cursor()
        if endpoint is None:
            req = cursor.execute('SELECT DISTINCT(name) FROM tags')
        else:
            req = cursor.execute('SELECT DISTINCT(name) FROM tags WHERE endpoint=?', (endpoint.id,))
        for row in req:
            ret.append(cls(row[0]))
        cursor.close()
        return ret

    @classmethod
    def find_one(cls, name: str | None = None) -> Self | None:
        """Find a tag matching the criteria

        Args:
            name (str): the username to search

        Returns:
            A single `Tag` or `None`.
        """

        if name is None:
            return None

        cursor = Db.get().cursor()
        cursor.execute('''SELECT name FROM tags WHERE name=?''', (name, ))
        row = cursor.fetchone()
        cursor.close()
        if row is None:
            return None
        return cls(row[0])

    def __str__(self) -> str:
        return "!"+self.name
