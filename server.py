"""
Montreal Travel Companion API
A context-aware travel recommendation system that provides personalized suggestions
based on location, weather, time, and user preferences.
"""

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import httpx
import os
import logging
from math import radians, sin, cos, sqrt, atan2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
	title="Montreal Travel Companion API",
	description="Context-aware travel recommendations based on location, weather, and time",
	version="1.0.0"
)

# CORS Configuration
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # In production, specify exact origins
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# API Keys
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")

# In-memory storage (use database in production)
user_preferences_store: Dict[str, dict] = {}
user_last_context: Dict[str, dict] = {}
user_notifications: Dict[str, List[dict]] = {}

# Constants
LOCATION_CHANGE_THRESHOLD_KM = 0.25  # Notify if user moves more than 500m
TEMPERATURE_CHANGE_THRESHOLD_C = 1  # Notify if temperature changes by 5°C
NOTIFICATION_HISTORY_LIMIT = 50  # Keep last 50 notifications
OUTDOOR_MIN_TEMP_C = -25  # Adjusted for Montreal winters
OUTDOOR_MAX_TEMP_C = 38  # Adjusted for Montreal summers

# Montreal boundaries for location validation
MONTREAL_BOUNDS = {
	"min_lat": 45.4,
	"max_lat": 45.7,
	"min_lon": -73.9,
	"max_lon": -73.4,
	"center_lat": 45.5017,
	"center_lon": -73.5673
}


# ============================================================================
# WebSocket Connection Manager
# ============================================================================

class ConnectionManager:
	"""Manages WebSocket connections for real-time notifications"""
	
	def __init__(self):
		self.active_connections: Dict[str, WebSocket] = {}
	
	async def connect(self, user_id: str, websocket: WebSocket) -> None:
		"""Accept and store a new WebSocket connection"""
		await websocket.accept()
		self.active_connections[user_id] = websocket
		logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections)}")
	
	def disconnect(self, user_id: str) -> None:
		"""Remove a WebSocket connection"""
		if user_id in self.active_connections:
			del self.active_connections[user_id]
			logger.info(f"User {user_id} disconnected. Total connections: {len(self.active_connections)}")
	
	async def send_notification(self, user_id: str, notification: dict) -> bool:
		"""Send a notification to a specific user"""
		if user_id in self.active_connections:
			try:
				await self.active_connections[user_id].send_json(notification)
				logger.info(f"Notification sent to user {user_id}: {notification.get('type', 'unknown')}")
				return True
			except Exception as e:
				logger.error(f"Error sending notification to {user_id}: {e}")
				self.disconnect(user_id)
				return False
		return False
	
	async def broadcast(self, notification: dict, exclude_user: Optional[str] = None) -> int:
		"""Broadcast a notification to all connected users"""
		count = 0
		for user_id in list(self.active_connections.keys()):
			if user_id != exclude_user:
				if await self.send_notification(user_id, notification):
					count += 1
		return count


manager = ConnectionManager()


# ============================================================================
# Pydantic Models
# ============================================================================

class LocationData(BaseModel):
	"""Geographic location coordinates"""
	latitude: float = Field(..., ge=-90, le=90, description="Latitude between -90 and 90")
	longitude: float = Field(..., ge=-180, le=180, description="Longitude between -180 and 180")


class UserPreferences(BaseModel):
	"""User preferences for activities and dining"""
	user_id: str = Field(..., min_length=1, description="Unique user identifier")
	activity_type: str = Field(..., description="Preferred activity type: indoor or outdoor")
	meal_times: Dict[str, str] = Field(default_factory=dict, description="Meal times in HH:MM format")
	preferred_cuisines: List[str] = Field(default_factory=list, description="List of preferred cuisines")
	
	@validator('activity_type')
	def validate_activity_type(cls, v):
		if v not in ['indoor', 'outdoor']:
			raise ValueError('activity_type must be either "indoor" or "outdoor"')
		return v
	
	@validator('meal_times')
	def validate_meal_times(cls, v):
		valid_meals = ['breakfast', 'lunch', 'dinner']
		for meal, time in v.items():
			if meal not in valid_meals:
				raise ValueError(f'Invalid meal type: {meal}. Must be one of {valid_meals}')
			try:
				hour, minute = time.split(':')
				if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
					raise ValueError
			except:
				raise ValueError(f'Invalid time format for {meal}: {time}. Use HH:MM format')
		return v


class ManualContextData(BaseModel):
	"""Manual context override for testing"""
	time_hour: Optional[int] = Field(None, ge=0, le=23, description="Hour of day (0-23)")
	weather: Optional[str] = Field(None, description="Weather condition")
	temperature: Optional[int] = Field(None, description="Temperature in Celsius")
	latitude: Optional[float] = Field(None, ge=-90, le=90)
	longitude: Optional[float] = Field(None, ge=-180, le=180)
	
	@validator('weather')
	def validate_weather(cls, v):
		if v is not None:
			valid_weather = ['sunny', 'cloudy', 'rainy', 'snowy']
			if v not in valid_weather:
				raise ValueError(f'weather must be one of: {", ".join(valid_weather)}')
		return v


class RecommendationRequest(BaseModel):
	"""Request for recommendations"""
	preferences: UserPreferences
	location: LocationData


class ManualRecommendationRequest(BaseModel):
	"""Request for recommendations with manual context override"""
	preferences: UserPreferences
	location: LocationData
	manual_context: Optional[ManualContextData] = None


class ContextUpdate(BaseModel):
	"""Context update request"""
	user_id: str = Field(..., min_length=1)
	location: Optional[LocationData] = None
	current_time: Optional[int] = Field(None, ge=0, le=23)
	force_check: bool = Field(False, description="Force notification check even if no change")


class Recommendation(BaseModel):
	"""Recommendation response model"""
	name: str
	type: str
	description: str
	address: str
	reason: str
	distance: Optional[float] = None
	rating: Optional[float] = None
	latitude: Optional[float] = None
	longitude: Optional[float] = None


# ============================================================================
# Constants - Category Mappings
# ============================================================================

