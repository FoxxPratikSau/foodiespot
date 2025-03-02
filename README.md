# Restaurant Booking AI Agent

This repository contains an AI-powered restaurant booking assistant that helps users find restaurants, get recommendations, and make reservations. It demonstrates different implementation approaches for building AI agents with tool-use capabilities.

## Features

- Search for restaurants by city, cuisine type, and ambiance
- Get detailed information about specific restaurants
- Receive restaurant recommendations based on preferences
- Check availability and make reservations
- View reservation details
- Progressive information gathering for a better user experience

## Implementation Approaches

This repository includes three different implementations of the restaurant booking agent:

1. **Original ToolAgent**: A custom implementation using a structured prompting pattern that guides the LLM to call appropriate functions
2. **DSPy Agent**: A more modular implementation using DSPy's ChainOfThought pattern for better performance
3. **DSPy ReAct Agent**: An advanced implementation using DSPy's ReAct pattern, which combines reasoning and acting in an iterative cycle

## Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/restaurant-booking-agent.git
   cd restaurant-booking-agent
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your API keys in the `.env` file:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   NEON_DB_URL=your_neon_database_url_here
   ```

   - Get a Groq API key by signing up at [https://console.groq.com/](https://console.groq.com/)
   - Set up a Neon database at [https://neon.tech/](https://neon.tech/) or use any PostgreSQL database

4. Initialize the database:
   ```bash
   node db-populate.js
   ```

## Running the Agent

You can run any of the three agent implementations directly:

```bash
# Run the original ToolAgent
python intent_restaurant_booking.py

# Run the DSPy Agent
python dspy_restaurant_agent.py

# Run the DSPy ReAct Agent
python dspy_react_restaurant_agent.py
```

Or use the agent runner to try all implementations:

```bash
# Interactive selection menu
python restaurant_agent_runner.py

# Run a specific agent
python restaurant_agent_runner.py --agent original
python restaurant_agent_runner.py --agent dspy
python restaurant_agent_runner.py --agent react

# Run all agents in sequence
python restaurant_agent_runner.py --agent all
```

## Example Queries

Here are some examples of queries you can try with the agent:

- "Find Italian restaurants in New York"
- "Are there any good places for a romantic dinner in Chicago?"
- "I need a restaurant for a business meeting in Boston"
- "Book a table for 4 at Del Posto tomorrow at 7 PM"
- "What's the phone number for The French Laundry?"
- "Check my reservation with confirmation number 12345"

## Comparing Implementations

The three implementations offer different advantages:

1. **Original ToolAgent**:
   - Simple architecture with minimal dependencies
   - Direct control over prompt engineering
   - Easy to understand and modify

2. **DSPy Agent**:
   - More modular design with separate components
   - Better natural language understanding
   - Enhanced information extraction for booking details

3. **DSPy ReAct Agent**:
   - Most advanced reasoning capabilities
   - Iterative thinking process for complex queries
   - Better handling of edge cases
   - Superior conversation management

Try them all to see which performs best for your use case!

## Technical Details

### Database Schema

The application uses a PostgreSQL database with the following tables:

- `restaurants`: Contains restaurant information (name, city, cuisine, etc.)
- `reservations`: Stores reservation details

### Tools and Modules

- The `search_restaurants`, `get_restaurant_details`, and other modules provide specific functionality
- Each agent implementation orchestrates these tools in different ways
- DSPy provides optimized prompting patterns for better LLM performance

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 