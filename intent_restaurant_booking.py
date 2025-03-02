import os
import json
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from colorama import init, Fore, Style
from datetime import datetime

from tool_pattern.tool_agent import ToolAgent
from tool_pattern.tool import tool
from utils.logging import fancy_print

# Initialize colorama
init()

# Load environment variables
load_dotenv()

# Global variables to store database metadata
AVAILABLE_CITIES = set()
AVAILABLE_CUISINES = set()
AVAILABLE_MOODS = set()
CITY_MAPPINGS = {}  # For normalizing city names

# Database connection
def get_db_connection():
    """Create and return a database connection."""
    try:
        conn = psycopg2.connect(os.getenv("NEON_DB_URL"))
        conn.autocommit = True
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def initialize_database_tables():
    """Initialize database tables if they don't exist."""
    conn = get_db_connection()
    if not conn:
        print(Fore.RED + "Error: Failed to initialize database tables" + Fore.RESET)
        return False
    
    try:
        cur = conn.cursor()
        
        # Create restaurants table if it doesn't exist
        # (This is typically done by the database population script, but adding for completeness)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS restaurants (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                city VARCHAR(100) NOT NULL,
                address VARCHAR(255) NOT NULL,
                cuisine VARCHAR(100) NOT NULL,
                seating_capacity INTEGER NOT NULL,
                available_capacity INTEGER NOT NULL,
                available_reservations TEXT[] NOT NULL,
                mood VARCHAR(100) NOT NULL
            );
        """)
        
        # Create reservations table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id SERIAL PRIMARY KEY,
                restaurant_id INTEGER REFERENCES restaurants(id),
                customer_name VARCHAR(255) NOT NULL,
                contact_number VARCHAR(20) NOT NULL,
                party_size INTEGER NOT NULL,
                reservation_time VARCHAR(20) NOT NULL,
                reservation_date DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        print(Fore.GREEN + "Database tables initialized successfully" + Fore.RESET)
        return True
    
    except Exception as e:
        print(Fore.RED + f"Error initializing database tables: {e}" + Fore.RESET)
        return False
    
    finally:
        if conn:
            conn.close()

def initialize_db_metadata():
    """Initialize database metadata by loading available cities, cuisines, etc."""
    global AVAILABLE_CITIES, AVAILABLE_CUISINES, AVAILABLE_MOODS, CITY_MAPPINGS
    
    # Initialize database tables
    initialize_database_tables()
    
    conn = get_db_connection()
    if not conn:
        print(Fore.RED + "Error: Failed to initialize database metadata" + Fore.RESET)
        return
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get all distinct cities
        cur.execute("SELECT DISTINCT city FROM restaurants")
        cities = [row['city'].lower() for row in cur.fetchall()]
        AVAILABLE_CITIES = set(cities)
        
        # Get all distinct cuisines
        cur.execute("SELECT DISTINCT cuisine FROM restaurants")
        cuisines = [row['cuisine'].lower() for row in cur.fetchall()]
        AVAILABLE_CUISINES = set(cuisines)
        
        # Get all distinct moods
        cur.execute("SELECT DISTINCT mood FROM restaurants")
        moods = [row['mood'].lower() for row in cur.fetchall()]
        AVAILABLE_MOODS = set(moods)
        
        # Initialize city mappings (for handling variations like "New York" vs "NYC")
        for city in AVAILABLE_CITIES:
            CITY_MAPPINGS[city] = city  # Basic mapping (lowercase city -> original city)
            
        # Add common variations for cities
        city_variations = {
            "new york": ["nyc", "new york city", "manhattan"],
            "los angeles": ["la", "l.a.", "lax"],
            "san francisco": ["sf", "san fran"],
            "las vegas": ["vegas"],
            "washington dc": ["washington d.c.", "dc", "d.c."],
        }
        
        # Add the variations to our mappings
        for city, variations in city_variations.items():
            if city in AVAILABLE_CITIES:
                for variation in variations:
                    CITY_MAPPINGS[variation] = city
        
        print(Fore.GREEN + f"Database metadata initialized: {len(AVAILABLE_CITIES)} cities, {len(AVAILABLE_CUISINES)} cuisines, {len(AVAILABLE_MOODS)} moods" + Fore.RESET)
    
    except Exception as e:
        print(Fore.RED + f"Error initializing database metadata: {e}" + Fore.RESET)
    
    finally:
        if conn:
            conn.close()

def normalize_city(city):
    """Normalize city name to match database entries."""
    if not city:
        return None
    
    city_lower = city.lower()
    
    # Check if we have a mapping for this city
    if city_lower in CITY_MAPPINGS:
        return CITY_MAPPINGS[city_lower]
    
    # If no direct mapping, try to find a partial match
    for variation, mapped_city in CITY_MAPPINGS.items():
        if variation in city_lower or city_lower in variation:
            return mapped_city
    
    # If no match found, return the original city
    return city

def normalize_cuisine(cuisine):
    """Normalize cuisine name to match database entries."""
    if not cuisine:
        return None
    
    cuisine_lower = cuisine.lower()
    
    # Check if the cuisine exists in our database
    if cuisine_lower in AVAILABLE_CUISINES:
        return cuisine_lower
    
    # If no exact match, try to find a partial match
    for db_cuisine in AVAILABLE_CUISINES:
        if cuisine_lower in db_cuisine or db_cuisine in cuisine_lower:
            return db_cuisine
    
    # If no match found, return the original cuisine
    return cuisine

@tool
def search_restaurants(city: str = None, cuisine: str = None, mood: str = None):
    """
    Search for restaurants based on city, cuisine type, and/or mood.
    
    Args:
        city (str, optional): The city to search for restaurants in.
        cuisine (str, optional): The type of cuisine (e.g., Italian, Japanese).
        mood (str, optional): The ambiance/mood (e.g., romantic, casual, sophisticated).
        
    Returns:
        dict: JSON-formatted data with the search results and metadata.
    """
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database connection error", "data": None}
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Normalize inputs to match database values
        normalized_city = normalize_city(city) if city else None
        normalized_cuisine = normalize_cuisine(cuisine) if cuisine else None
        
        # Build the query based on provided parameters
        query = "SELECT * FROM restaurants WHERE 1=1"
        params = []
        
        if normalized_city:
            query += " AND LOWER(city) = LOWER(%s)"
            params.append(normalized_city)
        
        if normalized_cuisine:
            query += " AND LOWER(cuisine) = LOWER(%s)"
            params.append(normalized_cuisine)
        
        if mood:
            query += " AND LOWER(mood) = LOWER(%s)"
            params.append(mood)
        
        # Execute the query
        cur.execute(query, params)
        restaurants = cur.fetchall()
        
        # Convert restaurants to a list of dictionaries for JSON serialization
        result_data = []
        for restaurant in restaurants:
            # Convert the RealDictRow to a regular dict
            restaurant_dict = dict(restaurant)
            # Convert datetime objects to strings for JSON serialization if needed
            for key, value in restaurant_dict.items():
                if isinstance(value, datetime):
                    restaurant_dict[key] = value.isoformat()
            result_data.append(restaurant_dict)
        
        # If no results were found but we have normalized inputs, include this information
        normalization_info = {}
        if city and normalized_city and city.lower() != normalized_city:
            normalization_info["city"] = {"original": city, "normalized": normalized_city}
        if cuisine and normalized_cuisine and cuisine.lower() != normalized_cuisine:
            normalization_info["cuisine"] = {"original": cuisine, "normalized": normalized_cuisine}
        
        return {
            "status": "success",
            "count": len(result_data),
            "query_params": {
                "city": city,
                "normalized_city": normalized_city,
                "cuisine": cuisine,
                "normalized_cuisine": normalized_cuisine,
                "mood": mood
            },
            "normalization_info": normalization_info if normalization_info else None,
            "data": result_data
        }
    
    except Exception as e:
        return {"status": "error", "message": str(e), "data": None}
    
    finally:
        if conn:
            conn.close()

@tool
def get_restaurant_details(restaurant_name: str, city: str = None):
    """
    Get detailed information about a specific restaurant.
    
    Args:
        restaurant_name (str): The name of the restaurant.
        city (str, optional): The city where the restaurant is located.
        
    Returns:
        dict: JSON-formatted data with restaurant details.
    """
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database connection error", "data": None}
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Normalize city if provided
        normalized_city = normalize_city(city) if city else None
        
        # Build the query
        query = "SELECT * FROM restaurants WHERE LOWER(name) LIKE LOWER(%s)"
        params = [f"%{restaurant_name}%"]
        
        if normalized_city:
            query += " AND LOWER(city) = LOWER(%s)"
            params.append(normalized_city)
        
        # Execute the query
        cur.execute(query, params)
        restaurant = cur.fetchone()
        
        if not restaurant:
            return {
                "status": "not_found",
                "message": "Restaurant not found",
                "query_params": {
                    "restaurant_name": restaurant_name,
                    "city": city,
                    "normalized_city": normalized_city
                },
                "data": None
            }
        
        # Convert to regular dict for JSON serialization
        restaurant_data = dict(restaurant)
        # Convert datetime objects to strings if needed
        for key, value in restaurant_data.items():
            if isinstance(value, datetime):
                restaurant_data[key] = value.isoformat()
        
        return {
            "status": "success",
            "query_params": {
                "restaurant_name": restaurant_name,
                "city": city,
                "normalized_city": normalized_city
            },
            "data": restaurant_data
        }
    
    except Exception as e:
        return {"status": "error", "message": str(e), "data": None}
    
    finally:
        if conn:
            conn.close()

@tool
def get_recommendations(city: str = None, occasion: str = None, cuisine_preference: str = None, group_size: int = None):
    """
    Get restaurant recommendations based on city, occasion, cuisine preference, and group size.
    
    Args:
        city (str, optional): The city to search for restaurants in.
        occasion (str, optional): The occasion (e.g., date, business meeting, family dinner).
        cuisine_preference (str, optional): Preferred cuisine type.
        group_size (int, optional): The number of people in the group.
        
    Returns:
        dict: JSON-formatted data with restaurant recommendations.
    """
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database connection error", "data": None}
    
    try:
        # Convert group_size to int if it's a string
        if group_size is not None and not isinstance(group_size, int):
            try:
                group_size = int(group_size)
            except (ValueError, TypeError):
                return {
                    "status": "error", 
                    "message": f"Invalid group size: {group_size}. Must be a number.", 
                    "data": None
                }
        
        # Normalize inputs to match database values
        normalized_city = normalize_city(city) if city else None
        normalized_cuisine = normalize_cuisine(cuisine_preference) if cuisine_preference else None
        
        # If we don't have enough info, suggest what's needed
        if not normalized_city:
            available_cities = list(AVAILABLE_CITIES)
            available_cities.sort()  # Sort for consistent output
            return {
                "status": "insufficient_info",
                "message": "Please specify a city for restaurant recommendations",
                "available_cities": available_cities[:10],  # Limit to 10 cities
                "data": None
            }
            
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Map occasion to mood (simplified for this example)
        mood_mapping = {
            "date": "romantic",
            "business": "sophisticated",
            "family": "casual",
            "friends": "casual",
            "celebration": "lively"
        }
        
        mood = None
        if occasion:
            # Check if any key is contained within the occasion string
            for key, value in mood_mapping.items():
                if key in occasion.lower():
                    mood = value
                    break
        
        # Build the query with proper parameter handling
        query = "SELECT * FROM restaurants WHERE 1=1"
        params = []
        
        if group_size is not None:
            query += " AND available_capacity >= %s"
            params.append(group_size)
        
        if normalized_city:
            query += " AND LOWER(city) = LOWER(%s)"
            params.append(normalized_city)
        
        if normalized_cuisine:
            query += " AND LOWER(cuisine) = LOWER(%s)"
            params.append(normalized_cuisine)
        
        if mood:
            query += " AND LOWER(mood) = LOWER(%s)"
            params.append(mood)
        
        # Execute the query
        cur.execute(query, params)
        restaurants = cur.fetchall()
        
        if not restaurants and mood:
            # Try a more relaxed search without mood constraint if no results
            new_query = query.replace(" AND LOWER(mood) = LOWER(%s)", "")
            # Remove the mood parameter from params
            new_params = [p for p in params if p != mood]
            cur.execute(new_query, new_params)
            restaurants = cur.fetchall()
        
        # If still no restaurants and cuisine preference was specified, try without cuisine
        if not restaurants and normalized_cuisine:
            new_query = query.replace(" AND LOWER(cuisine) = LOWER(%s)", "")
            if mood:
                new_query = new_query.replace(" AND LOWER(mood) = LOWER(%s)", "")
                new_params = [p for p in params if p != mood and p != normalized_cuisine]
            else:
                new_params = [p for p in params if p != normalized_cuisine]
            cur.execute(new_query, new_params)
            restaurants = cur.fetchall()
            
        # If still no results, try just the city to see what's available
        if not restaurants and normalized_city:
            cur.execute("SELECT * FROM restaurants WHERE LOWER(city) = LOWER(%s)", [normalized_city])
            city_restaurants = cur.fetchall()
            
            # Get available cuisines in this city to suggest alternatives
            available_city_cuisines = set()
            for restaurant in city_restaurants:
                if restaurant['cuisine']:
                    available_city_cuisines.add(restaurant['cuisine'].lower())
            
            # Create a list of fallback suggestions
            fallback_suggestions = {
                "available_cuisines": sorted(list(available_city_cuisines)),
                "city_restaurant_count": len(city_restaurants)
            }
        else:
            fallback_suggestions = None
        
        # Convert results to list of dicts for JSON
        result_data = []
        for restaurant in restaurants:
            restaurant_dict = dict(restaurant)
            # Convert datetime objects to strings for JSON serialization if needed
            for key, value in restaurant_dict.items():
                if isinstance(value, datetime):
                    restaurant_dict[key] = value.isoformat()
            result_data.append(restaurant_dict)
        
        # Sort results by relevance (prioritize exact mood/cuisine matches)
        if result_data:
            # Sort by most available times first
            result_data.sort(key=lambda x: len(x.get('available_reservations', [])), reverse=True)
            
            # If mood was specified, prioritize restaurants matching that mood
            if mood:
                result_data.sort(key=lambda x: x.get('mood', '').lower() == mood.lower(), reverse=True)
            
            # If cuisine was specified, prioritize restaurants matching that cuisine
            if normalized_cuisine:
                result_data.sort(key=lambda x: x.get('cuisine', '').lower() == normalized_cuisine.lower(), reverse=True)
        
        # If no results were found, include metadata about what was normalized
        normalization_info = {}
        if city and normalized_city and city.lower() != normalized_city:
            normalization_info["city"] = {"original": city, "normalized": normalized_city}
        if cuisine_preference and normalized_cuisine and cuisine_preference.lower() != normalized_cuisine:
            normalization_info["cuisine"] = {"original": cuisine_preference, "normalized": normalized_cuisine}
        
        return {
            "status": "success" if result_data else "no_results",
            "count": len(result_data),
            "query_params": {
                "city": city,
                "normalized_city": normalized_city,
                "occasion": occasion,
                "derived_mood": mood,
                "cuisine_preference": cuisine_preference,
                "normalized_cuisine": normalized_cuisine,
                "group_size": group_size
            },
            "normalization_info": normalization_info if normalization_info else None,
            "fallback_suggestions": fallback_suggestions,
            "data": result_data[:5]  # Limit to top 5 results for more efficient response
        }
    
    except Exception as e:
        return {"status": "error", "message": str(e), "data": None}
    
    finally:
        if conn:
            conn.close()

@tool
def book_restaurant(restaurant_name: str, reservation_time: str, party_size: int, customer_name: str, contact_number: str, city: str = None):
    """
    Book a table at a restaurant.
    
    IMPORTANT: Before calling this function, ensure ALL required information is available.
    Use validate_booking_info first if you're unsure whether you have complete information.
    
    Args:
        restaurant_name (str): The name of the restaurant.
        reservation_time (str): The desired reservation time (e.g., "7:00 PM").
        party_size (int): The number of people in the party.
        customer_name (str): The name of the customer making the reservation.
        contact_number (str): Contact phone number for the reservation.
        city (str, optional): The city where the restaurant is located.
        
    Returns:
        dict: JSON-formatted data with booking confirmation or error details.
    """
    # Check if all required fields are present
    missing_fields = []
    if not restaurant_name:
        missing_fields.append("restaurant name")
    if not reservation_time:
        missing_fields.append("reservation time")
    if not party_size:
        missing_fields.append("party size")
    try:
        party_size = int(party_size)  # Convert to int if it's a string
    except (ValueError, TypeError):
        missing_fields.append("valid party size (must be a number)")
    if not customer_name:
        missing_fields.append("customer name")
    if not contact_number:
        missing_fields.append("contact number")
    
    if missing_fields:
        return {
            "status": "incomplete",
            "message": "Missing required information",
            "missing_fields": missing_fields,
            "data": None
        }
    
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database connection error", "data": None}
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Normalize city if provided
        normalized_city = normalize_city(city) if city else None
        
        # Find the restaurant
        query = "SELECT * FROM restaurants WHERE LOWER(name) LIKE LOWER(%s)"
        params = [f"%{restaurant_name}%"]
        
        if normalized_city:
            query += " AND LOWER(city) = LOWER(%s)"
            params.append(normalized_city)
        
        cur.execute(query, params)
        restaurant = cur.fetchone()
        
        if not restaurant:
            return {
                "status": "not_found",
                "message": "Restaurant not found",
                "query_params": {
                    "restaurant_name": restaurant_name,
                    "city": city,
                    "normalized_city": normalized_city
                },
                "data": None
            }
        
        # Check if the requested time is available
        if reservation_time not in restaurant['available_reservations']:
            return {
                "status": "unavailable_time",
                "message": "Requested time is not available",
                "available_times": restaurant['available_reservations'],
                "data": None
            }
        
        # Check if there are enough seats available
        if party_size > restaurant['available_capacity']:
            return {
                "status": "insufficient_capacity",
                "message": "Not enough seats available",
                "available_capacity": restaurant['available_capacity'],
                "requested_size": party_size,
                "data": None
            }
        
        # Create the reservation
        cur.execute("""
            INSERT INTO reservations (restaurant_id, customer_name, contact_number, party_size, reservation_time)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (restaurant['id'], customer_name, contact_number, party_size, reservation_time))
        
        reservation_id = cur.fetchone()['id']
        
        # Update the restaurant's available capacity
        new_capacity = restaurant['available_capacity'] - party_size
        
        # Update available reservations - always remove the booked time slot
        available_reservations = restaurant['available_reservations'].copy()
        available_reservations.remove(reservation_time)
        
        cur.execute("""
            UPDATE restaurants
            SET available_capacity = %s, available_reservations = %s
            WHERE id = %s
        """, (new_capacity, available_reservations, restaurant['id']))
        
        # Return booking confirmation as structured data
        return {
            "status": "success",
            "message": "Reservation created successfully",
            "data": {
                "confirmation_id": reservation_id,
                "restaurant": {
                    "id": restaurant['id'],
                    "name": restaurant['name'],
                    "address": restaurant['address'],
                    "city": restaurant['city']
                },
                "reservation": {
                    "date": datetime.now().strftime('%Y-%m-%d'),
                    "time": reservation_time,
                    "party_size": party_size,
                    "customer_name": customer_name,
                    "contact_number": contact_number
                }
            }
        }
    
    except Exception as e:
        return {"status": "error", "message": str(e), "data": None}
    
    finally:
        if conn:
            conn.close()

