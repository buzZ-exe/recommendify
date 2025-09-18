import os
import requests
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from datetime import datetime
import asyncio
import httpx
from fastapi import Body
import json
import re

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
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

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
async def recommend_music(payload: dict = Body(...)):
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

    # weather + time
    weather, time_of_day, local_time = get_weather_and_time(lat, lon)

    # prompt
    prompt = f"""
    You do not remember past conversations.
    You are a smart music recommendation assistant. Suggest 10 songs for the user based on:

    Time of Day: {time_of_day}
    Weather: {weather['description']}
    User Input: {user_input if user_input else 'None'}

    The songs should not be well known but also should not be unknown.
    Don't be afraid to give obscure songs.
    Keep at least 3 popular at the top and at least 3 not well known but well rated songs as well. 
    If needed check rateyourmusic.com for good suggestions.
    For each song, provide: name, artist, genre, two moods in one string separated with comma.
    Whatever the user inputs takes priority over the time and weather.
    Format strictly as JSON array, no extra text, NO PREAMBLE AND NO TEXT AFTER.
    """

    # call OpenRouter (async)
    async with httpx.AsyncClient(timeout=60.0) as client:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            # "model": "deepseek/deepseek-chat-v3.1:free",
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }

        # r = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        r = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
        raw_text = r.json()["choices"][0]["message"]["content"]

    try:
        recommendations = json.loads(raw_text)  
    except Exception:
        recommendations = []

    async def enrich_song(rec):
        loop = asyncio.get_event_loop()
        def search():
            query = f"{rec['name']} {rec['artist']}"
            return sp.search(q=query, limit=1, type="track")

        results = await loop.run_in_executor(None, search)

        if results["tracks"]["items"]:
            track = results["tracks"]["items"][0]
            rec["spotify_url"] = track["external_urls"]["spotify"]
            rec["album_cover"] = track["album"]["images"][0]["url"]
        else:
            rec["spotify_url"] = None
            rec["album_cover"] = None
        return rec

    
    enriched = await asyncio.gather(*(enrich_song(rec) for rec in recommendations))

    return {
        "local_time": local_time,
        "time_of_day": time_of_day,
        "weather": weather,
        "recommendations": enriched,
    }

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


@app.get("/context")
def context(lat: float, lon: float):
    return get_weather_and_time(lat, lon)
