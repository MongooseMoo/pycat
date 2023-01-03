from mcp.basepackage import PACKAGES, McpPackage
from proxy import Client


class VMooUserlist(McpPackage):
    user: str
    icons: str = ""
    fields: str = ""
    users: list = []

    datatag: str = ""


    def handle(self, name, args) -> bool:
        if name == 'dns-com-vmoo-userlist-you':
            self.user = args['nr']
        elif name == 'dns-com-vmoo-userlist':
            self.datatag = args['_data-tag']
        return super().handle(name, args)

    def handleMultiline(self, tag, key, value) -> bool:
        if tag == self.datatag:
            if key == "fields":
                self.fields = value
            elif key == 'icons':
                self.icons = value
            elif key == 'd':
                # This is the fun one.
                if value[0] == '=':
                    pass

            return True
        return super().handleMultiline(tag, key, value)

    def newClient(self, client: Client) -> None:
        authkey = client.state["mcp_key"]
        client.write(f'#$#dns-com-vmoo-userlist-you {authkey} nr: {self.user}\n')
        client.write(f'#$#dns-com-vmoo-userlist {authkey} icons*: "" fields*: "" d*: "" _data-tag: {self.datatag}\n')
        client.write(f'#$#* {self.datatag} fields: {self.fields}')
        client.write(f'#$#* {self.datatag} icons: {self.icons}')
        client.write('#$#* ' + self.datatag + ' d: ={}\n')


PACKAGES['dns-com-vmoo-userlist'] = VMooUserlist
