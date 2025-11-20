import os
import json
import subprocess
import ollama

# --- 1. Define Tools ---


def read_file(path):
    try:
        if not os.path.exists(path):
            return "Error: File not found."
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


def write_file(path, content):
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Success: File '{path}' written successfully."
    except Exception as e:
        return f"Error writing file: {str(e)}"


def list_files():
    return str(os.listdir("."))


def run_command(command):
    # SAFETY CHECK: Ask user for permission before running shell commands
    print(f"\n[⚠️ SAFETY CHECK] Agent wants to run command: {command}")
    confirm = input("Allow execution? (y/n): ")
    if confirm.lower() != "y":
        return "Error: User denied command execution."

    try:
        # Run command with a timeout to prevent hanging
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        output = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out."
    except Exception as e:
        return f"Error executing command: {str(e)}"


# --- 2. System Prompt ---

system_prompt = """
You are an autonomous coding agent. You have access to the following tools:

1. read_file: Reads the content of a file. Args: path (string)
2. write_file: Writes content to a file. Args: path (string), content (string)
3. list_files: Lists files in the current directory. No args.
4. run_command: Executes a shell command. Args: command (string)

When you need to use a tool, you MUST output the request in strict JSON format.
Example: {"tool": "write_file", "args": {"path": "hello.py", "content": "print('hello')"}}

Do not output any other text when calling a tool. Only the JSON.
"""

# Initialize conversation history
messages = [{"role": "system", "content": system_prompt}]

print("--- Local Agent Started (Type 'quit' to exit) ---")
print("--- Supported Tools: read_file, write_file, list_files, run_command ---")

while True:
    client = ollama.Client(host="http://localhost:11434")
    # --- 3. User Input ---
    user_input = input("\nUser: ")
    if user_input.lower() in ["quit", "exit"]:
        break

    messages.append({"role": "user", "content": user_input})

    # --- 4. LLM Generation ---
    print("Agent is thinking...")
    try:
        response = client.chat(model="qwen2.5-coder:0.5b", messages=messages)
    except Exception as e:
        print(f"Ollama Error: {e}")
        continue

    content = response["message"]["content"]

    # --- 5. Tool Detection & Execution ---
    if '{"tool":' in content:
        try:
            # Clean up JSON (sometimes models add markdown code blocks)
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]

            # Extract JSON object
            start_idx = json_str.find("{")
            end_idx = json_str.rfind("}") + 1
            clean_json = json_str[start_idx:end_idx]

            parsed_json = json.loads(clean_json)
            tool_name = parsed_json.get("tool")
            args = parsed_json.get("args", {})

            print(f"[System] Tool detected: {tool_name}")

            # Execute Tool
            result = "Error: Tool not found"
            if tool_name == "read_file":
                result = read_file(args.get("path"))
            elif tool_name == "write_file":
                result = write_file(args.get("path"), args.get("content"))
            elif tool_name == "list_files":
                result = list_files()
            elif tool_name == "run_command":
                result = run_command(args.get("command"))
            print(result)
            # --- 6. Feed Result Back to LLM ---
            # Add the model's tool call and the actual tool output to history
            messages.append({"role": "assistant", "content": content})
            messages.append(
                {"role": "user", "content": f"Tool Execution Result: {result}"}
            )

            # Generate final response interpreting the tool output
            final_response = client.chat(model="qwen2.5-coder:0.5b", messages=messages)
            final_content = final_response["message"]["content"]

            print(f"Agent: {final_content}")
            messages.append({"role": "assistant", "content": final_content})

        except json.JSONDecodeError:
            print("System: Failed to parse tool call JSON.")
            print(f"Agent (Raw): {content}")
    else:
        # No tool called, just normal chat
        print(f"Agent: {content}")
        messages.append({"role": "assistant", "content": content})
