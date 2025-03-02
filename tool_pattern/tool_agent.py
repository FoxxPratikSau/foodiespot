import json
import re

from colorama import Fore
from dotenv import load_dotenv
from groq import Groq

from tool_pattern.tool import Tool
from tool_pattern.tool import validate_arguments
from utils.completions import build_prompt_structure
from utils.completions import ChatHistory
from utils.completions import completions_create
from utils.completions import update_chat_history
from utils.extraction import extract_tag_content

load_dotenv()


TOOL_SYSTEM_PROMPT = """
You are a restaurant concierge assistant who helps people find and book restaurants. You provide efficient, direct answers based only on what you know from the database.

IMPORTANT GUIDELINES:
- Be concise and solution-oriented - focus on providing information rather than extended conversation.
- Minimize questions - only ask for essential information when absolutely necessary.
- When you have enough information to help, directly provide results instead of asking more questions.
- Present information clearly and directly - focus on facts from the database.
- When recommending restaurants, provide specific options with key details.
- If the user's request is vague, make reasonable assumptions based on common preferences.
- Prioritize calling the appropriate function with available information over asking clarifying questions.

DATABASE AND DATA INTEGRITY:
- NEVER make up or hallucinate restaurant information that isn't returned from the database.
- If a search returns no results (empty data array), explicitly tell the user no results were found.
- When a query returns no matches, suggest modifications (different cuisine, city, etc.) based on what IS available in the database.
- Only recommend restaurants that were explicitly returned in query results.
- If a user asks about a specific restaurant, city, or cuisine that isn't in the database, clearly state that you don't have that information.
- Use the get_available_options tool to check what options are actually available in the database when needed.

HANDLING EMPTY RESULTS:
- When a search returns empty results, look at the "fallback_suggestions" in the response for alternative options.
- If a city is valid but a cuisine isn't found, suggest available cuisines in that city.
- If a user's search is too specific, suggest broadening it (e.g., different cuisine, removing mood constraints).
- NEVER fabricate restaurants, reviews, or details - only present data that was actually returned from database queries.

DATA HANDLING:
- All tools return JSON data with a "status" field and usually a "data" field with the actual results.
- Always check the "status" field ("success", "error", "not_found", "no_results", etc.) to determine how to respond.
- Focus on the key data properties most relevant to the user's request.
- Filter and sort results to show the most relevant options first.

For each function call return a json object with function name and arguments within <tool_call></tool_call>
XML tags as follows:

<tool_call>
{"name": <function-name>,"arguments": <args-dict>,  "id": <monotonically-increasing-id>}
</tool_call>

Here are the available tools:

<tools>
%s
</tools>
"""


