import { useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { googleLogin } from '../../api/client';
import type { GoogleCredentialResponse } from '../../types/auth';

// ── Inline SVG Icons ────────────────────────────────────────────────
function ScoreIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-8 h-8">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
      <path d="M8 14l2-4 2 3 2-5 2 6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function FundamentalIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-8 h-8">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M7 17V13M12 17V7M17 17V11" strokeLinecap="round" />
    </svg>
  );
}

function TechnicalIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-8 h-8">
      <path d="M3 17l4-4 4 4 4-8 6 6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="7" cy="13" r="1.5" fill="currentColor" />
      <circle cx="11" cy="17" r="1.5" fill="currentColor" />
      <circle cx="15" cy="9" r="1.5" fill="currentColor" />
      <circle cx="21" cy="15" r="1.5" fill="currentColor" />
    </svg>
  );
}

function EarningsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-8 h-8">
      <path d="M4 4h16v16H4z" />
      <path d="M4 9h16M9 4v16" />
      <path d="M13 13l2 2 3-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function NewsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-8 h-8">
      <path d="M4 4h16a1 1 0 011 1v14a1 1 0 01-1 1H4a1 1 0 01-1-1V5a1 1 0 011-1z" />
      <path d="M7 8h10M7 12h6M7 16h8" strokeLinecap="round" />
    </svg>
  );
}

function SwingTradeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-8 h-8">
      <path d="M2 20l5-5 4 4 5-7 6 4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M18 8h4v4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ── Feature Data ────────────────────────────────────────────────────
const features = [
  {
    icon: ScoreIcon,
    title: 'Overall Scorecard',
    tagline: 'One Score. Complete Picture.',
    description:
      'Get a composite score from 0-100 with a letter grade and clear buy/sell/hold signal. Combines fundamental and technical analysis into one actionable view.',
    highlights: ['Composite 0-100 score', 'Letter grade (A-F)', 'Buy / Sell / Hold signal'],
  },
  {
    icon: FundamentalIcon,
    title: 'Fundamental Analysis',
    tagline: 'Deep Dive Into the Numbers',
    description:
      'Valuation, growth, financial health, and profitability scoring powered by multi-source data from Yahoo Finance, Finnhub, and SEC EDGAR filings.',
    highlights: ['Valuation & growth metrics', 'Peer-relative scoring', 'SEC EDGAR integration'],
  },
  {
    icon: TechnicalIcon,
    title: 'Technical Analysis',
    tagline: 'Charts & Signals That Matter',
    description:
      'Interactive candlestick charts with moving average overlays, RSI, MACD, volume analysis, and support/resistance levels across multiple timeframes.',
    highlights: ['Candlestick charts + MA overlays', 'RSI, MACD, volume signals', 'Hourly / Daily / Weekly views'],
  },
  {
    icon: EarningsIcon,
    title: 'Earnings Tracker',
    tagline: 'Track Quarterly Performance',
    description:
      'Visualize revenue and earnings trends with quarter-over-quarter and year-over-year growth rates. Direct links to SEC filings and margin analysis.',
    highlights: ['QoQ & YoY growth trends', 'Margin analysis', 'SEC filing links'],
  },
  {
    icon: NewsIcon,
    title: 'News Feed',
    tagline: 'Stay Informed',
    description:
      'Real-time financial news for any ticker with source attribution and quick summaries so you never miss a market-moving headline.',
    highlights: ['Real-time news updates', 'Source attribution', 'Per-ticker filtering'],
  },
  {
    icon: SwingTradeIcon,
    title: 'Swing Trade Calculator',
    tagline: 'Actionable Entry & Exit Points',
    description:
      'Get calculated entry zones, stop loss levels, and target prices with risk/reward ratios and trade reasoning based on technical signals.',
    highlights: ['Entry zone & stop loss', 'Target price levels', 'Risk/reward ratio'],
  },
];

// ── Intersection Observer Hook ──────────────────────────────────────
function useScrollReveal() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add('opacity-100', 'translate-y-0');
          el.classList.remove('opacity-0', 'translate-y-8');
          observer.unobserve(el);
        }
      },
      { threshold: 0.15 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return ref;
}

