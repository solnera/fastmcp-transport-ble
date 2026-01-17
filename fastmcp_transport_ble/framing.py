from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .constants import (
    HEADER_SEQ_MASK,
    HEADER_TYPE_MASK,
    TYPE_CONT,
    TYPE_END,
    TYPE_SINGLE,
    TYPE_START,
)


class Framer:
    def __init__(self) -> None:
        self._buf = bytearray()
        self._total = 0
        self._in_progress = False
        self._expect_seq = 0

    def feed(self, packet: bytes) -> Optional[str]:
        if not packet:
            return None

        header = packet[0]
        pkt_type = header & HEADER_TYPE_MASK
        seq_id = header & HEADER_SEQ_MASK
        payload = packet[1:]

        if pkt_type == TYPE_SINGLE:
            return payload.decode("utf-8")

        if pkt_type == TYPE_START:
            if len(payload) < 4:
                self._reset()
                return None
            self._total = int.from_bytes(payload[:4], "big")
            self._buf = bytearray(payload[4:])
            self._in_progress = True
            self._expect_seq = (seq_id + 1) & HEADER_SEQ_MASK
            return None

        if not self._in_progress:
            return None

        if seq_id != self._expect_seq:
            self._reset()
            return None
        self._expect_seq = (self._expect_seq + 1) & HEADER_SEQ_MASK

        if pkt_type == TYPE_CONT:
            self._buf.extend(payload)
            return None

        if pkt_type == TYPE_END:
            self._buf.extend(payload)
            if len(self._buf) != self._total:
                self._reset()
                return None
            msg = self._buf.decode("utf-8")
            self._reset()
            return msg

        return None

    def _reset(self) -> None:
        self._buf = bytearray()
        self._total = 0
        self._in_progress = False
        self._expect_seq = 0


@dataclass(frozen=True)
class PacketizeResult:
    packets: list[bytes]
    max_payload: int


def compute_max_payload(mtu: int, *, max_gatt_value_len: int, min_payload: int = 20) -> int:
    max_payload = int(mtu) - 3
    if max_payload < min_payload:
        max_payload = min_payload
    if max_payload > max_gatt_value_len:
        max_payload = max_gatt_value_len
    return max_payload


def packetize_json(message: str, *, max_payload: int) -> PacketizeResult:
    data = message.encode("utf-8")
    total_len = len(data)

    if total_len + 1 <= max_payload:
        pkt = bytes([TYPE_SINGLE | 0]) + data
        return PacketizeResult(packets=[pkt], max_payload=max_payload)

    if max_payload <= 5:
        raise RuntimeError("MTU too small")

    packets: list[bytes] = []
    offset = 0
    seq = 0

    start_chunk_size = max_payload - 5
    start_chunk = data[offset : offset + start_chunk_size]
    pkt = bytes([TYPE_START | (seq & HEADER_SEQ_MASK)]) + total_len.to_bytes(4, "big") + start_chunk
    packets.append(pkt)
    offset += len(start_chunk)
    seq = (seq + 1) & 0xFF

    cont_chunk_size = max_payload - 1
    while offset < total_len:
        remaining = total_len - offset
        if remaining > cont_chunk_size:
            chunk = data[offset : offset + cont_chunk_size]
            pkt = bytes([TYPE_CONT | (seq & HEADER_SEQ_MASK)]) + chunk
            packets.append(pkt)
            offset += len(chunk)
        else:
            chunk = data[offset : offset + remaining]
            pkt = bytes([TYPE_END | (seq & HEADER_SEQ_MASK)]) + chunk
            packets.append(pkt)
            offset += len(chunk)
        seq = (seq + 1) & 0xFF

    return PacketizeResult(packets=packets, max_payload=max_payload)
