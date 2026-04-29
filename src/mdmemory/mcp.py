"""MCP Server for MdMemory."""

import os
import sys
import argparse
import asyncio
from typing import Any, Dict, List, Optional
from pathlib import Path

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from .core import MdMemory


class MdMemoryMCPServer:
    """MCP Server wrapper for MdMemory."""

    def __init__(
        self,
        usr_id: str,
        model_name: str,
        model_api_key: Optional[str] = None,
        storage_path: str = "./MdMemory",
    ):
        self.usr_id = usr_id
        self.memory = MdMemory(
            model_name=model_name,
            model_api_key=model_api_key,
            storage_path=storage_path
        )
        self.server = Server("mdmemory")
        self._setup_handlers()

    def _setup_handlers(self):
        """Register MCP handlers."""

        @self.server.list_resources()
        async def handle_list_resources() -> List[types.Resource]:
            await self.memory._ensure_initialized()
            resources = [
                types.Resource(
                    uri="mdmemory://index",
                    name="Knowledge Tree Root Index",
                    description="The main index of all stored memories",
                    mimeType="text/markdown",
                )
            ]
            
            topics = self.memory.list_topics()
            for topic in topics:
                resources.append(
                    types.Resource(
                        uri=f"mdmemory://topic/{topic}",
                        name=f"Topic: {topic}",
                        description=f"Full content for topic {topic}",
                        mimeType="text/markdown",
                    )
                )
            return resources

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            await self.memory._ensure_initialized()
            if uri == "mdmemory://index":
                return await self.memory.retrieve(self.usr_id)
            
            if uri.startswith("mdmemory://topic/"):
                topic = uri.replace("mdmemory://topic/", "")
                content = await self.memory.get(self.usr_id, topic)
                if content:
                    return content
            
            raise ValueError(f"Resource not found: {uri}")

        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            return [
                types.Tool(
                    name="store_memory",
                    description="Store a new memory item. The LLM will automatically categorize it.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "The content to store"},
                            "topic": {"type": "string", "description": "Optional topic ID. If omitted, one is generated."}
                        },
                        "required": ["content"]
                    },
                ),
                types.Tool(
                    name="search_memory",
                    description="Search for memories using keywords in topic, summary, or tags.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Keyword search query"}
                        },
                        "required": ["query"]
                    },
                ),
                types.Tool(
                    name="get_topic",
                    description="Retrieve the full content of a specific topic by its ID.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string", "description": "The topic ID to retrieve"}
                        },
                        "required": ["topic"]
                    },
                ),
                types.Tool(
                    name="delete_topic",
                    description="Permanently remove a topic from memory.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string", "description": "The topic ID to delete"}
                        },
                        "required": ["topic"]
                    },
                ),
                types.Tool(
                    name="optimize_structure",
                    description="Manually trigger a reorganization of the knowledge tree to keep it tidy.",
                    inputSchema={"type": "object", "properties": {}},
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
            await self.memory._ensure_initialized()
            
            if name == "store_memory":
                content = arguments.get("content")
                topic = arguments.get("topic")
                result = await self.memory.store(self.usr_id, content, topic)
                return [types.TextContent(type="text", text=f"Stored successfully as topic: {result}")]
            
            elif name == "search_memory":
                query = arguments.get("query")
                results = await self.memory.search(self.usr_id, query)
                return [types.TextContent(type="text", text=f"Search Results:\n{json_format(results)}")]
            
            elif name == "get_topic":
                topic = arguments.get("topic")
                content = await self.memory.get(self.usr_id, topic)
                if content:
                    return [types.TextContent(type="text", text=content)]
                return [types.TextContent(type="text", text=f"Topic '{topic}' not found.")]
            
            elif name == "delete_topic":
                topic = arguments.get("topic")
                success = await self.memory.delete(self.usr_id, topic)
                return [types.TextContent(type="text", text=f"Deletion {'successful' if success else 'failed'} for topic: {topic}")]
            
            elif name == "optimize_structure":
                await self.memory.optimize(self.usr_id)
                return [types.TextContent(type="text", text="Optimization process completed.")]
            
            raise ValueError(f"Unknown tool: {name}")

        @self.server.list_prompts()
        async def handle_list_prompts() -> List[types.Prompt]:
            return [
                types.Prompt(
                    name="summarize_knowledge",
                    description="Ask the agent to summarize all knowledge stored in memory.",
                    arguments=[]
                )
            ]

        @self.server.get_prompt()
        async def handle_get_prompt(name: str, arguments: Dict[str, str]) -> types.GetPromptResult:
            if name == "summarize_knowledge":
                await self.memory._ensure_initialized()
                index = await self.memory.retrieve(self.usr_id)
                return types.GetPromptResult(
                    description="Summarize the current knowledge tree",
                    messages=[
                        types.PromptMessage(
                            role="user",
                            content=types.TextContent(
                                type="text",
                                text=f"Please summarize my current knowledge based on this index:\n\n{index}"
                            )
                        )
                    ]
                )
            raise ValueError(f"Unknown prompt: {name}")

    async def run_stdio(self):
        """Run server using stdio transport."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="mdmemory",
                    server_version="0.4.1",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    async def run_sse(self, host: str = "0.0.0.0", port: int = 8000):
        """Run server using SSE transport (FastAPI)."""
        from mcp.server.fastapi import FastApiServer
        import uvicorn
        
        starlette_app = FastApiServer(self.server)
        config = uvicorn.Config(starlette_app, host=host, port=port)
        server = uvicorn.Server(config)
        await server.serve()


def json_format(data: Any) -> str:
    import json
    return json.dumps(data, indent=2)


def main():
    """Main entry point for MCP server."""
    parser = argparse.ArgumentParser(description="MdMemory MCP Server")
    parser.add_argument("--usr_id", help="User ID (defaults to MDMEMORY_USER_ID env var)")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio", help="Transport protocol")
    parser.add_argument("--host", default="0.0.0.0", help="Host for SSE")
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE")
    parser.add_argument("--storage", help="Storage path")
    parser.add_argument("--model", help="LLM model name")
    
    args = parser.parse_args()
    
    usr_id = args.usr_id or os.environ.get("MDMEMORY_USER_ID")
    if not usr_id:
        print("Error: --usr_id or MDMEMORY_USER_ID environment variable is required.")
        sys.exit(1)
        
    model_name = args.model or os.environ.get("MDMEMORY_MODEL") or "gpt-3.5-turbo"
    api_key = os.environ.get("MDMEMORY_API_KEY")
    storage_path = args.storage or os.environ.get("MDMEMORY_STORAGE") or "./MdMemory"
    
    server_wrapper = MdMemoryMCPServer(
        usr_id=usr_id,
        model_name=model_name,
        model_api_key=api_key,
        storage_path=storage_path
    )
    
    if args.transport == "stdio":
        asyncio.run(server_wrapper.run_stdio())
    else:
        asyncio.run(server_wrapper.run_sse(host=args.host, port=args.port))


if __name__ == "__main__":
    main()
