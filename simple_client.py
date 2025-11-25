import httpx
import json
import uuid
import time

# --- Configuration ---
# Your server's address
SERVER_URL = "http://127.0.0.1:8080"
# The tool you want to call
TOOL_NAME = "generate_image"
# The arguments for the tool
TOOL_ARGS = {
    "prompt": "a futuristic car driving on the surface of Mars"
}

def create_mcp_request(tool_name: str, arguments: dict) -> str:
    """Creates a JSON-RPC 2.0 message for an MCP tool call."""
    request_id = str(uuid.uuid4())
    message = {
        "jsonrpc": "2.0",
        "method": "call_tool",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
        "id": request_id,
    }
    return json.dumps(message), request_id

def main():
    """
    A simple client to connect to the MCP server and call a tool.
    """
    print(f"Connecting to MCP server at {SERVER_URL}")
    print(f"Calling tool '{TOOL_NAME}' with prompt: '{TOOL_ARGS['prompt']}'")

    # The MCP protocol uses Server-Sent Events (SSE) for communication.
    # The client first connects to the /sse endpoint to get an event stream.
    # Then, it sends a POST request to /messages/ with the tool call.
    # Finally, it listens on the /sse stream for the result.

    try:
        with httpx.stream("GET", f"{SERVER_URL}/sse", timeout=None) as response:
            print("\n--- Connection Log ---")
            print("✅ Connected to /sse endpoint.")
            
            # The first message from the server should be the session info
            sse_iterator = response.iter_bytes()
            
            # Consume the initial session message from the server
            initial_message = next(sse_iterator)
            print("Received session info from server.")

            # Now, send the tool call request
            tool_request_json, request_id = create_mcp_request(TOOL_NAME, TOOL_ARGS)
            post_response = httpx.post(f"{SERVER_URL}/messages/", content=tool_request_json)
            
            if post_response.status_code == 200:
                print(f"✅ Successfully sent tool call request (ID: {request_id}).")
            else:
                print(f"❌ Failed to send tool call request. Status: {post_response.status_code}")
                print(f"Response: {post_response.text}")
                return

            print("\n--- Waiting for Result ---")
            # Listen for the result on the SSE stream
            for line in sse_iterator:
                line_str = line.decode('utf-8').strip()
                if line_str.startswith('data:'):
                    data_str = line_str[len('data:'):].strip()
                    try:
                        data = json.loads(data_str)
                        # Check if this message is the result of our request
                        if data.get("id") == request_id and "result" in data:
                            print("\n--- Result Received ---")
                            result = data["result"]
                            # The result is a list of content parts. We'll find the image.
                            for part in result:
                                if part.get("type") == "image":
                                    image_uri = part["image"]["uri"]
                                    print(f"🖼️  Image generated successfully!")
                                    print(f"URI: {image_uri}")
                            # Exit after getting the result
                            return
                    except json.JSONDecodeError:
                        # Ignore non-json data lines
                        pass
    except httpx.ConnectError as e:
        print(f"\n❌ Connection Error: Could not connect to the server at {SERVER_URL}.")
        print("Please make sure your MCP server is running.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
