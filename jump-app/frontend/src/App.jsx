import React, { useEffect, useState } from "react";
import ChatUI from "./ChatUI";

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("auth") === "success") {
      setIsLoggedIn(true);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const handleLogin = () => {
    window.location.href = `${
      import.meta.env.VITE_API_BASE_URL
    }/auth/google/login`;
  };

  if (!isLoggedIn) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
        <div className="flex flex-col items-center w-full max-w-md px-4">
          <h1 className="text-3xl font-bold mb-6 text-center">
            Welcome to Jump Agent
          </h1>
          <button
            onClick={handleLogin}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
          >
            Login with Google
          </button>
        </div>
      </div>
    );
  }

  return <ChatUI />;
}