@tool
def check_reservation(confirmation_number: int):
    """
    Check the details of an existing reservation.
    
    Args:
        confirmation_number (int): The reservation confirmation number.
        
    Returns:
        dict: JSON-formatted data with reservation details.
    """
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database connection error", "data": None}
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Query to get reservation details with restaurant information
        query = """
            SELECT r.id, r.customer_name, r.contact_number, r.party_size, r.reservation_time, 
                   r.created_at, res.name as restaurant_name, res.address, res.city
            FROM reservations r
            JOIN restaurants res ON r.restaurant_id = res.id
            WHERE r.id = %s
        """
        
        cur.execute(query, (confirmation_number,))
        reservation = cur.fetchone()
        
        if not reservation:
            return {
                "status": "not_found",
                "message": "Reservation not found",
                "confirmation_number": confirmation_number,
                "data": None
            }
        
        # Convert to dict for JSON serialization
        reservation_data = dict(reservation)
        # Convert datetime objects to strings
        for key, value in reservation_data.items():
            if isinstance(value, datetime):
                reservation_data[key] = value.isoformat()
        
        return {
            "status": "success",
            "data": reservation_data
        }
    
    except Exception as e:
        return {"status": "error", "message": str(e), "data": None}
    
    finally:
        if conn:
            conn.close()

