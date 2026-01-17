# list_tools (BLE)

This example shows how to connect to an MCP Server over BLE using `fastmcp_transport_ble.BleTransport`, then call `list_tools` to print the available tool names.

## Prerequisites

- Python 3.10+
- A BLE peripheral running an MCP Server, exposing the expected GATT service/characteristics
- A working host BLE adapter and OS support (provided by `bleak`)

For the GATT protocol and default UUIDs, see the repo root [README.md](file:///Users/lyf/python/fastmcp-transport-ble/README.md).

## Install

From the repo root:

```bash
python -m pip install -r examples/list_tools/requirements.txt
```

If you are developing inside this repository, you can install the package in editable mode instead:

```bash
python -m pip install -e .
```

## Run

From the repo root:

```bash
python examples/list_tools/list_tools.py --help
python examples/list_tools/list_tools.py --name-hint MCP_Server_BLE
python examples/list_tools/list_tools.py --address AA:BB:CC:DD:EE:FF
```

## CLI options

- `--address`: connect to a specific BLE address (skips name-based scanning)
- `--name-hint`: substring match against the device name when scanning (default: `MCP_Server_BLE`)
- `--scan-timeout`: scan timeout in seconds (default: `5.0`)

## Output

On success it prints the tool count and each tool name, for example:

```text
Connecting to MCP Server BLE...
tools.count=3
ping
list_files
read_file
Done.
```
