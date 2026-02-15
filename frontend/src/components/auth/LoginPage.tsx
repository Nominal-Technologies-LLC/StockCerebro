import { useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { googleLogin } from '../../api/client';
import type { GoogleCredentialResponse } from '../../types/auth';

export default function LoginPage() {
  const { login } = useAuth();
  const googleButtonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Initialize Google Sign-In
    if (window.google) {
      window.google.accounts.id.initialize({
        client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
        callback: handleGoogleCallback,
      });

      window.google.accounts.id.renderButton(
        googleButtonRef.current!,
        {
          theme: 'filled_blue',
          size: 'large',
          text: 'signin_with',
          width: 300,
        }
      );
    }
  }, []);

  const handleGoogleCallback = async (response: GoogleCredentialResponse) => {
    try {
      const { user } = await googleLogin(response.credential);
      login(user);
    } catch (error) {
      console.error('Login failed:', error);
      alert('Login failed. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="card max-w-md w-full text-center p-8">
        <h1 className="text-3xl font-bold text-white mb-2">StockCerebro</h1>
        <p className="text-gray-400 mb-8">
          Sign in to access stock analysis and insights
        </p>
        <div className="flex justify-center">
          <div ref={googleButtonRef}></div>
        </div>
      </div>
    </div>
  );
}
