from registers import register_auth

@register_auth("password")
def password_auth(credentials):
    print(credentials)