@tool
def validate_booking_info(restaurant_name: str = None, reservation_time: str = None, party_size: int = None, customer_name: str = None, contact_number: str = None, city: str = None):
    """
    Validates if all required booking information is available. Use this before attempting to book a restaurant.
    
    Args:
        restaurant_name (str, optional): The name of the restaurant.
        reservation_time (str, optional): The desired reservation time (e.g., "7:00 PM").
        party_size (int, optional): The number of people in the party.
        customer_name (str, optional): The name of the customer making the reservation.
        contact_number (str, optional): Contact phone number for the reservation.
        city (str, optional): The city where the restaurant is located.
        
    Returns:
        dict: JSON-formatted data with validation results.
    """
    missing_fields = []
    
    if not restaurant_name:
        missing_fields.append("restaurant_name")
    
    if not reservation_time:
        missing_fields.append("reservation_time")
    
    if not party_size:
        missing_fields.append("party_size")
    else:
        # Validate that party_size is a number
        try:
            party_size = int(party_size)
        except (ValueError, TypeError):
            missing_fields.append("valid_party_size")
            # Update the party_size to None so it doesn't appear in provided_fields
            party_size = None
    
    if not customer_name:
        missing_fields.append("customer_name")
    
    if not contact_number:
        missing_fields.append("contact_number")
    
    if not city:
        missing_fields.append("city")
    
    provided_fields = {
        "restaurant_name": restaurant_name,
        "reservation_time": reservation_time,
        "party_size": party_size,
        "customer_name": customer_name,
        "contact_number": contact_number,
        "city": city
    }
    
    # Filter out None values
    provided_fields = {k: v for k, v in provided_fields.items() if v is not None}
    
    return {
        "status": "missing_fields" if missing_fields else "complete",
        "missing_fields": missing_fields,
        "provided_fields": provided_fields
    }

