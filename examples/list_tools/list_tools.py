import argparse
import asyncio

from fastmcp import Client
from fastmcp_transport_ble import BleTransport


async def main() -> None:
    print("Connecting to MCP Server BLE...")
    p = argparse.ArgumentParser()
    p.add_argument("--address", default=None)
    p.add_argument("--name-hint", default="MCP_Server_BLE")
    p.add_argument("--scan-timeout", type=float, default=5.0)
    args = p.parse_args()

    transport = BleTransport(address=args.address, name_hint=args.name_hint, scan_timeout_s=args.scan_timeout)

    async with Client(transport) as client:
        tools = await client.list_tools()
        print(f"tools.count={len(tools)}")
        for tool in tools:
            print(tool.name)

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
