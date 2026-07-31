from baboossh import Connection, Creds, Endpoint, Extensions, Tag, User


class OptionsMixin:
    """`Workspace` methods for managing the active target options."""

    def set_option(self, option, value):
        """Set an option for the `Workspace`

        Args:
            option (str): the option to set
            value (str): the new value
        """

        if option == 'connection':
            if value is None:
                self.options['endpoint'] = None
                self.options['user'] = None
                self.options['creds'] = None

                print("endpoint => "+str(self.options['endpoint']))
                print("user => "+str(self.options['user']))
                print("creds => "+str(self.options['creds']))

            elif '@' not in value or ':' not in value:
                return
            connection = Connection.from_target(value)
            if connection is None:
                return
            self.options['endpoint'] = connection.endpoint
            self.options['user'] = connection.user
            self.options['creds'] = connection.creds

            print("endpoint => "+str(self.options['endpoint']))
            print("user => "+str(self.options['user']))
            print("creds => "+str(self.options['creds']))
            return

        if not option in list(self.options.keys()):
            raise ValueError(option+" isn't a valid option.")

        if value is not None:
            value = value.strip()
            if option == "endpoint":
                if value[0] == "!":
                    value = Tag(value[1:])
                else:
                    endpoint = Endpoint.find_one(ip_port=value)
                    if endpoint is None:
                        raise ValueError
                    value = endpoint
            elif option == "user":
                user = User.find_one(name=value)
                if user is None:
                    raise ValueError
                value = user
            elif option == "creds":
                if value[0] == '#':
                    creds_id = value[1:]
                else:
                    creds_id = value
                creds = Creds.find_one(creds_id=creds_id)
                if creds is None:
                    raise ValueError
                value = creds
            elif option == "payload":
                value = Extensions.payloads[value]
            self.options[option] = value
        else:
            self.options[option] = None
        print(option+" => "+str(self.options[option]))