class ToolAgent:
    """
    The ToolAgent class represents an agent that can interact with a language model and use tools
    to assist with user queries. It generates function calls based on user input, validates arguments,
    and runs the respective tools.

    Attributes:
        tools (Tool | list[Tool]): A list of tools available to the agent.
        model (str): The model to be used for generating tool calls and responses.
        client (Groq): The Groq client used to interact with the language model.
        tools_dict (dict): A dictionary mapping tool names to their corresponding Tool objects.
    """

    def __init__(
        self,
        tools: Tool | list[Tool],
        model: str = "llama-3.3-70b-versatile",
    ) -> None:
        self.client = Groq()
        self.model = model
        self.tools = tools if isinstance(tools, list) else [tools]
        self.tools_dict = {tool.name: tool for tool in self.tools}
        
        # Initialize chat histories
        self.tool_chat_history = ChatHistory(
            [
                build_prompt_structure(
                    prompt=TOOL_SYSTEM_PROMPT % self.add_tool_signatures(),
                    role="system",
                ),
            ]
        )
        self.agent_chat_history = ChatHistory([])
        # Track tool call IDs
        self.tool_call_id = 0

    def add_tool_signatures(self) -> str:
        """
        Collects the function signatures of all available tools.

        Returns:
            str: A concatenated string of all tool function signatures in JSON format.
        """
        return "".join([tool.fn_signature for tool in self.tools])

    def process_tool_calls(self, tool_calls_content: list) -> dict:
        """
        Processes each tool call, validates arguments, executes the tools, and collects results.

        Args:
            tool_calls_content (list): List of strings, each representing a tool call in JSON format.

        Returns:
            dict: A dictionary where the keys are tool call IDs and values are the results from the tools.
        """
        observations = {}
        for tool_call_str in tool_calls_content:
            try:
                tool_call = json.loads(tool_call_str)
                tool_name = tool_call["name"]
                
                # Verify tool exists
                if tool_name not in self.tools_dict:
                    raise KeyError(tool_name)
                    
                tool = self.tools_dict[tool_name]

                print(Fore.GREEN + f"\nUsing Tool: {tool_name}")

                # Validate and execute the tool call
                validated_tool_call = validate_arguments(
                    tool_call, json.loads(tool.fn_signature)
                )
                print(Fore.GREEN + f"\nTool call dict: \n{validated_tool_call}")

                # Type checking for integer parameters like group_size
                args = validated_tool_call["arguments"]
                for key, value in args.items():
                    if key == 'group_size' and value is not None:
                        try:
                            args[key] = int(value)
                        except (ValueError, TypeError):
                            # If conversion fails, keep original value
                            pass

                result = tool.run(**args)
                print(Fore.GREEN + f"\nTool result: \n{result}")
                # Store the result using the tool call ID
                observations[validated_tool_call["id"]] = result
            except KeyError as e:
                print(Fore.RED + f"\nError: Attempted to call non-existent tool: {e}")
                observations["error"] = f"Tool '{e}' not found"
            except Exception as e:
                print(Fore.RED + f"\nError processing tool call: {e}")
                observations["error"] = f"Error: {str(e)}"
        
        return observations

    def run(
        self,
        user_msg: str,
    ) -> str:
        """
        Handles the full process of interacting with the language model and executing a tool based on user input.

        Args:
            user_msg (str): The user's message that prompts the tool agent to act.

        Returns:
            str: The final output after executing the tool and generating a response from the model.
        """
        # Reset the tool call ID for each new user message
        self.tool_call_id = 0
        
        user_prompt = build_prompt_structure(prompt=user_msg, role="user")
        
        # Add user message to both chat histories
        self.tool_chat_history.append(user_prompt)
        self.agent_chat_history.append(user_prompt)

        tool_call_response = completions_create(
            self.client, messages=self.tool_chat_history, model=self.model
        )
        
        # Add assistant response to tool chat history
        update_chat_history(
            self.tool_chat_history, 
            tool_call_response, 
            "assistant"
        )
        
        tool_calls = extract_tag_content(str(tool_call_response), "tool_call")

        if tool_calls.found:
            try:
                observations = self.process_tool_calls(tool_calls.content)
                
                # Check if any results have empty data but include fallback suggestions
                for key, result in observations.items():
                    if isinstance(result, dict):
                        if result.get("status") == "no_results" and "data" in result and not result["data"]:
                            # Add an explicit reminder to not make up data
                            observations["reminder"] = {
                                "message": "IMPORTANT: No restaurants found matching these criteria. Do NOT make up restaurant information. Only suggest options based on available data in fallback_suggestions if present."
                            }
                            break
                
                # Format the observations as structured data to help the AI
                formatted_observations = json.dumps(observations, indent=2)
                update_chat_history(
                    self.agent_chat_history, 
                    f"Observation: {formatted_observations}", 
                    "user"
                )
            except Exception as e:
                # Handle any exceptions during tool processing
                print(Fore.RED + f"\nError: {e}")
                update_chat_history(
                    self.agent_chat_history,
                    f"Error: Unable to process that request. {str(e)}",
                    "user"
                )

        response = completions_create(self.client, self.agent_chat_history, self.model)
        
        # Add assistant response to agent chat history
        update_chat_history(
            self.agent_chat_history,
            response,
            "assistant"
        )
        
        return response