import React, { useEffect, useState } from "react";
import ChatUI from "./ChatUI";

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [googleConnected, setGoogleConnected] = useState(() => {
    return localStorage.getItem('googleConnected') === 'true';
  });
  const [hubspotConnected, setHubspotConnected] = useState(() => {
    return localStorage.getItem('hubspotConnected') === 'true';
  });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("auth") === "success") {
      setGoogleConnected(true);
      localStorage.setItem('googleConnected', 'true');
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (params.get("auth") === "hubspot_success") {
      setHubspotConnected(true);
      localStorage.setItem('hubspotConnected', 'true');
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  // Check if both accounts are connected whenever either state changes
  useEffect(() => {
    if (googleConnected && hubspotConnected) {
      setIsLoggedIn(true);
    }
  }, [googleConnected, hubspotConnected]);

  const handleGoogleLogin = () => {
    window.location.href = `${
      import.meta.env.VITE_API_BASE_URL
    }/auth/google/login`;
  };

  const handleHubspotLogin = () => {
    window.location.href = `${
      import.meta.env.VITE_API_BASE_URL
    }/auth/hubspot`;
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setGoogleConnected(false);
    setHubspotConnected(false);
    localStorage.removeItem('googleConnected');
    localStorage.removeItem('hubspotConnected');
  };

  // Debug function to clear all auth states (for testing)
  const clearAuthStates = () => {
    setGoogleConnected(false);
    setHubspotConnected(false);
    localStorage.removeItem('googleConnected');
    localStorage.removeItem('hubspotConnected');
  };

  if (!isLoggedIn) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
        <div className="flex flex-col items-center w-full max-w-md px-4">
          <h1 className="text-3xl font-bold mb-6 text-center">
            Welcome to Jump Agent
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mb-8 text-center">
            Connect your accounts to get started
          </p>
          
          {/* Progress indicator */}
          <div className="w-full mb-6">
            <div className="flex justify-between text-sm text-gray-600 mb-2">
              <span>Progress</span>
              <span>{googleConnected && hubspotConnected ? '2/2' : googleConnected || hubspotConnected ? '1/2' : '0/2'}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-green-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(googleConnected ? 1 : 0) + (hubspotConnected ? 1 : 0)}/2 * 100%` }}
              ></div>
            </div>
          </div>

          <div className="w-full space-y-4">
            {/* Google Connection */}
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center space-x-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  googleConnected ? 'bg-green-500' : 'bg-red-500'
                }`}>
                  <span className="text-white text-sm font-bold">G</span>
                </div>
                <span className="font-medium">Google Account</span>
              </div>
              {googleConnected ? (
                <span className="text-green-600 text-sm font-medium">✓ Connected</span>
              ) : (
                <button
                  onClick={handleGoogleLogin}
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition text-sm"
                >
                  Connect
                </button>
              )}
            </div>

            {/* HubSpot Connection */}
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center space-x-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  hubspotConnected ? 'bg-green-500' : 'bg-orange-500'
                }`}>
                  <span className="text-white text-sm font-bold">H</span>
                </div>
                <span className="font-medium">HubSpot Account</span>
              </div>
              {hubspotConnected ? (
                <span className="text-green-600 text-sm font-medium">✓ Connected</span>
              ) : (
                <button
                  onClick={handleHubspotLogin}
                  className="bg-orange-600 text-white px-4 py-2 rounded hover:bg-orange-700 transition text-sm"
                >
                  Connect
                </button>
              )}
            </div>
          </div>

          {/* Show status message based on connection state */}
          {googleConnected && !hubspotConnected && (
            <div className="mt-6 text-center p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-blue-700 font-medium">✅ Google connected! Now connect HubSpot to continue.</p>
            </div>
          )}
          
          {!googleConnected && hubspotConnected && (
            <div className="mt-6 text-center p-4 bg-orange-50 border border-orange-200 rounded-lg">
              <p className="text-orange-700 font-medium">✅ HubSpot connected! Now connect Google to continue.</p>
            </div>
          )}

          {googleConnected && hubspotConnected && (
            <div className="mt-6 text-center p-4 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-green-700 font-medium mb-3">🎉 All accounts connected!</p>
              <button
                onClick={() => setIsLoggedIn(true)}
                className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition"
              >
                Continue to Chat
              </button>
            </div>
          )}

          {/* Debug button (only in development) */}
          {import.meta.env.DEV && (
            <div className="mt-4 text-center">
              <button
                onClick={clearAuthStates}
                className="text-xs text-gray-500 hover:text-red-500 underline"
              >
                Clear Auth States (Debug)
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  return <ChatUI onLogout={handleLogout} />;
}
