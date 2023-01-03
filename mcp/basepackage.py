from proxy import Client

PACKAGES = {}

class McpPackage:
    def __init__(self, mud) -> None:
        self.mud = mud

    def handle(self, name, args) -> bool:
        return False

    def handleMultiline(self, tag, key, value) -> bool:
        return False

    def newClient(self, client: Client) -> None:
        pass
