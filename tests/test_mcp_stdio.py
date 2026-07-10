from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def list_tool_names(data_dir: Path) -> set[str]:
    environment = dict(os.environ)
    environment["COSYVOICE_KO_DATA_DIR"] = str(data_dir)
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "cosyvoice_ko_mcp.server"],
        env=environment,
    )
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            result = await session.list_tools()
            return {tool.name for tool in result.tools}


def test_stdio_server_lists_tools_without_loading_model(tmp_path: Path) -> None:
    names = asyncio.run(list_tool_names(tmp_path / "mcp-data"))
    assert names == {
        "model_status",
        "usage_reporting_status",
        "configure_usage_reporting",
        "report_feedback",
        "prepare_model",
        "register_voice",
        "list_voices",
        "synthesize",
        "synthesize_zero_shot",
        "remove_voice",
    }