CUISINE_CATEGORIES = {
	"Italian": "italian restaurant",
	"Burgers": "burger restaurant",
	"Pizza": "pizza restaurant",
	"Asian": "asian restaurant",
	"French": "french restaurant",
	"Mexican": "mexican restaurant",
	"Cafe": "cafe coffee shop",
	"Chinese": "chinese restaurant",
	"Japanese": "japanese restaurant sushi",
	"Indian": "indian restaurant",
	"Thai": "thai restaurant",
	"Korean": "korean restaurant",
	"Mediterranean": "mediterranean restaurant",
	"Vietnamese": "vietnamese restaurant",
	"Greek": "greek restaurant",
	"Seafood": "seafood restaurant",
	"Steakhouse": "steakhouse"
}

# Updated activity categories with descriptive names
ACTIVITY_CATEGORIES = {
	"indoor": {
		"early_morning": [
			"gym", "fitness center", "yoga studio"
		],
		"morning": [
			"museum", "art gallery", "library", "bookstore", 
			"shopping mall", "aquarium"
		],
		"noon": [
			"arcade", "amusement center", "bowling alley", "shopping mall",
			"movie theater", "museum", "art gallery", "aquarium", "spa"
		],
		"evening": [
			"bowling alley", "movie theater", "arcade", "casino",
			"shopping mall", "gym", "spa"
		],
		"night": [
			"night club", "casino", "movie theater", "bar"
		]
	},

	"outdoor": {
		"early_morning": [
			"park", "hiking trail", "nature preserve", "garden", "bike trail"
		],
		"morning": [
			"tourist attraction", "zoo", "botanical garden", "park", 
			"marina", "scenic viewpoint"
		],
		"noon": [
			"beach", "water park", "theme park", "zoo", "tourist attraction",
			"stadium", "sports complex", "marina", "playground"
		],
		"evening": [
			"park", "tourist attraction", "stadium", "sports complex",
			"marina", "theme park"
		],
		"night": [
			"night club", "casino"
		]
	}
}


# ============================================================================
# Utility Functions
# ============================================================================

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
	"""
	Calculate distance between two coordinates using Haversine formula
	Returns distance in kilometers
	"""
	R = 6371  # Earth's radius in kilometers
	
	lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
	dlat = lat2 - lat1
	dlon = lon2 - lon1
	
	a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
	c = 2 * atan2(sqrt(a), sqrt(1-a))
	
	return R * c


def is_in_montreal_area(lat: float, lon: float) -> bool:
	"""Check if coordinates are within Montreal metropolitan area"""
	return (MONTREAL_BOUNDS["min_lat"] <= lat <= MONTREAL_BOUNDS["max_lat"] and
			MONTREAL_BOUNDS["min_lon"] <= lon <= MONTREAL_BOUNDS["max_lon"])


def get_time_period(hour: int) -> str:
	"""Get human-readable time period for a given hour"""
	if 5 <= hour < 8:
		return "Early Morning"
	elif 8 <= hour < 12:
		return "Morning"
	elif 12 <= hour < 17:
		return "Afternoon"
	elif 17 <= hour < 21:
		return "Evening"
	elif 21 <= hour < 24 or 0 <= hour < 2:
		return "Night"
	else:
		return "Late Night"


def get_time_period_key(hour: int) -> str:
	"""Get time period key for category lookup"""
	if 5 <= hour < 8:
		return "early_morning"
	elif 8 <= hour < 12:
		return "morning"
	elif 12 <= hour < 17:
		return "noon"
	elif 17 <= hour < 21:
		return "evening"
	else:
		return "night"


def get_meal_type(current_hour: int, meal_times: dict) -> Optional[str]:
	"""Determine if current time matches a meal time"""
	for meal, time_str in meal_times.items():
		try:
			meal_hour = int(time_str.split(":")[0])
			if abs(current_hour - meal_hour) <= 1:
				return meal
		except (ValueError, IndexError):
			logger.warning(f"Invalid meal time format: {meal}: {time_str}")
			continue
	return None


def is_outdoor_suitable(weather: str, temperature: int) -> bool:
	"""Check if weather is suitable for outdoor activities"""
	if temperature < OUTDOOR_MIN_TEMP_C or temperature > OUTDOOR_MAX_TEMP_C:
		return False
	
	if weather == "rainy" and temperature < 10:
		return False
	
	return True


# ============================================================================
# External API Functions
# ============================================================================

async def get_weather(lat: float, lon: float) -> dict:
	"""
	Get real weather data from OpenWeatherMap API
	Returns simplified weather data with fallback
	"""
	async with httpx.AsyncClient() as client:
		response = await client.get(
			"https://api.openweathermap.org/data/2.5/weather",
			params={
				"lat": lat,
				"lon": lon,
				"appid": OPENWEATHER_API_KEY,
				"units": "metric"
			},
			timeout=10.0
		)
		
		if response.status_code == 200:
			data = response.json()
			weather_main = data["weather"][0]["main"].lower()
			
			# Map OpenWeather conditions to simple categories
			weather_map = {
				"rain": "rainy",
				"drizzle": "rainy",
				"thunderstorm": "rainy",
				"snow": "snowy",
				"clouds": "cloudy",
				"mist": "cloudy",
				"fog": "cloudy",
			}
			weather_condition = weather_map.get(weather_main, "sunny")
			
			return {
				"weather": weather_condition,
				"temperature": round(data["main"]["temp"]),
				"description": data["weather"][0]["description"],
				"humidity": data["main"]["humidity"],
				"wind_speed": data["wind"]["speed"]
			}
		else:
			logger.error(f"Weather API error: {response.status_code}")