@tool
def progressive_restaurant_inquiry(query: str, known_info: dict = None):
    """
    Analyzes a restaurant inquiry and determines what information to ask for next.
    
    Args:
        query (str): The user's query about restaurants.
        known_info (dict, optional): Information already gathered from the user.
        
    Returns:
        dict: JSON-formatted data with inquiry analysis and next steps.
    """
    if not known_info:
        known_info = {}
    
    # Determine what's missing and what to ask next
    missing_info = []
    
    if 'city' not in known_info:
        missing_info.append("city")
    
    if 'party_size' not in known_info and ('book' in query.lower() or 'reservation' in query.lower()):
        missing_info.append("party_size")
    
    if 'cuisine' not in known_info:
        missing_info.append("cuisine")
    
    if 'time' not in known_info and ('book' in query.lower() or 'reservation' in query.lower()):
        missing_info.append("time")
    
    return {
        "query": query,
        "known_info": known_info,
        "missing_info": missing_info,
        "is_booking_intent": 'book' in query.lower() or 'reservation' in query.lower(),
        "next_field_to_ask": missing_info[0] if missing_info else None,
        "can_recommend": 'city' in known_info
    }

@tool
def get_available_options():
    """
    Fetches available cities, cuisines, and moods from the database.
    Use this to suggest valid options to users.
    
    Returns:
        dict: JSON-formatted data with available options
    """
    return {
        "status": "success",
        "data": {
            "cities": sorted(list(AVAILABLE_CITIES)),
            "cuisines": sorted(list(AVAILABLE_CUISINES)),
            "moods": sorted(list(AVAILABLE_MOODS))
        }
    }