function RevealSection({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  const ref = useScrollReveal();
  return (
    <div ref={ref} className={`opacity-0 translate-y-8 transition-all duration-700 ease-out ${className}`}>
      {children}
    </div>
  );
}

// ── Google Sign-In Button ───────────────────────────────────────────
function GoogleSignInButton({ width = 300 }: { width?: number }) {
  const { login } = useAuth();
  const buttonRef = useRef<HTMLDivElement>(null);

  const handleGoogleCallback = useCallback(
    async (response: GoogleCredentialResponse) => {
      try {
        const { user } = await googleLogin(response.credential);
        login(user);
      } catch (error) {
        console.error('Login failed:', error);
        alert('Login failed. Please try again.');
      }
    },
    [login]
  );

  useEffect(() => {
    if (window.google && buttonRef.current) {
      window.google.accounts.id.initialize({
        client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
        callback: handleGoogleCallback,
      });
      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: 'filled_blue',
        size: 'large',
        text: 'signin_with',
        width,
      });
    }
  }, [handleGoogleCallback, width]);

  return <div ref={buttonRef} />;
}

// ── Feature Card ────────────────────────────────────────────────────
function FeatureCard({ feature, index }: { feature: (typeof features)[number]; index: number }) {
  const Icon = feature.icon;
  const isEven = index % 2 === 0;

  return (
    <RevealSection>
      <div className={`flex flex-col ${isEven ? 'lg:flex-row' : 'lg:flex-row-reverse'} gap-8 items-center`}>
        {/* Icon side */}
        <div className="flex-shrink-0 flex items-center justify-center w-20 h-20 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
          <Icon />
        </div>

        {/* Content side */}
        <div className="flex-1 text-center lg:text-left">
          <h3 className="text-2xl font-bold text-white mb-1">{feature.title}</h3>
          <p className="text-blue-400 font-medium mb-3">{feature.tagline}</p>
          <p className="text-gray-400 mb-4 max-w-xl">{feature.description}</p>
          <ul className="flex flex-wrap gap-2 justify-center lg:justify-start">
            {feature.highlights.map((h) => (
              <li
                key={h}
                className="text-xs font-medium px-3 py-1 rounded-full bg-gray-800 text-gray-300 border border-gray-700"
              >
                {h}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </RevealSection>
  );
}

// ── Main Landing Page ───────────────────────────────────────────────
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* ─── Sticky Header ─── */}
      <header className="sticky top-0 z-50 bg-gray-950/80 backdrop-blur-md border-b border-gray-800/50">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <span className="text-xl font-bold text-white tracking-tight">StockCerebro</span>
          <GoogleSignInButton width={200} />
        </div>
      </header>

      {/* ─── Hero Section ─── */}
      <section className="relative overflow-hidden">
        {/* Gradient background */}
        <div className="absolute inset-0 bg-gradient-to-b from-blue-950/40 via-gray-950 to-gray-950 pointer-events-none" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-blue-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative max-w-4xl mx-auto px-4 pt-24 pb-20 text-center">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white leading-tight mb-6">
            Smarter Stock Analysis,{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">
              Powered by Data
            </span>
          </h1>
          <p className="text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Multi-source fundamental and technical analysis with actionable buy/sell signals.
            Aggregate data from Yahoo Finance, Finnhub, and SEC EDGAR in one unified dashboard.
          </p>
          <div className="flex justify-center">
            <GoogleSignInButton width={300} />
          </div>
        </div>
      </section>

      {/* ─── Features ─── */}
      <section className="max-w-5xl mx-auto px-4 py-20">
        <RevealSection className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">Everything You Need to Analyze a Stock</h2>
          <p className="text-gray-400 max-w-2xl mx-auto">
            Six powerful tools working together to give you a complete picture of any publicly traded company.
          </p>
        </RevealSection>

        <div className="space-y-16">
          {features.map((feature, i) => (
            <FeatureCard key={feature.title} feature={feature} index={i} />
          ))}
        </div>
      </section>

      {/* ─── Final CTA ─── */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-t from-blue-950/30 via-gray-950 to-gray-950 pointer-events-none" />
        <RevealSection className="relative max-w-3xl mx-auto px-4 py-24 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">Ready to Analyze?</h2>
          <p className="text-gray-400 mb-8 text-lg">
            Sign in and start making smarter investment decisions today.
          </p>
          <div className="flex justify-center">
            <GoogleSignInButton width={300} />
          </div>
        </RevealSection>
      </section>

      {/* ─── Footer ─── */}
      <footer className="border-t border-gray-800/50 py-8">
        <p className="text-center text-gray-600 text-sm">
          &copy; {new Date().getFullYear()} StockCerebro. All rights reserved.
        </p>
      </footer>
    </div>
  );
}