async def search_places_nearby(
	lat: float, 
	lon: float, 
	search_terms: List[str], 
	limit: int = 20
) -> List[dict]:
	"""
	Search for places using Google Places API
	Returns list of places with details
	"""
	
	if not search_terms:
		search_query = "restaurant OR attraction OR museum OR park"
	else:
		search_query = " OR ".join(search_terms)
	
	params = {
		"query": search_query,
		"location": f"{lat},{lon}",
		"radius": 5000,  # 5km radius
		"key": GOOGLE_PLACES_API_KEY
	}
	
	logger.info(f"Searching Google Places: {search_query}")
	

	async with httpx.AsyncClient() as client:
		response = await client.get(
			"https://maps.googleapis.com/maps/api/place/textsearch/json",
			params=params,
			timeout=10.0
		)
		
		if response.status_code != 200:
			raise HTTPException(
				status_code=response.status_code,
				detail=f"Google Places API HTTP error: {response.status_code}"
			)
		
		data = response.json()
		status = data.get("status")
		
		if status == "OK":
			results = data.get("results", [])
			logger.info(f"Found {len(results)} places")
			
			places = []
			for result in results[:limit]:
				place_lat = result.get("geometry", {}).get("location", {}).get("lat")
				place_lon = result.get("geometry", {}).get("location", {}).get("lng")
				
				distance = 0
				if place_lat and place_lon:
					distance = calculate_distance(lat, lon, place_lat, place_lon)
				
				places.append({
					"name": result.get("name", "Unknown"),
					"address": result.get("formatted_address", "Address not available"),
					"latitude": place_lat,
					"longitude": place_lon,
					"distance": int(distance * 1000),  # Convert to meters
					"categories": result.get("types", [])[:3],
					"rating": result.get("rating")
				})
			
			return places
		
		elif status == "ZERO_RESULTS":
			logger.info("No places found")
			return []
		
		elif status == "REQUEST_DENIED":
			error_msg = data.get('error_message', 'Check API key and ensure Places API is enabled')
			raise HTTPException(status_code=403, detail=f"Google Places API request denied: {error_msg}")
		
		else:
			error_msg = data.get('error_message', 'Unknown error')
			raise HTTPException(status_code=500, detail=f"Google Places API error: {status} - {error_msg}")


def build_google_search_query(preferences: UserPreferences, meal_type: Optional[str] = None) -> List[str]:
	"""
	Build Google Places search query based on user preferences
	IMPROVED: Only returns restaurant/cafe queries when it's meal time
	"""
	search_terms = []
	
	# Only search for restaurants/cafes if it's actually meal time
	if meal_type:
		# Add cuisine-specific searches if user has preferences
		if preferences.preferred_cuisines:
			for cuisine in preferences.preferred_cuisines:
				if cuisine in CUISINE_CATEGORIES:
					search_terms.append(CUISINE_CATEGORIES[cuisine])
		
		# Add general restaurant/cafe terms for meal time
		# These ensure we get food options even if no specific cuisine is preferred
		if meal_type == "breakfast":
			search_terms.extend([
				"breakfast restaurant", 
				"cafe", 
				"coffee shop", 
				"brunch restaurant", 
				"bakery",
				"breakfast diner"
			])
		elif meal_type == "lunch":
			search_terms.extend([
				"lunch restaurant", 
				"restaurant", 
				"bistro", 
				"cafe",
				"fast food",
				"deli"
			])
		elif meal_type == "dinner":
			search_terms.extend([
				"dinner restaurant", 
				"restaurant", 
				"fine dining", 
				"steakhouse",
				"gastropub"
			])
	
	# Return empty list if not meal time - no restaurant searches
	return search_terms


def get_activity_search_terms(activity_type: str, time_period: str, weather: Optional[str] = None, temperature: Optional[int] = None) -> List[str]:
	"""Get activity search terms based on preferences, time, and weather"""
	
	if activity_type == "indoor":
		# Indoor activities - only consider time of day
		time_key = time_period
		if time_key in ACTIVITY_CATEGORIES["indoor"]:
			return ACTIVITY_CATEGORIES["indoor"][time_key]
		return ACTIVITY_CATEGORIES["indoor"]["morning"]  # Default fallback
	
	else:  # outdoor
		# Outdoor activities - consider both time and weather
		time_key = time_period
		
		# First check if weather is suitable for outdoor
		if weather and temperature is not None:
			if not is_outdoor_suitable(weather, temperature):
				logger.info(f"Weather not suitable for outdoor ({weather}, {temperature}°C). Suggesting indoor alternatives.")
				# Return indoor alternatives
				if time_key in ACTIVITY_CATEGORIES["indoor"]:
					return ACTIVITY_CATEGORIES["indoor"][time_key]
				return ACTIVITY_CATEGORIES["indoor"]["morning"]
		
		# Get base outdoor activities for time of day
		if time_key not in ACTIVITY_CATEGORIES["outdoor"]:
			time_key = "morning"  # Default fallback
		
		outdoor_activities = ACTIVITY_CATEGORIES["outdoor"][time_key]
		
		# Filter based on weather conditions
		if weather and temperature is not None:
			filtered = filter_activities_by_weather(outdoor_activities, weather, temperature)
			return filtered if filtered else outdoor_activities
		
		return outdoor_activities


def filter_activities_by_weather(activities: List[str], weather: str, temperature: int) -> List[str]:
	"""Filter outdoor activities based on weather conditions"""
	
	# Define weather-sensitive activities
	water_activities = ["beach", "water park", "marina", "boat rental"]
	cold_weather_activities = ["ice skating", "ski area", "sledding"]
	rain_sensitive = ["hiking trail", "park", "playground", "sports complex", "stadium"]
	
	filtered = []
	
	for activity in activities:
		activity_lower = activity.lower()
		
		# Snowy or very cold weather
		if weather == "snowy" or temperature < -5:
			# Prefer cold weather activities
			if any(cold in activity_lower for cold in cold_weather_activities):
				filtered.append(activity)
			elif not any(water in activity_lower for water in water_activities):
				filtered.append(activity)
		
		# Rainy weather
		elif weather == "rainy":
			# Exclude most outdoor activities except covered areas
			if any(term in activity_lower for term in ["mall", "market", "covered", "indoor"]):
				filtered.append(activity)
			elif not any(rain in activity_lower for rain in rain_sensitive):
				filtered.append(activity)
		
		# Cold but not snowy
		elif temperature < 10:
			# Exclude water activities
			if not any(water in activity_lower for water in water_activities):
				filtered.append(activity)
		
		# Hot weather
		elif temperature > 28:
			# Prefer water activities and shaded areas
			filtered.append(activity)
		
		# Normal weather
		else:
			filtered.append(activity)
	
	return filtered if filtered else activities  # Return all if no matches


