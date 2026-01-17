import unittest

from fastmcp_transport_ble.constants import HEADER_SEQ_MASK, HEADER_TYPE_MASK
from fastmcp_transport_ble.framing import Framer, packetize_json


class TestFramer(unittest.TestCase):
    def test_single_packet(self) -> None:
        message = '{"jsonrpc":"2.0","id":1,"method":"ping"}'
        packetized = packetize_json(message, max_payload=512)

        self.assertEqual(len(packetized.packets), 1)

        framer = Framer()
        out = framer.feed(packetized.packets[0])
        self.assertEqual(out, message)

    def test_multi_packet_roundtrip(self) -> None:
        message = "x" * 200
        packetized = packetize_json(message, max_payload=32)

        self.assertGreater(len(packetized.packets), 1)

        framer = Framer()
        out = None
        for pkt in packetized.packets:
            out = framer.feed(pkt) or out
        self.assertEqual(out, message)

    def test_seq_mismatch_resets(self) -> None:
        message = "y" * 200
        packetized = packetize_json(message, max_payload=32)
        self.assertGreater(len(packetized.packets), 2)

        bad_packets = list(packetized.packets)
        header = bad_packets[1][0]
        pkt_type = header & HEADER_TYPE_MASK
        seq_id = header & HEADER_SEQ_MASK
        bad_seq = (seq_id + 2) & HEADER_SEQ_MASK
        bad_packets[1] = bytes([pkt_type | bad_seq]) + bad_packets[1][1:]

        framer = Framer()
        out = None
        for pkt in bad_packets:
            out = framer.feed(pkt) or out
        self.assertIsNone(out)


if __name__ == "__main__":
    unittest.main()
