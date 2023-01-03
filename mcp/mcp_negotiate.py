from mcp.basepackage import PACKAGES, McpPackage
from proxy import Client


class Negotiate(McpPackage):
    negotiated = False
    server_packages: list[tuple[str, str, str]] = []

    def handle(self, name: str, args: dict[str, str]) -> bool:
        if name == 'mcp-negotiate-can' and not self.negotiated:
            package = args['package']
            min = args['min-version']
            max = args['max-version']
            self.server_packages.append((package, min, max))
            if package == 'mcp-negotiate':
                pass  # duh
            elif (imp := PACKAGES.get(package)):
                self.mud.mcp.append(imp(self.mud))
            else:
                print(f'Unsupported MCP package {package}')
            return True
        elif name == 'mcp-negotiate-end':
            self.negotiated = True

        return False

    def newClient(self, client: Client) -> None:
        authkey = client.state["mcp_key"]
        for p in self.server_packages:
            client.write(f'#$#mcp-negotiate-can {authkey} package: {p[0]} min-version: {p[1]} max-version: {p[2]}\n')
        client.write(f'#$#mcp-negotiate-end {authkey}\n')
