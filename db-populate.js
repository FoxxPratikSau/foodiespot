require('dotenv').config();
const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

// Read restaurant data from JSON file
const restaurantData = JSON.parse(fs.readFileSync(path.join(__dirname, 'resturant.json'), 'utf8'));

// Create a connection pool to the Neon database
const pool = new Pool({
  connectionString: process.env.NEON_DB_URL,
});

// Function to create the restaurants table if it doesn't exist
async function createTable() {
  const createTableQuery = `
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
  `;
  
  try {
    await pool.query(createTableQuery);
    console.log('Table created or already exists');
  } catch (error) {
    console.error('Error creating table:', error);
    throw error;
  }
}

// Function to insert restaurant data
async function insertRestaurants() {
  // First, clear existing data to avoid duplicates
  try {
    await pool.query('TRUNCATE TABLE restaurants RESTART IDENTITY');
    console.log('Cleared existing restaurant data');
  } catch (error) {
    console.error('Error clearing existing data:', error);
    throw error;
  }

  // Insert each restaurant
  for (const restaurant of restaurantData) {
    const insertQuery = `
      INSERT INTO restaurants (
        name, city, address, cuisine, seating_capacity, 
        available_capacity, available_reservations, mood
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    `;
    
    const values = [
      restaurant.name,
      restaurant.city,
      restaurant.address,
      restaurant.cuisine,
      restaurant.seatingCapacity,
      restaurant.availableCapacity,
      restaurant.availableReservations,
      restaurant.mood
    ];
    
    try {
      await pool.query(insertQuery, values);
      console.log(`Inserted restaurant: ${restaurant.name}`);
    } catch (error) {
      console.error(`Error inserting restaurant ${restaurant.name}:`, error);
      throw error;
    }
  }
}

// Additional restaurants for more variety
const additionalRestaurants = [
  {
    name: "Spice Garden",
    city: "New York",
    address: "123 Curry Lane",
    cuisine: "Indian",
    seatingCapacity: 75,
    availableCapacity: 25,
    availableReservations: ["12:00 PM", "6:30 PM", "8:30 PM"],
    mood: "exotic"
  },
  {
    name: "Sushi Supreme",
    city: "Los Angeles",
    address: "456 Ocean Drive",
    cuisine: "Japanese",
    seatingCapacity: 60,
    availableCapacity: 15,
    availableReservations: ["1:00 PM", "7:00 PM", "9:00 PM"],
    mood: "tranquil"
  },
  {
    name: "Thai Delight",
    city: "Chicago",
    address: "789 Spice Street",
    cuisine: "Thai",
    seatingCapacity: 70,
    availableCapacity: 30,
    availableReservations: ["12:30 PM", "6:00 PM", "8:00 PM"],
    mood: "cozy"
  },
  {
    name: "Mediterranean Oasis",
    city: "Miami",
    address: "101 Beach Boulevard",
    cuisine: "Mediterranean",
    seatingCapacity: 90,
    availableCapacity: 40,
    availableReservations: ["1:30 PM", "7:30 PM", "9:30 PM"],
    mood: "breezy"
  },
  {
    name: "Parisian Corner",
    city: "San Francisco",
    address: "202 Golden Gate Ave",
    cuisine: "French",
    seatingCapacity: 65,
    availableCapacity: 20,
    availableReservations: ["12:00 PM", "6:30 PM", "8:30 PM"],
    mood: "romantic"
  }
];

// Function to add additional restaurants
async function addMoreRestaurants() {
  for (const restaurant of additionalRestaurants) {
    const insertQuery = `
      INSERT INTO restaurants (
        name, city, address, cuisine, seating_capacity, 
        available_capacity, available_reservations, mood
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    `;
    
    const values = [
      restaurant.name,
      restaurant.city,
      restaurant.address,
      restaurant.cuisine,
      restaurant.seatingCapacity,
      restaurant.availableCapacity,
      restaurant.availableReservations,
      restaurant.mood
    ];
    
    try {
      await pool.query(insertQuery, values);
      console.log(`Inserted additional restaurant: ${restaurant.name}`);
    } catch (error) {
      console.error(`Error inserting additional restaurant ${restaurant.name}:`, error);
      throw error;
    }
  }
}

// Main function to run the database population
async function populateDatabase() {
  try {
    await createTable();
    await insertRestaurants();
    await addMoreRestaurants();
    console.log('Database population completed successfully!');
  } catch (error) {
    console.error('Database population failed:', error);
  } finally {
    // Close the pool
    await pool.end();
  }
}

// Run the population script
populateDatabase(); 