def get_weather_activity_impact(old_weather: str, new_weather: str) -> dict:
	"""Determine impact of weather change on activities"""
	weather_transitions = {
		("sunny", "rainy"): {
			"message": "Weather changed to rainy. Consider indoor activities.",
			"suggestion": "indoor"
		},
		("sunny", "snowy"): {
			"message": "Snow has started! Winter activities are now available.",
			"suggestion": "winter_sports"
		},
		("rainy", "sunny"): {
			"message": "Rain has stopped! Great time for outdoor activities.",
			"suggestion": "outdoor"
		},
		("snowy", "sunny"): {
			"message": "Snow has cleared. Enjoy outdoor activities!",
			"suggestion": "outdoor"
		},
		("cloudy", "sunny"): {
			"message": "Sun is out! Perfect for outdoor exploration.",
			"suggestion": "outdoor"
		},
		("sunny", "cloudy"): {
			"message": "Weather is now cloudy but still good for activities.",
			"suggestion": "outdoor"
		}
	}
	
	return weather_transitions.get(
		(old_weather, new_weather),
		{
			"message": f"Weather changed from {old_weather} to {new_weather}.",
			"suggestion": "check_recommendations"
		}
	)


# ============================================================================
# Context Analysis Functions
# ============================================================================


def get_suitable_activities_by_weather(weather: str, temperature: int, activity_type: str) -> List[str]:
	"""Get suitable activity categories based on weather"""
	if activity_type == "indoor":
		# Indoor activities not affected by weather
		return []
	
	# For outdoor, this is now handled in get_activity_search_terms
	return []


def get_suitable_activities_by_time(current_hour: int, activity_type: str) -> dict:
	"""Get suitable activities based on time of day"""
	time_key = get_time_period_key(current_hour)
	
	if activity_type == "indoor":
		activities = ACTIVITY_CATEGORIES["indoor"].get(time_key, ACTIVITY_CATEGORIES["indoor"]["morning"])
		return {
			"categories": activities,
			"reason": f"{get_time_period(current_hour)} {activity_type} activities"
		}
	else:  # outdoor
		activities = ACTIVITY_CATEGORIES["outdoor"].get(time_key, ACTIVITY_CATEGORIES["outdoor"]["morning"])
		return {
			"categories": activities,
			"reason": f"{get_time_period(current_hour)} {activity_type} activities"
		}


# ============================================================================
# Notification Functions
# ============================================================================

async def detect_context_changes(user_id: str, new_context: dict, preferences: dict) -> List[dict]:
	"""Detect context changes and generate notifications"""
	notifications = []
	
	if user_id not in user_last_context:
		user_last_context[user_id] = new_context
		return notifications
	
	old_context = user_last_context[user_id]
	
	# Location change
	if "location" in new_context and "location" in old_context:
		old_lat = old_context["location"]["latitude"]
		old_lon = old_context["location"]["longitude"]
		new_lat = new_context["location"]["latitude"]
		new_lon = new_context["location"]["longitude"]
		
		distance_change = calculate_distance(old_lat, old_lon, new_lat, new_lon)
		
		if distance_change > LOCATION_CHANGE_THRESHOLD_KM:
			notifications.append({
				"type": "location_change",
				"title": "Location Changed",
				"message": f"You've moved {round(distance_change, 2)} km. Check out nearby recommendations!",
				"distance_moved": round(distance_change, 2),
				"timestamp": datetime.now().isoformat()
			})
	
	# Time period change
	if "time_hour" in new_context and "time_hour" in old_context:
		old_period = get_time_period(old_context["time_hour"])
		new_period = get_time_period(new_context["time_hour"])
		
		if old_period != new_period:
			notifications.append({
				"type": "time_period_change",
				"title": f"{new_period} Activities Available",
				"message": f"It's now {new_period.lower()}! Discover activities for this time of day.",
				"old_period": old_period,
				"new_period": new_period,
				"timestamp": datetime.now().isoformat()
			})
		
		# Meal time notification
		if preferences and "meal_times" in preferences:
			new_hour = new_context["time_hour"]
			old_hour = old_context["time_hour"]
			
			meal_type = get_meal_type(new_hour, preferences["meal_times"])
			old_meal_type = get_meal_type(old_hour, preferences["meal_times"])
			
			if meal_type and meal_type != old_meal_type:
				notifications.append({
					"type": "meal_time",
					"title": f"Time for {meal_type.capitalize()}!",
					"message": f"Check out restaurant recommendations for {meal_type} nearby.",
					"meal_type": meal_type,
					"timestamp": datetime.now().isoformat()
				})
	
	# Weather change
	if "weather" in new_context and "weather" in old_context:
		if old_context["weather"] != new_context["weather"]:
			weather_impact = get_weather_activity_impact(
				old_context["weather"],
				new_context["weather"]
			)
			notifications.append({
				"type": "weather_change",
				"title": "Weather Update",
				"message": weather_impact["message"],
				"old_weather": old_context["weather"],
				"new_weather": new_context["weather"],
				"activity_suggestion": weather_impact["suggestion"],
				"timestamp": datetime.now().isoformat()
			})
	
	# Temperature change
	if "temperature" in new_context and "temperature" in old_context:
		temp_diff = abs(new_context["temperature"] - old_context["temperature"])
		
		if temp_diff >= TEMPERATURE_CHANGE_THRESHOLD_C:
			notifications.append({
				"type": "temperature_change",
				"title": "Temperature Changed",
				"message": f"Temperature changed from {old_context['temperature']}°C to {new_context['temperature']}°C.",
				"old_temperature": old_context["temperature"],
				"new_temperature": new_context["temperature"],
				"timestamp": datetime.now().isoformat()
			})
	
	# Update stored context
	user_last_context[user_id] = new_context
	
	# Store in history
	if notifications:
		if user_id not in user_notifications:
			user_notifications[user_id] = []
		user_notifications[user_id].extend(notifications)
		user_notifications[user_id] = user_notifications[user_id][-NOTIFICATION_HISTORY_LIMIT:]
	
	return notifications


