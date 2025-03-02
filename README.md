# Restaurant Booking AI Agent

This repository contains an AI-powered restaurant booking assistant that helps users find restaurants, get recommendations, and make reservations. It demonstrates a structured approach to building an AI agent with tool-use capabilities.

## Features

- Search for restaurants by city, cuisine type, and ambiance
- Get detailed information about specific restaurants
- Receive restaurant recommendations based on preferences
- Check availability and make reservations
- View reservation details
- Progressive information gathering for a better user experience

## Implementation

The project includes the `intent_restaurant_booking.py` script, which serves as the main entry point for the restaurant booking agent. This implementation utilizes a structured prompting pattern to guide the AI in making appropriate function calls.

### Setup

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

To run the restaurant booking agent, execute the following command:

```bash
python intent_restaurant_booking.py
```

## Example Queries

Here are some examples of queries you can try with the agent:

- "Find Italian restaurants in New York"
- "Are there any good places for a romantic dinner in Chicago?"
- "I need a restaurant for a business meeting in Boston"
- "Book a table for 4 at Del Posto tomorrow at 7 PM"
- "What's the phone number for The French Laundry?"
- "Check my reservation with confirmation number 12345"

## Technical Details

### Database Schema

The application uses a PostgreSQL database with the following tables:

- `restaurants`: Contains restaurant information (name, city, cuisine, etc.)
- `reservations`: Stores reservation details

### Tools and Modules

- The `search_restaurants`, `get_restaurant_details`, and other modules provide specific functionality
- The agent orchestrates these tools to fulfill user requests

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 