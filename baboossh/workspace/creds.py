from baboossh import Creds, Extensions


class CredsMixin:
    """`Workspace` methods for managing `Creds` objects."""

    def creds_add(self, creds_type, stmt):
        """Add :class:`Creds` to the workspace

        Args:
            creds_type (str): The `Creds` ' object type
            stmt (`argparse.Namespace`): the rest of the command be parsed by the object
        """

        content = Extensions.auths[creds_type].fromStatement(stmt)
        new_creds = Creds(creds_type, content)
        new_creds.save()
        return new_creds.id

    def creds_show(self, creds_id):
        """Show a :class:`Creds` ' properties

        Args:
            creds_id (str): The `Creds` ' id
        """

        if creds_id[0] == '#':
            creds_id = creds_id[1:]
        creds = Creds.find_one(creds_id=creds_id)
        if creds is None:
            print("Specified creds not found")
            return
        creds.show()

    def creds_edit(self, creds_id):
        """Edit a :class:`Creds` ' properties

        Args:
            creds_id (str): The `Creds` ' id
        """

        if creds_id[0] == '#':
            creds_id = creds_id[1:]
        creds = Creds.find_one(creds_id=creds_id)
        if creds is None:
            print("Specified creds not found")
            return
        creds.edit()

    def creds_del(self, creds_id):
        """Delete a :class:`Creds` ' from the workspace

        Args:
            creds_id (str): The `Creds` ' id
        """

        if creds_id[0] == '#':
            creds_id = creds_id[1:]
        creds = Creds.find_one(creds_id=creds_id)
        if creds is None:
            print("Specified creds not found")
            return False
        if self.options["creds"] == creds:
            self.set_option("creds", None)
        self.unstore(creds.delete())
        return True
