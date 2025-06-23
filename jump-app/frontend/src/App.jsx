import React, { useState, useEffect } from 'react';
import './App.css';
import Login from './Login';
import ChatUI from './ChatUI';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authStep, setAuthStep] = useState('login'); // 'login', 'hubspot', 'chat'

  useEffect(() => {
    checkSession();
  }, []);

  const checkSession = async () => {
    try {
      console.log('Checking session...'); // Debug log
      console.log('Current URL:', window.location.href); // Debug log
      console.log('Current cookies:', document.cookie); // Debug log
      
      const response = await fetch('http://127.0.0.1:8000/auth/session', {
        credentials: 'include'
      });
      
      console.log('Session response status:', response.status); // Debug log
      console.log('Session response headers:', Object.fromEntries(response.headers.entries())); // Debug log
      
      if (response.ok) {
        const data = await response.json();
        console.log('Session data:', data); // Debug log
        
        if (data.authenticated) {
          setUserInfo({
            email: data.email,
            hasGoogle: data.has_google,
            hasHubspot: data.has_hubspot
          });
          
          console.log('User info set:', { email: data.email, hasGoogle: data.has_google, hasHubspot: data.has_hubspot }); // Debug log
          
          // Determine the current auth step
          if (data.has_google && data.has_hubspot) {
            console.log('Setting auth step to: chat'); // Debug log
            setIsAuthenticated(true);
            setAuthStep('chat');
          } else if (data.has_google) {
            console.log('Setting auth step to: hubspot'); // Debug log
            setAuthStep('hubspot');
          } else {
            console.log('Setting auth step to: login'); // Debug log
            setAuthStep('login');
          }
        } else {
          console.log('Not authenticated, setting auth step to: login'); // Debug log
          setIsAuthenticated(false);
          setUserInfo(null);
          setAuthStep('login');
        }
      } else {
        console.log('Session response not ok, setting auth step to: login'); // Debug log
        console.log('Response text:', await response.text()); // Debug log
        setIsAuthenticated(false);
        setUserInfo(null);
        setAuthStep('login');
      }
    } catch (error) {
      console.error('Error checking session:', error);
      setIsAuthenticated(false);
      setUserInfo(null);
      setAuthStep('login');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch('http://127.0.0.1:8000/auth/logout', {
        method: 'GET',
        credentials: 'include'
      });
      setIsAuthenticated(false);
      setUserInfo(null);
      setAuthStep('login');
    } catch (error) {
      console.error('Error logging out:', error);
    }
  };

  const handleGoogleSuccess = () => {
    // After Google OAuth, check session again to see if we need HubSpot
    setTimeout(() => {
      checkSession();
    }, 1000);
  };

  const handleHubspotSuccess = () => {
    // After HubSpot OAuth, check session again to see if we can go to chat
    setTimeout(() => {
      checkSession();
    }, 1000);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      {authStep === 'chat' ? (
        <ChatUI 
          userInfo={userInfo} 
          onLogout={handleLogout}
          onSessionExpired={() => {
            setIsAuthenticated(false);
            setUserInfo(null);
            setAuthStep('login');
          }}
        />
      ) : (
        <Login 
          authStep={authStep}
          userInfo={userInfo}
          onGoogleSuccess={handleGoogleSuccess}
          onHubspotSuccess={handleHubspotSuccess}
          onLogout={handleLogout}
        />
      )}
    </div>
  );
}

export default App;