async def store_notification(user_id: str, notification: dict) -> None:
	"""Store a notification in history"""
	if user_id not in user_notifications:
		user_notifications[user_id] = []
	user_notifications[user_id].append(notification)
	user_notifications[user_id] = user_notifications[user_id][-NOTIFICATION_HISTORY_LIMIT:]


# ============================================================================
# Recommendation Engine
# ============================================================================

async def generate_recommendations(
	preferences: UserPreferences,
	location: LocationData,
	current_hour: int,
	weather_data: dict
) -> List[Recommendation]:
	"""
	Enhanced recommendation engine with better meal/activity separation
	IMPROVED: Clearer separation between meal and activity recommendations
	"""
	recommendations = []
	
	# Check if it's meal time
	meal_type = get_meal_type(current_hour, preferences.meal_times)
	is_meal_time = meal_type is not None
	
	# PART 1: Restaurant recommendations (ONLY if meal time)
	if is_meal_time:
		logger.info(f"Meal time detected: {meal_type}")
		
		# Build restaurant/cafe search query
		restaurant_search_terms = build_google_search_query(preferences, meal_type)
		
		if restaurant_search_terms:
			try:
				logger.info(f"Searching for restaurants: {restaurant_search_terms}")
				restaurants = await search_places_nearby(
					location.latitude,
					location.longitude,
					restaurant_search_terms,
					limit=30
				)
				
				# Filter and add restaurants
				for restaurant in restaurants[:8]:
					# Additional filtering to ensure it's actually a restaurant/cafe
					categories_str = " ".join(restaurant.get("categories", [])).lower()
					name_lower = restaurant["name"].lower()
					
					# Make sure it's food-related
					is_food_place = any(term in categories_str or term in name_lower 
									   for term in ["restaurant", "cafe", "food", "dining", 
									               "bakery", "bistro", "eatery", "coffee"])
					
					if is_food_place:
						cuisine_desc = ", ".join(preferences.preferred_cuisines) if preferences.preferred_cuisines else "Various"
						recommendations.append(Recommendation(
							name=restaurant["name"],
							type="restaurant",
							description=", ".join(restaurant["categories"][:3]),
							address=restaurant["address"],
							reason=f"Perfect for {meal_type} - {cuisine_desc} cuisine",
							distance=restaurant["distance"],
							latitude=restaurant["latitude"],
							longitude=restaurant["longitude"],
							rating=restaurant.get("rating")
						))
					
			except HTTPException as e:
				logger.error(f"Error fetching restaurants: {e.detail}")
	
	# PART 2: Activity recommendations (ONLY if NOT meal time or if we need more recommendations)
	if not is_meal_time or len(recommendations) < 10:
		time_key = get_time_period_key(current_hour)
		
		# Get activity search terms (excludes restaurants when not meal time)
		activity_search_terms = get_activity_search_terms(
			preferences.activity_type,
			time_key,
			weather_data["weather"],
			weather_data["temperature"]
		)
		
		if activity_search_terms:
			try:
				logger.info(f"Searching for activities (non-food): {activity_search_terms}")
				activities = await search_places_nearby(
					location.latitude,
					location.longitude,
					activity_search_terms,
					limit=30
				)
				
				# Filter out any restaurants that might have slipped through
				for activity in activities:
					categories_str = " ".join(activity.get("categories", [])).lower()
					name_lower = activity["name"].lower()
					
					# Exclude if it's primarily a food place
					is_food_place = any(term in categories_str or term in name_lower 
									   for term in ["restaurant", "cafe", "dining", "cuisine", 
									               "bistro", "eatery", "food"])
					
					if not is_food_place:
						# Build reason based on conditions
						time_based = get_suitable_activities_by_time(current_hour, preferences.activity_type)
						reason = time_based["reason"]
						
						if preferences.activity_type == "outdoor":
							if not is_outdoor_suitable(weather_data["weather"], weather_data["temperature"]):
								reason += " (showing indoor alternatives due to weather)"
							else:
								reason += f" (weather: {weather_data['weather']}, {weather_data['temperature']}°C)"
						
						recommendations.append(Recommendation(
							name=activity["name"],
							type=activity["categories"][0] if activity["categories"] else "activity",
							description=", ".join(activity["categories"][:3]),
							address=activity["address"],
							reason=reason,
							distance=activity["distance"],
							latitude=activity["latitude"],
							longitude=activity["longitude"],
							rating=activity.get("rating")
						))
						
						# Stop when we have enough recommendations
						if len(recommendations) >= 10:
							break
					
			except HTTPException as e:
				logger.error(f"Error fetching activities: {e.detail}")
	
	logger.info(f"Returning {len(recommendations)} total recommendations: "
				f"{sum(1 for r in recommendations if r.type == 'restaurant')} restaurants, "
				f"{sum(1 for r in recommendations if r.type != 'restaurant')} activities")
	
	return recommendations


# ============================================================================
# API Endpoints - Preferences
# ============================================================================

@app.post("/api/preferences", tags=["Preferences"])
async def save_preferences(preferences: UserPreferences) -> dict:
	"""Save or update user preferences"""
	user_preferences_store[preferences.user_id] = {
		"activity_type": preferences.activity_type,
		"meal_times": preferences.meal_times,
		"preferred_cuisines": preferences.preferred_cuisines,
		"updated_at": datetime.now().isoformat()
	}
	
	logger.info(f"Preferences saved for user {preferences.user_id}")
	
	return {
		"message": "Preferences saved successfully",
		"user_id": preferences.user_id,
		"preferences": user_preferences_store[preferences.user_id]
	}


