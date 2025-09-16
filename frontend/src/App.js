import React, { useState } from "react";
import "./App.css"; 

function App() {
  const [userInput, setUserInput] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showContext, setShowContext] = useState(false);

  document.title = "Recommendify";

  const getRecommendations = () => {
    setLoading(true);

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;

        try {
          const res = await fetch("http://localhost:8000/recommend", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              lat,
              lon,
              user_input: userInput, 
            }),
          });

          const json = await res.json();
          setData(json);
        } catch (err) {
          console.error("Error fetching recommendations:", err);
        } finally {
          setLoading(false);
        }
      },
      (error) => {
        console.error("Error fetching location:", error);
        setLoading(false);
      }
    );
  };

  return (
    <div className="app">
      <h1 className="title">Recommendify</h1>
      <p className="subtitle">Music picks based on your mood, time & weather</p>

      {/* Input */}
      <input
        type="text"
        placeholder="What we feeling today?"
        value={userInput}
        onChange={(e) => setUserInput(e.target.value)}
        className="input"
      />

      {/* Button */}
      <button className="button" onClick={getRecommendations} disabled={loading}>
        {loading ? "Loading..." : "Get Recommendations"}
      </button>

      {/* Results */}
      {data && (
        // <div className="results">
        //   <p><b>Time of Day:</b> {data.time_of_day}</p>
        //   <p><b>Weather:</b> {data.weather.description}</p>
        //   <p><b>Temperature:</b> {data.weather.temperature}°C</p>

        <div className="results">

          {/* Show Context Toggle */}
          <button
            className="button"
            onClick={() => setShowContext(!showContext)}
          >
            {showContext ? "Hide Info" : "Show Info"}
          </button>

          {showContext && (
            <div className="context-box">
              <p><b>Time of Day:</b> {data.time_of_day}</p>
              <p><b>Weather:</b> {data.weather.description}</p>
              <p><b>Temperature:</b> {data.weather.temperature}°C</p>
            </div>
          )}
          
          <h1>Recommendations</h1>
          <ul className="recommendations">
            {data.recommendations.map((rec, idx) => (
              <li key={idx} className="recommendation-card">
                <img
                  src={rec.album_cover}
                  alt="cover"
                  className="album-cover"
                />
                <div>
                  <h3>{rec.name}</h3>
                  <p className="artist">{rec.artist}</p>
                  <p className="meta">
                    {rec.genre} • Mood: {rec.mood}
                  </p>
                  {rec.spotify_url && (
                    <a
                      href={rec.spotify_url}
                      target="_blank"
                      rel="noreferrer"
                      className="spotify-link"
                    >
                      ▶ Listen on Spotify
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default App;
