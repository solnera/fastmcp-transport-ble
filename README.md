# fastmcp-transport-ble

A Bluetooth Low Energy (BLE) client transport for FastMCP.

This project provides a `ClientTransport` implementation that connects to an MCP server over BLE using GATT writes (client → server) and notifications (server → client). It is intended for scenarios where you want to run an MCP server on a BLE-capable device (embedded board, mobile device, etc.) and interact with it from a Python FastMCP client.

## Features

- FastMCP `ClientTransport` implementation for BLE (powered by `bleak`)
- Device discovery by BLE address or by advertised service UUID (with optional name hint)
- JSON-RPC message framing over GATT to support payloads larger than a single characteristic write
- Small, testable core for framing/packetization logic

## Requirements

- Python 3.10+
- A BLE peripheral that implements the expected GATT service and characteristics (see “BLE GATT Protocol”)
- Supported host platform for `bleak` (macOS, Windows, Linux; details depend on your BLE adapter and OS)

## Installation

```bash
python -m pip install fastmcp-transport-ble
```

## Usage

Create a FastMCP client with the BLE transport:

```python
import asyncio
from fastmcp import Client

from fastmcp_transport_ble import BleTransport


async def main() -> None:
    transport = BleTransport(
        address=None,
        name_hint="MCP_Server_BLE",
        scan_timeout_s=10.0,
    )

    async with Client(transport) as client:
        tools = await client.list_tools()
        print([t.name for t in tools])


if __name__ == "__main__":
    asyncio.run(main())
```

### Demo script

There is a minimal demo at:

- `examples/list_tools/list_tools.py`

Run it directly:

```bash
python examples/list_tools/list_tools.py --help
python examples/list_tools/list_tools.py --name-hint MCP_Server_BLE
python examples/list_tools/list_tools.py --address AA:BB:CC:DD:EE:FF
```

## Configuration

`BleTransport` supports:

- `target`: a `BleTarget` object (or use the convenience args below)
- `address`: connect to a specific device address
- `name_hint`: substring match against device name (applies when scanning)
- `service_uuid`: service UUID used for scanning (defaults to `SERVICE_UUID`)
- `rx_char_uuid`: characteristic UUID for client writes (defaults to `RX_CHAR_UUID`)
- `tx_char_uuid`: characteristic UUID for server notifications (defaults to `TX_CHAR_UUID`)
- `scan_timeout_s`: BLE scan timeout (seconds)
- `request_mtu`: optional MTU request (best-effort; platform-dependent)
- `write_with_response`: whether to write with response (reliable, but may be slower)

## BLE GATT Protocol

This transport expects the peripheral to expose:

- A primary service UUID (default `SERVICE_UUID`)
- An RX characteristic UUID (default `RX_CHAR_UUID`) that the client writes to
- A TX characteristic UUID (default `TX_CHAR_UUID`) that the client subscribes to for notifications

Payloads are UTF-8 JSON strings. Messages are framed into packets with a 1-byte header:

- High 2 bits: packet type (`SINGLE`, `START`, `CONT`, `END`)
- Low 6 bits: sequence number (mod 64)

Packet formats:

- `SINGLE`: `[header][json-bytes...]`
- `START`: `[header][total_len:4 bytes big-endian][chunk...]`
- `CONT`:  `[header][chunk...]`
- `END`:   `[header][chunk...]`

The maximum payload per packet is derived from the negotiated MTU (minus ATT overhead), with a safety floor and a hard cap.

## Development

Run unit tests:

```bash
python -m unittest discover -s tests -p "test*.py"
```

## Compatibility notes

- BLE MTU negotiation support varies across platforms and adapters; the transport treats MTU requests as best-effort.
- GATT write/notify throughput can be limited; consider using smaller payloads and fewer concurrent requests if you see timeouts.

## Contributing

Issues and pull requests are welcome. Please include:

- OS and Python version
- BLE adapter details (if relevant)
- Peripheral firmware/protocol details (UUIDs, MTU, packet sizes)

## License

No license has been specified yet. Add a license file before publishing if you want others to legally reuse and redistribute the project.