@app.get("/api/preferences/{user_id}", tags=["Preferences"])
async def get_preferences(user_id: str) -> dict:
	"""Get user preferences"""
	if user_id not in user_preferences_store:
		raise HTTPException(status_code=404, detail="User preferences not found")
	
	return {
		"user_id": user_id,
		"preferences": user_preferences_store[user_id]
	}


@app.put("/api/preferences/{user_id}", tags=["Preferences"])
async def update_preferences(user_id: str, preferences: UserPreferences) -> dict:
	"""
	Update existing user preferences
	FIXED: Now automatically sends notification when preferences change
	"""
	if user_id not in user_preferences_store:
		raise HTTPException(
			status_code=404,
			detail="User preferences not found. Use POST to create new preferences."
		)
	
	# Store old preferences for comparison
	old_preferences = user_preferences_store[user_id]
	
	# Update preferences
	user_preferences_store[user_id] = {
		"activity_type": preferences.activity_type,
		"meal_times": preferences.meal_times,
		"preferred_cuisines": preferences.preferred_cuisines,
		"updated_at": datetime.now().isoformat()
	}
	
	logger.info(f"Preferences updated for user {user_id}")
	
	# FIXED: Detect what changed and send notification
	changes = []
	if old_preferences["activity_type"] != preferences.activity_type:
		changes.append(f"activity preference changed to {preferences.activity_type}")
	if old_preferences["meal_times"] != preferences.meal_times:
		changes.append("meal times updated")
	if old_preferences["preferred_cuisines"] != preferences.preferred_cuisines:
		changes.append("cuisine preferences updated")
	
	# Send notification about preference change
	if changes:
		notification = {
			"type": "preferences_updated",
			"title": "Preferences Updated",
			"message": f"Your recommendations will now reflect your updated preferences: {', '.join(changes)}.",
			"changes": changes,
			"timestamp": datetime.now().isoformat()
		}
		
		# Send via WebSocket
		await manager.send_notification(user_id, notification)
		
		# Store in history
		await store_notification(user_id, notification)
	
	return {
		"message": "Preferences updated successfully",
		"user_id": user_id,
		"preferences": user_preferences_store[user_id],
		"notification_sent": len(changes) > 0,
		"changes_detected": changes
	}


@app.delete("/api/preferences/{user_id}", tags=["Preferences"])
async def delete_preferences(user_id: str) -> dict:
	"""Delete user preferences"""
	if user_id not in user_preferences_store:
		raise HTTPException(status_code=404, detail="User preferences not found")
	
	del user_preferences_store[user_id]
	
	# Clean up related data
	if user_id in user_last_context:
		del user_last_context[user_id]
	if user_id in user_notifications:
		del user_notifications[user_id]
	
	logger.info(f"Preferences deleted for user {user_id}")
	
	return {
		"message": "Preferences deleted successfully",
		"user_id": user_id
	}


# ============================================================================
# API Endpoints - Recommendations
# ============================================================================

@app.post("/api/recommendations", tags=["Recommendations"])
async def get_recommendations(request: RecommendationRequest) -> dict:
	"""Get personalized recommendations based on current context"""
	preferences = request.preferences
	location = request.location
	
	# Validate Montreal location (optional warning)
	if not is_in_montreal_area(location.latitude, location.longitude):
		logger.warning(f"Location outside Montreal area: {location.latitude}, {location.longitude}")
	
	# Get current context
	current_hour = datetime.now().hour
	weather_data = await get_weather(location.latitude, location.longitude)
	
	# Generate recommendations using refactored engine
	recommendations = await generate_recommendations(
		preferences,
		location,
		current_hour,
		weather_data
	)
	
	return {
		"recommendations": recommendations,
		"context": {
			"time_hour": current_hour,
			"time_period": get_time_period(current_hour),
			"weather": weather_data["weather"],
			"temperature": weather_data["temperature"],
			"location": {
				"latitude": location.latitude,
				"longitude": location.longitude,
				"in_montreal": is_in_montreal_area(location.latitude, location.longitude)
			}
		},
		"timestamp": datetime.now().isoformat()
	}


@app.post("/api/recommendations/manual", tags=["Recommendations"])
async def get_recommendations_with_manual_context(request: ManualRecommendationRequest) -> dict:
	"""
	Get recommendations with manual context override (for testing/demo)
	FIXED: Now fully implemented with complete recommendation logic
	"""
	preferences = request.preferences
	location = request.location
	manual_context = request.manual_context
	
	# Use manual or current values
	current_hour = manual_context.time_hour if manual_context and manual_context.time_hour is not None else datetime.now().hour
	
	search_lat = manual_context.latitude if manual_context and manual_context.latitude is not None else location.latitude
	search_lon = manual_context.longitude if manual_context and manual_context.longitude is not None else location.longitude
	
	# Create location object for search
	search_location = LocationData(latitude=search_lat, longitude=search_lon)
	
	# Get weather (manual or real)
	if manual_context and manual_context.weather and manual_context.temperature is not None:
		weather_data = {
			"weather": manual_context.weather,
			"temperature": manual_context.temperature,
			"description": f"manually set to {manual_context.weather}",
			"humidity": 50,
			"wind_speed": 5
		}
	else:
		weather_data = await get_weather(search_lat, search_lon)
	
	# FIXED: Use the refactored recommendation engine
	recommendations = await generate_recommendations(
		preferences,
		search_location,
		current_hour,
		weather_data
	)
	
	return {
		"recommendations": recommendations,
		"context_used": {
			"time_hour": current_hour,
			"time_period": get_time_period(current_hour),
			"weather": weather_data["weather"],
			"temperature": weather_data["temperature"],
			"location": {
				"latitude": search_lat,
				"longitude": search_lon,
				"in_montreal": is_in_montreal_area(search_lat, search_lon)
			},
			"manual_override": manual_context is not None
		},
		"timestamp": datetime.now().isoformat()
	}


# ============================================================================
# API Endpoints - Weather
# ============================================================================

