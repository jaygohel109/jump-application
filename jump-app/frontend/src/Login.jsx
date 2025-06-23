import React, { useState } from 'react';
import { Sparkles, Globe, Users, CheckCircle, ArrowRight, Shield } from 'lucide-react';

function Login({ authStep, userInfo, onGoogleSuccess, onHubspotSuccess, onLogout }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch('http://127.0.0.1:8000/auth/google/login');
      const data = await response.json();
      
      if (data.oauth_url) {
        window.location.href = data.oauth_url;
      } else {
        setError('Failed to get Google OAuth URL');
      }
    } catch (error) {
      console.error('Google login error:', error);
      setError('Failed to initiate Google login');
    } finally {
      setLoading(false);
    }
  };

  const handleHubspotLogin = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch('http://127.0.0.1:8000/auth/hubspot', {
        credentials: 'include',
      });
      const data = await response.json();
      
      if (data.oauth_url) {
        window.location.href = data.oauth_url;
      } else {
        setError('Failed to get HubSpot OAuth URL');
      }
    } catch (error) {
      console.error('HubSpot login error:', error);
      setError('Failed to initiate HubSpot login');
    } finally {
      setLoading(false);
    }
  };

  const renderStepContent = () => {
    switch (authStep) {
      case 'login':
        return (
          <div className="space-y-8">
            <div className="text-center">
              <div className="w-20 h-20 bg-gradient-to-r from-blue-500 to-purple-600 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-2xl">
                <Sparkles className="w-10 h-10 text-white" />
              </div>
              <h2 className="text-3xl font-bold text-white mb-3">Welcome to Jump Agent</h2>
              <p className="text-white/70 text-lg">Your intelligent AI assistant for managing emails, contacts, and calendar</p>
            </div>
            
            {error && (
              <div className="bg-red-500/20 backdrop-blur-sm border border-red-400/30 rounded-2xl p-4">
                <p className="text-red-300 text-sm">{error}</p>
              </div>
            )}
            
            <div className="space-y-4">
              <button
                onClick={handleGoogleLogin}
                disabled={loading}
                className="w-full flex justify-center items-center px-6 py-4 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-semibold rounded-2xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed shadow-xl hover:shadow-2xl transform hover:scale-[1.02]"
              >
                {loading ? (
                  <div className="flex items-center space-x-3">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    <span>Connecting...</span>
                  </div>
                ) : (
                  <>
                    <Globe className="w-5 h-5 mr-3" />
                    <span>Connect with Google</span>
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </>
                )}
              </button>
            </div>

            <div className="text-center space-y-4">
              <div className="flex items-center justify-center space-x-4 text-white/60">
                <div className="flex items-center space-x-2">
                  <Shield className="w-4 h-4" />
                  <span className="text-sm">Secure</span>
                </div>
                <div className="w-1 h-1 bg-white/40 rounded-full"></div>
                <div className="flex items-center space-x-2">
                  <Sparkles className="w-4 h-4" />
                  <span className="text-sm">AI-Powered</span>
                </div>
                <div className="w-1 h-1 bg-white/40 rounded-full"></div>
                <div className="flex items-center space-x-2">
                  <CheckCircle className="w-4 h-4" />
                  <span className="text-sm">Free</span>
                </div>
              </div>
            </div>
          </div>
        );

      case 'hubspot':
        return (
          <div className="space-y-8">
            <div className="text-center">
              <div className="w-20 h-20 bg-gradient-to-r from-green-500 to-blue-600 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-2xl">
                <CheckCircle className="w-10 h-10 text-white" />
              </div>
              <h2 className="text-3xl font-bold text-white mb-3">Google Connected! 🎉</h2>
              <p className="text-white/70 text-lg">Now connect your HubSpot account to unlock full functionality</p>
            </div>
            
            <div className="bg-green-500/20 backdrop-blur-sm border border-green-400/30 rounded-2xl p-6">
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-blue-600 rounded-2xl flex items-center justify-center">
                  <Globe className="w-6 h-6 text-white" />
                </div>
                <div className="flex-1">
                  <p className="text-white font-semibold">
                    Google account connected successfully
                  </p>
                  <p className="text-white/70 text-sm mt-1">
                    {userInfo?.email}
                  </p>
                </div>
              </div>
            </div>
            
            {error && (
              <div className="bg-red-500/20 backdrop-blur-sm border border-red-400/30 rounded-2xl p-4">
                <p className="text-red-300 text-sm">{error}</p>
              </div>
            )}
            
            <div className="space-y-4">
              <button
                onClick={handleHubspotLogin}
                disabled={loading}
                className="w-full flex justify-center items-center px-6 py-4 bg-gradient-to-r from-orange-500 to-red-600 hover:from-orange-600 hover:to-red-700 text-white font-semibold rounded-2xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed shadow-xl hover:shadow-2xl transform hover:scale-[1.02]"
              >
                {loading ? (
                  <div className="flex items-center space-x-3">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    <span>Connecting...</span>
                  </div>
                ) : (
                  <>
                    <Users className="w-5 h-5 mr-3" />
                    <span>Connect HubSpot</span>
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </>
                )}
              </button>
              
              <button
                onClick={onLogout}
                className="w-full px-6 py-3 text-white/70 hover:text-white underline transition-colors duration-200"
              >
                Use different Google account
              </button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 relative overflow-hidden">
      {/* Background decorations */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500/20 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-500/20 rounded-full blur-3xl"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-gradient-to-r from-purple-500/10 to-blue-500/10 rounded-full blur-3xl"></div>
      </div>

      <div className="relative z-10 max-w-md w-full mx-4">
        {/* Progress indicator */}
        <div className="mb-8">
          <div className="flex justify-between text-sm text-white/80 mb-3">
            <span className="font-medium">Setup Progress</span>
            <span className="font-medium">{authStep === 'login' ? '1/2' : '2/2'}</span>
          </div>
          <div className="w-full bg-white/10 backdrop-blur-sm rounded-full h-3 border border-white/20">
            <div 
              className="bg-gradient-to-r from-green-400 to-blue-500 h-3 rounded-full transition-all duration-500 shadow-lg"
              style={{ width: authStep === 'login' ? '50%' : '100%' }}
            ></div>
          </div>
        </div>

        {/* Main content */}
        <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-8 shadow-2xl">
          {renderStepContent()}
        </div>
        
        <div className="text-center mt-6">
          <p className="text-xs text-white/50">
            By connecting your accounts, you agree to our{' '}
            <a href="#" className="text-blue-400 hover:text-blue-300 underline">terms of service</a>
            {' '}and{' '}
            <a href="#" className="text-blue-400 hover:text-blue-300 underline">privacy policy</a>.
          </p>
        </div>
      </div>
    </div>
  );
}

export default Login; 