def main():
    # Initialize database tables and metadata
    initialize_database_tables()
    initialize_db_metadata()
    
    # Create a ToolAgent with the restaurant tools
    agent = ToolAgent(
        tools=[
            search_restaurants,
            get_restaurant_details,
            get_recommendations,
            progressive_restaurant_inquiry,
            validate_booking_info,
            book_restaurant,
            check_reservation,
            get_available_options
        ],
        model="llama3-8b-8192",  # Can be changed to other Groq models
    )
    
    fancy_print("Restaurant Recommendation & Booking Assistant")
    print(Fore.YELLOW + "I can help you find restaurants, get recommendations, and make reservations.")
    print(Fore.YELLOW + "What can I help you with today? (type 'exit' to quit)\n")
    print(Fore.YELLOW + "Example queries:")
    print(Fore.YELLOW + "- Find Italian restaurants in New York")
    print(Fore.YELLOW + "- Good romantic places in Chicago")
    print(Fore.YELLOW + "- Business meeting restaurant in Boston")
    print(Fore.YELLOW + "- Book a table for 4 tomorrow at Delmonico's")
    print(Fore.YELLOW + "- Check reservation #12345\n")
    
    while True:
        user_input = input(Fore.GREEN + "You: " + Fore.RESET)
        if user_input.lower() in ["exit", "quit"]:
            break
        
        try:
            response = agent.run(user_input)
            print(Fore.BLUE + "Assistant: " + Fore.RESET + response)
        except Exception as e:
            # Handle exceptions gracefully
            error_message = str(e)
            print(Fore.RED + "Error: " + Fore.RESET + error_message)
            print(Fore.BLUE + "Assistant: " + Fore.RESET + 
                  "I'm having trouble processing that request. Could you try again with more details?")


if __name__ == "__main__":
    main() 