@app.post("/api/weather", tags=["Weather"])
async def get_current_weather(location: LocationData) -> dict:
	"""Get current weather for a location"""
	weather_data = await get_weather(location.latitude, location.longitude)
	
	# Add Montreal location info
	in_montreal = is_in_montreal_area(location.latitude, location.longitude)
	
	return {
		**weather_data,
		"location": {
			"latitude": location.latitude,
			"longitude": location.longitude,
			"in_montreal": in_montreal
		},
		"timestamp": datetime.now().isoformat()
	}


# ============================================================================
# API Endpoints - Context & Notifications
# ============================================================================

@app.post("/api/context/update", tags=["Context"])
async def update_user_context(context_update: ContextUpdate) -> dict:
	"""Update user context and trigger notifications"""
	user_id = context_update.user_id
	
	if user_id not in user_preferences_store:
		raise HTTPException(
			status_code=404,
			detail="User preferences not found. Please set preferences first."
		)
	
	preferences = user_preferences_store[user_id]
	
	# Build new context
	new_context = {}
	
	if context_update.location:
		new_context["location"] = {
			"latitude": context_update.location.latitude,
			"longitude": context_update.location.longitude
		}
		
		weather_data = await get_weather(
			context_update.location.latitude,
			context_update.location.longitude
		)
		new_context["weather"] = weather_data["weather"]
		new_context["temperature"] = weather_data["temperature"]
	
	new_context["time_hour"] = context_update.current_time if context_update.current_time is not None else datetime.now().hour
	
	# Detect changes
	notifications = await detect_context_changes(user_id, new_context, preferences)
	
	# Send notifications via WebSocket
	for notification in notifications:
		await manager.send_notification(user_id, notification)
	
	return {
		"user_id": user_id,
		"context_updated": new_context,
		"notifications_generated": len(notifications),
		"notifications": notifications,
		"timestamp": datetime.now().isoformat()
	}


@app.get("/api/context/{user_id}", tags=["Context"])
async def get_current_context(user_id: str) -> dict:
	"""Get current stored context for a user"""
	if user_id not in user_last_context:
		raise HTTPException(status_code=404, detail="No context found for this user")
	
	return {
		"user_id": user_id,
		"context": user_last_context[user_id],
		"timestamp": datetime.now().isoformat()
	}


@app.get("/api/notifications/{user_id}", tags=["Notifications"])
async def get_notification_history(
	user_id: str,
	limit: int = Query(20, ge=1, le=100, description="Number of notifications to return")
) -> dict:
	"""Get notification history for a user"""
	if user_id not in user_notifications:
		return {
			"user_id": user_id,
			"notifications": [],
			"total": 0,
			"showing": 0
		}
	
	notifications = user_notifications[user_id]
	limited = notifications[-limit:] if len(notifications) > limit else notifications
	
	return {
		"user_id": user_id,
		"notifications": limited,
		"total": len(notifications),
		"showing": len(limited)
	}


@app.delete("/api/notifications/{user_id}", tags=["Notifications"])
async def clear_notification_history(user_id: str) -> dict:
	"""Clear notification history for a user"""
	count = 0
	if user_id in user_notifications:
		count = len(user_notifications[user_id])
		user_notifications[user_id] = []
	
	return {
		"user_id": user_id,
		"message": "Notification history cleared" if count > 0 else "No notification history found",
		"notifications_cleared": count
	}


# ============================================================================
# API Endpoints - Categories
# ============================================================================

@app.get("/api/cuisines/categories", tags=["Categories"])
async def get_cuisine_categories() -> dict:
	"""Get all available cuisine categories"""
	return {
		"cuisines": [
			{"name": name, "search_term": search_term}
			for name, search_term in sorted(CUISINE_CATEGORIES.items())
		],
		"total": len(CUISINE_CATEGORIES)
	}


@app.get("/api/activities/categories", tags=["Categories"])
async def get_activity_categories() -> dict:
	"""Get all available activity categories"""
	
	return {
		"indoor": {
			"early_morning": ACTIVITY_CATEGORIES["indoor"]["early_morning"],
			"morning": ACTIVITY_CATEGORIES["indoor"]["morning"],
			"noon": ACTIVITY_CATEGORIES["indoor"]["noon"],
			"evening": ACTIVITY_CATEGORIES["indoor"]["evening"],
			"night": ACTIVITY_CATEGORIES["indoor"]["night"]
		},
		"outdoor": {
			"early_morning": ACTIVITY_CATEGORIES["outdoor"]["early_morning"],
			"morning": ACTIVITY_CATEGORIES["outdoor"]["morning"],
			"noon": ACTIVITY_CATEGORIES["outdoor"]["noon"],
			"evening": ACTIVITY_CATEGORIES["outdoor"]["evening"],
			"night": ACTIVITY_CATEGORIES["outdoor"]["night"]
		},
		"total_indoor": sum(len(activities) for activities in ACTIVITY_CATEGORIES["indoor"].values()),
		"total_outdoor": sum(len(activities) for activities in ACTIVITY_CATEGORIES["outdoor"].values())
	}


# ============================================================================
# API Endpoints - Montreal Validation
# ============================================================================

@app.post("/api/location/validate", tags=["Location"])
async def validate_montreal_location(location: LocationData) -> dict:
	"""Validate if location is within Montreal metropolitan area"""
	in_montreal = is_in_montreal_area(location.latitude, location.longitude)
	
	# Calculate distance from Montreal center
	distance_from_center = calculate_distance(
		location.latitude,
		location.longitude,
		MONTREAL_BOUNDS["center_lat"],
		MONTREAL_BOUNDS["center_lon"]
	)
	
	return {
		"location": {
			"latitude": location.latitude,
			"longitude": location.longitude
		},
		"in_montreal_area": in_montreal,
		"distance_from_center_km": round(distance_from_center, 2),
		"montreal_center": {
			"latitude": MONTREAL_BOUNDS["center_lat"],
			"longitude": MONTREAL_BOUNDS["center_lon"]
		},
		"recommendation": "OK" if in_montreal else "Location is outside Montreal area. Recommendations may be limited."
	}


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws/notifications/{user_id}")
async def websocket_notifications(websocket: WebSocket, user_id: str):
	"""WebSocket endpoint for real-time notifications"""
	await manager.connect(user_id, websocket)
	
	try:
		# Send welcome message
		await manager.send_notification(user_id, {
			"type": "connection_established",
			"title": "Connected",
			"message": "You will receive notifications about context changes.",
			"timestamp": datetime.now().isoformat()
		})
		
		# Keep connection alive
		while True:
			data = await websocket.receive_text()
			
			if data == "ping":
				await websocket.send_json({
					"type": "pong",
					"timestamp": datetime.now().isoformat()
				})
	
	except WebSocketDisconnect:
		manager.disconnect(user_id)
		logger.info(f"WebSocket disconnected for user {user_id}")
	except Exception as e:
		logger.error(f"WebSocket error for user {user_id}: {e}")
		manager.disconnect(user_id)


