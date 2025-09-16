import os
import requests
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from datetime import datetime

# Load env vars
load_dotenv()

# FastAPI app
app = FastAPI()

# Allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Spotify API setup
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def get_weather_and_time(lat: float, lon: float):
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
    res = requests.get(url)
    data = res.json()

    if res.status_code != 200:
        return {"error": data.get("message", "Failed to fetch weather")}

    weather = {
        "description": data["weather"][0]["description"],
        "temperature": data["main"]["temp"],
        "feels_like": data["main"]["feels_like"]
    }

    timezone_offset = data["timezone"]
    local_time = datetime.utcfromtimestamp(data["dt"] + timezone_offset)

    hour = local_time.hour
    if 5 <= hour < 12:
        time_of_day = "Morning"
    elif 12 <= hour < 17:
        time_of_day = "Afternoon"
    elif 17 <= hour < 21:
        time_of_day = "Evening"
    else:
        time_of_day = "Night"

    return weather, time_of_day, local_time.strftime("%Y-%m-%d %H:%M:%S")


@app.post("/recommend")
def recommend_music(payload: dict = Body(...)):
    """
    Expects payload:
    {
      "lat": float,
      "lon": float,
      "user_input": "optional text or Spotify genres"
    }
    """
    lat = payload.get("lat")
    lon = payload.get("lon")
    user_input = payload.get("user_input", "")

    
    weather, time_of_day, local_time = get_weather_and_time(lat, lon)

   
    prompt = f"""
    You are a smart music recommendation assistant. Suggest 10 songs for the user based on:

    Time of Day: {time_of_day}
    Weather: {weather['description']}
    User Input: {user_input if user_input else 'None'}

    The sings should not be well known but also should not be unknown.
    Do not be afraid to give obscure songs. If needed check rateyourmusic.com for good suggesstions.
    For each song, provide: name, artist, genre, mood.
    Format strictly as JSON array, no extra text.
    """

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "deepseek/deepseek-chat-v3.1:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    raw_text = r.json()["choices"][0]["message"]["content"]

    try:
        recommendations = eval(raw_text)  # parse JSON array
    except Exception:
        recommendations = []

    
    enriched = []
    for rec in recommendations:
        query = f"{rec['name']} {rec['artist']}"
        results = sp.search(q=query, limit=1, type="track")

        if results["tracks"]["items"]:
            track = results["tracks"]["items"][0]
            rec["spotify_url"] = track["external_urls"]["spotify"]
            rec["album_cover"] = track["album"]["images"][0]["url"]
        else:
            rec["spotify_url"] = None
            rec["album_cover"] = None

        enriched.append(rec)

    return {
        "local_time": local_time,
        "time_of_day": time_of_day,
        "weather": weather,
        "recommendations": enriched
    }

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


@app.get("/context")
def context(lat: float, lon: float):
    return get_weather_and_time(lat, lon)
