import asyncio
import contextlib
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Unpack

import anyio
import mcp.types as types
from bleak import BleakClient, BleakScanner
from mcp import ClientSession
from mcp.shared.message import SessionMessage

from fastmcp.client.transports import ClientTransport, SessionKwargs

from .constants import MAX_GATT_VALUE_LEN, RX_CHAR_UUID, SERVICE_UUID, TX_CHAR_UUID
from .framing import Framer, compute_max_payload, packetize_json


@dataclass(frozen=True)
class BleTarget:
    address: str | None = None
    name_hint: str | None = None
    service_uuid: str = SERVICE_UUID


class BleTransport(ClientTransport):
    def __init__(
        self,
        *,
        target: BleTarget | None = None,
        address: str | None = None,
        name_hint: str | None = None,
        service_uuid: str = SERVICE_UUID,
        rx_char_uuid: str = RX_CHAR_UUID,
        tx_char_uuid: str = TX_CHAR_UUID,
        scan_timeout_s: float = 10.0,
        request_mtu: int | None = None,
        write_with_response: bool = True,
    ) -> None:
        if target is None:
            target = BleTarget(address=address, name_hint=name_hint, service_uuid=service_uuid)
        self._target = target
        self._rx_char_uuid = rx_char_uuid
        self._tx_char_uuid = tx_char_uuid
        self._scan_timeout_s = scan_timeout_s
        self._request_mtu = request_mtu
        self._write_with_response = write_with_response

    @contextlib.asynccontextmanager
    async def connect_session(self, **session_kwargs: Unpack[SessionKwargs]) -> AsyncIterator[ClientSession]:
        read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
        write_stream, write_stream_reader = anyio.create_memory_object_stream(0)
        packet_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=256)

        client: BleakClient | None = None
        framer = Framer()
        closing = False

        loop = asyncio.get_running_loop()

        def on_notify(_sender: int, data: bytearray) -> None:
            if closing:
                return
            b = bytes(data)

            def _push() -> None:
                try:
                    packet_queue.put_nowait(b)
                except asyncio.QueueFull:
                    return

            try:
                loop.call_soon_threadsafe(_push)
            except RuntimeError:
                return

        async def reader_task() -> None:
            while True:
                pkt = await packet_queue.get()
                try:
                    msg = framer.feed(pkt)
                    if msg is None:
                        continue
                    parsed = types.JSONRPCMessage.model_validate_json(msg)
                    await read_stream_writer.send(SessionMessage(parsed))
                except Exception as exc:
                    with contextlib.suppress(Exception):
                        await read_stream_writer.send(exc)

        async def writer_task() -> None:
            assert client is not None
            async with write_stream_reader:
                async for session_message in write_stream_reader:
                    json = session_message.message.model_dump_json(by_alias=True, exclude_none=True)
                    try:
                        await self._send_json(client, json)
                    except Exception as exc:
                        with contextlib.suppress(Exception):
                            await read_stream_writer.send(exc)
                        return

        try:
            device = await self._discover_device()
            async with BleakClient(device) as bleak_client:
                client = bleak_client

                if self._request_mtu is not None:
                    with contextlib.suppress(Exception):
                        await client.request_mtu(self._request_mtu)

                await client.start_notify(self._tx_char_uuid, on_notify)
                try:
                    async with anyio.create_task_group() as tg:
                        tg.start_soon(reader_task)
                        tg.start_soon(writer_task)
                        async with ClientSession(read_stream, write_stream, **session_kwargs) as session:
                            yield session
                finally:
                    closing = True
                    with contextlib.suppress(Exception):
                        await client.stop_notify(self._tx_char_uuid)
                    await asyncio.sleep(0.05)
        finally:
            with contextlib.suppress(Exception):
                await read_stream.aclose()
            with contextlib.suppress(Exception):
                await write_stream.aclose()
            with contextlib.suppress(Exception):
                await read_stream_writer.aclose()
            with contextlib.suppress(Exception):
                await write_stream_reader.aclose()
            closing = True

    async def _discover_device(self):
        if self._target.address:
            dev = await BleakScanner.find_device_by_address(self._target.address, timeout=self._scan_timeout_s)
            if dev is None:
                raise RuntimeError("BLE device not found by address")
            return dev

        found = await BleakScanner.discover(return_adv=True, timeout=self._scan_timeout_s)
        service_uuid = self._target.service_uuid.lower()
        for d, ad in found.values():
            svc = [u.lower() for u in (ad.service_uuids or [])]
            if service_uuid in svc:
                if self._target.name_hint and self._target.name_hint not in (d.name or ""):
                    continue
                return d
        raise RuntimeError("BLE device not found by service UUID")

    async def _send_json(self, client: BleakClient, message: str) -> None:
        mtu = getattr(client, "mtu_size", 23)
        max_payload = compute_max_payload(mtu, max_gatt_value_len=MAX_GATT_VALUE_LEN)
        packetized = packetize_json(message, max_payload=max_payload)

        resp = self._write_with_response
        for pkt in packetized.packets:
            await client.write_gatt_char(self._rx_char_uuid, pkt, response=resp)