# ============================================================================
# Root & Health Endpoints
# ============================================================================

@app.get("/", tags=["Info"])
async def root():
	"""API information and status"""
	return {
		"message": "Montreal Travel Companion API",
		"version": "2.0.0",
		"status": "active",
		"features": [
			"Real GPS location tracking",
			"Live weather data from OpenWeatherMap",
			"Real-time place discovery via Google Places API",
			"Context-aware recommendations (location, time, weather, preferences)",
			"Real-time notifications via WebSocket",
			"Automatic preference change detection",
			"Montreal location validation",
			"Change detection for all contexts",
			"Notification history tracking",
			"Manual context override for testing",
			"Smart outdoor/indoor activity filtering based on weather",
			"Improved meal/activity separation in search queries"
		],
		"api_keys_configured": {
			"openweather": bool(OPENWEATHER_API_KEY),
			"google_places": bool(GOOGLE_PLACES_API_KEY)
		},
		"notification_system": {
			"active_connections": len(manager.active_connections),
			"websocket_endpoint": "/ws/notifications/{user_id}",
			"context_update_endpoint": "/api/context/update",
			"notification_history_endpoint": "/api/notifications/{user_id}"
		},
		"improvements": {
			"search_separation": "Clear separation between meal and activity searches",
			"smart_filtering": "Restaurants only during meal times, activities only during non-meal times",
			"preference_queries": "Targeted Google API queries based on context",
			"weather_aware": "Intelligent activity suggestions based on weather conditions"
		},
		"documentation": "/docs"
	}


@app.get("/health", tags=["Info"])
async def health_check():
	"""Health check endpoint"""
	return {
		"status": "healthy",
		"timestamp": datetime.now().isoformat(),
		"apis_configured": {
			"openweather": bool(OPENWEATHER_API_KEY),
			"google_places": bool(GOOGLE_PLACES_API_KEY)
		},
		"active_users": len(user_preferences_store),
		"active_websocket_connections": len(manager.active_connections),
		"total_notifications_stored": sum(len(notifs) for notifs in user_notifications.values()),
		"configuration": {
			"location_threshold_km": LOCATION_CHANGE_THRESHOLD_KM,
			"temperature_threshold_c": TEMPERATURE_CHANGE_THRESHOLD_C,
			"notification_history_limit": NOTIFICATION_HISTORY_LIMIT,
			"outdoor_temp_range": f"{OUTDOOR_MIN_TEMP_C}°C to {OUTDOOR_MAX_TEMP_C}°C"
		}
	}


# ============================================================================
# Startup Event
# ============================================================================

@app.on_event("startup")
async def startup_event():
	"""Log startup information"""
	logger.info("="*50)
	logger.info("Montreal Travel Companion API Starting...")
	logger.info("="*50)
	logger.info(f"OpenWeather API: {'✓ Configured' if OPENWEATHER_API_KEY else '✗ NOT CONFIGURED'}")
	logger.info(f"Google Places API: {'✓ Configured' if GOOGLE_PLACES_API_KEY else '✗ NOT CONFIGURED'}")
	logger.info(f"Location Threshold: {LOCATION_CHANGE_THRESHOLD_KM} km")
	logger.info(f"Temperature Threshold: {TEMPERATURE_CHANGE_THRESHOLD_C}°C")
	logger.info(f"Outdoor Temperature Range: {OUTDOOR_MIN_TEMP_C}°C to {OUTDOOR_MAX_TEMP_C}°C")
	logger.info("Search Query Separation: ✓ Enabled (Meal vs Activity)")
	logger.info("="*50)
	
	if not OPENWEATHER_API_KEY:
		logger.warning("OpenWeather API key not configured - using fallback weather data")
	
	if not GOOGLE_PLACES_API_KEY:
		logger.warning("Google Places API key not configured - place search will fail")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
	import uvicorn
	
	print("\n" + "="*50)
	print("Montreal Travel Companion API Starting...")
	print("="*50)
	print(f"OpenWeather API: {'✓ Configured' if OPENWEATHER_API_KEY else '✗ NOT CONFIGURED'}")
	print(f"Google Places API: {'✓ Configured' if GOOGLE_PLACES_API_KEY else '✗ NOT CONFIGURED'}")
	print(f"Configuration:")
	print(f"  - Location Change Threshold: {LOCATION_CHANGE_THRESHOLD_KM} km")
	print(f"  - Temperature Change Threshold: {TEMPERATURE_CHANGE_THRESHOLD_C}°C")
	print(f"  - Outdoor Temperature Range: {OUTDOOR_MIN_TEMP_C}°C to {OUTDOOR_MAX_TEMP_C}°C")
	print(f"  - Montreal Area Validation: Enabled")
	print(f"  - Smart Activity Filtering: Enabled (weather-aware)")
	print(f"  - Search Query Separation: Enabled (Meal vs Activity)")
	print("="*50)
	
	if not GOOGLE_PLACES_API_KEY:
		print("\n⚠️  WARNING: Google Places API key not configured!")
		print("   Get your key from: https://console.cloud.google.com/")
		print("   Add to .env file: GOOGLE_PLACES_API_KEY=your_key_here\n")
	
	print("="*50 + "\n")
	
	uvicorn.run(
		"server:app",
		host="0.0.0.0",
		port=8000,
		reload=True,
		log_level="info"
	)
