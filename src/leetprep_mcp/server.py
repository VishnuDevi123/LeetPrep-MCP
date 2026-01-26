from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import json
import db
import leetcode_client

server = Server("leetprep-mcp Server")

# Define the tool listing handler
# This function will be called to list all available tools.
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    '''List all available tools.'''
    return [
        types.Tool(
            name="add_problem",
            description="Add a LeetCode problem to the local database for tracking.",
            inputSchema={
                "type": "object",
                "properties": {
                    "leetcode_id": {"type": "integer", "description": "leetcode problem id"},
                    "title": {"type": "string", "description": "leetcode problem title"},
                    "slug": {"type": "string", "description": "leetcode problem URL slug"},
                    "difficulty": {"type": "string", "description": "leetcode problem difficulty, like easy, medium, hard"},
                    "patterns": {"type": "string", "description": "JSON array of problem patterns"},
                    "companies": {"type": "string", "description": "JSON array of companies associated with the problem"},
                    "created_at": {"type": "string", "description": "timestamp when the problem was created"},
                    },
                "required": ["leetcode_id", "title", "slug", "difficulty", "patterns", "companies", "created_at"],
                
            },
            ),
        types.Tool(
            name="fetch_problem",
            description="Fetch a LeetCode problem's details from making a http request using the title slug and exttracing the infromation from the responce",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "Problem URL slug (e.g., 'two-sum')"}
                },
                "required": ["slug"]
            }
        )
    ]
  
# Implement the tool call handler
# This function will be called when a tool is invoked.  
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "add_problem":
        leetcode_id = arguments["leetcode_id"]
        title = arguments["title"]
        slug = arguments["slug"]
        difficulty = arguments["difficulty"]
        patterns = arguments["patterns"]
        companies = arguments["companies"]
        created_at = arguments["created_at"]
        result = db.add_problem(
            leetcode_id,
            title,
            slug,
            difficulty,
            patterns,
            companies,
            created_at
        )
        return [types.TextContent(type="text", text=json.dumps(result))]
    elif name == "fetch_problem":
        slug = arguments["slug"] 
        result = leetcode_client.fetch_problem(slug)
        return [types.TextContent(type="text", text=json.dumps(result))]
        
    
    else:
        raise ValueError(f"Unknown tool: {name}")

# Run the server using stdio
# This allows the server to communicate over standard input/output streams.
async def run():
    db.init_db()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            )
            
        )
    

if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
    
    
    
