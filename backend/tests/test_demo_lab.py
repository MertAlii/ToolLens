import asyncio
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import demo_lab


class DemoPolicyTests(unittest.TestCase):
    def test_risky_server_never_falls_back_to_host(self):
        with patch.object(demo_lab, "_docker_ready", return_value={"installed": False, "running": False, "image_ready": False}):
            with self.assertRaises(demo_lab.LabError):
                demo_lab._launch("calculator_risky")
            with self.assertRaises(demo_lab.LabError):
                asyncio.run(demo_lab.start_demo("documents_risky"))

    def test_docker_policy_has_no_network_or_host_credentials(self):
        with patch.object(demo_lab, "_docker_ready", return_value={"installed": True, "running": True, "image_ready": True}), patch.object(demo_lab.shutil, "which", return_value="docker"):
            command, args, env, name = demo_lab._launch("documents_risky")
        self.assertEqual(command, "docker")
        self.assertEqual(args[args.index("--network") + 1], "none")
        self.assertIn("--read-only", args)
        self.assertEqual(env, {})
        self.assertNotIn("--privileged", args)
        self.assertNotIn("docker.sock", " ".join(args))

    def test_stopped_session_cannot_be_called(self):
        with self.assertRaises(demo_lab.LabError):
            asyncio.run(demo_lab.call_tool("calculator_fixed", "calculate", {"expression": "2+2"}))


@unittest.skipUnless(importlib.util.find_spec("mcp"), "MCP SDK kurulumu gerekli")
class RealMcpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="toollens-mcp-test-")
        self.patch = patch.object(demo_lab, "DATA", Path(self.directory.name))
        self.patch.start()

    async def asyncTearDown(self):
        await demo_lab.close_all()
        self.patch.stop()
        self.directory.cleanup()

    async def test_calculator_real_handshake_and_call(self):
        session = await demo_lab.start_demo("calculator_fixed")
        self.assertEqual(session["status"], "running")
        tools = await demo_lab.list_tools("calculator_fixed")
        self.assertIn("calculate", [tool["name"] for tool in tools])
        result = await demo_lab.call_tool("calculator_fixed", "calculate", {"expression": "2 + 3 * 4"})
        self.assertFalse(result["is_error"])
        self.assertIn("14", result["result"]["content"][0]["text"])
        rejected = await demo_lab.call_tool("calculator_fixed", "calculate", {"expression": "abs(-4)"})
        self.assertTrue(rejected["is_error"])

    async def test_notes_actual_user_text_persists_and_traversal_rejected(self):
        await demo_lab.start_demo("documents_fixed")
        created = await demo_lab.call_tool("documents_fixed", "create_note", {"path": "test.txt", "text": "Kullanıcının gerçek notu"})
        self.assertFalse(created["is_error"])
        result = await demo_lab.call_tool("documents_fixed", "read_note", {"path": "test.txt"})
        self.assertIn("Kullanıcının gerçek notu", result["result"]["content"][0]["text"])
        self.assertEqual((Path(self.directory.name) / "documents/documents/test.txt").read_text(encoding="utf-8"), "Kullanıcının gerçek notu")
        rejected = await demo_lab.call_tool("documents_fixed", "read_note", {"path": "../outside.txt"})
        self.assertTrue(rejected["is_error"])


if __name__ == "__main__":
    unittest.main()
