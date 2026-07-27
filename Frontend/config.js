const API_BASE =
  location.hostname === "localhost" ||
  location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:8000"
    : "https://campuscoord.onrender.com";