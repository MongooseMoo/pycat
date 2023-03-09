import moo_grammar
from mcp.basepackage import PACKAGES, McpPackage
from proxy import Client


class VMooUserlist(McpPackage):
    user: str
    icons: str = ""
    fields: str = ""
    users: list = []
    menu: str = ""
    afk = moo_grammar.MooList()
    away = moo_grammar.MooList()

    datatag: str = ""


    def handle(self, name, args) -> bool:
        if name == 'dns-com-vmoo-userlist-you':
            self.user = args['nr']
            return True
        elif name == 'dns-com-vmoo-userlist':
            self.datatag = args['_data-tag']
            return True
        elif name == "dns-com-vmoo-userlist-menu":
            self.menu = args['menu']
            return True
        return super().handle(name, args)

    def handleMultiline(self, tag, key, value) -> bool:
        # print((tag, key, value))
        if tag == self.datatag:
            # print('userlist')
            if key == "fields":
                self.fields = value
            elif key == 'icons':
                self.icons = value
            elif key == 'd':
                # This is the fun one.
                val = moo_grammar.parse_value(value[1:])
                match value[0]:
                    case '=':
                        self.users = val
                    case '-':
                        # user offline
                        u = [u for u in self.users if u[0] == val][0]
                        self.users.remove(u)
                    case '+':
                        # user online
                        self.users.append(val)
                    case '>':
                        for v in val:
                            self.afk.remove(v)
                    case '<':
                        for v in val:
                            self.afk.append(v)
                    case '[':
                        for v in val:
                            self.away.append(v)
                    case ']':
                        for v in val:
                            self.away.remove(v)
                    case _:
                        print('unknown d: ' + repr(value))

            return True
        return super().handleMultiline(tag, key, value)

    def newClient(self, client: Client) -> None:
        authkey = client.state["mcp_key"]
        client.write(f'#$#dns-com-vmoo-userlist-you {authkey} nr: {self.user}\n')
        client.write(f'#$#dns-com-vmoo-userlist {authkey} icons*: "" fields*: "" d*: "" _data-tag: {self.datatag}\n')
        client.write(f'#$#* {self.datatag} fields: {self.fields}\n')
        client.write(f'#$#* {self.datatag} icons: {self.icons}\n')
        client.write('#$#* ' + self.datatag + f' d: ={self.users}\n')
        client.write('#$#* ' + self.datatag + f' d: <{self.afk}\n')
        client.write('#$#* ' + self.datatag + f' d: [{self.away}\n')



PACKAGES['dns-com-vmoo-userlist'] = VMooUserlist
