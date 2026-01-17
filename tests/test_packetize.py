import unittest

from fastmcp_transport_ble.constants import (
    HEADER_SEQ_MASK,
    TYPE_CONT,
    TYPE_END,
    TYPE_SINGLE,
    TYPE_START,
)
from fastmcp_transport_ble.framing import compute_max_payload, packetize_json


class TestPacketize(unittest.TestCase):
    def test_compute_max_payload_bounds(self) -> None:
        self.assertEqual(compute_max_payload(23, max_gatt_value_len=512), 20)
        self.assertEqual(compute_max_payload(200, max_gatt_value_len=64), 64)

    def test_packet_lengths_never_exceed_max_payload(self) -> None:
        message = "z" * 1000
        max_payload = 64
        packetized = packetize_json(message, max_payload=max_payload)

        self.assertGreater(len(packetized.packets), 1)
        for pkt in packetized.packets:
            self.assertLessEqual(len(pkt), max_payload)

    def test_packet_types_and_seq_cycle(self) -> None:
        message = "a" * 200
        packetized = packetize_json(message, max_payload=32)
        packets = packetized.packets

        first = packets[0][0] & 0xC0
        self.assertEqual(first, TYPE_START)

        last = packets[-1][0] & 0xC0
        self.assertEqual(last, TYPE_END)

        for pkt in packets[1:-1]:
            self.assertEqual(pkt[0] & 0xC0, TYPE_CONT)

        seqs = [(pkt[0] & HEADER_SEQ_MASK) for pkt in packets]
        expected = [(seqs[0] + i) & HEADER_SEQ_MASK for i in range(len(seqs))]
        self.assertEqual(seqs, expected)

    def test_single_packet_type(self) -> None:
        message = "hi"
        packetized = packetize_json(message, max_payload=10)
        self.assertEqual(len(packetized.packets), 1)
        self.assertEqual(packetized.packets[0][0] & 0xC0, TYPE_SINGLE)


if __name__ == "__main__":
    unittest.main()
