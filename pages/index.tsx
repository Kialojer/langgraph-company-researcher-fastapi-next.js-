import { useState, FormEvent } from 'react';
import { useAuth, SignInButton, SignedIn, SignedOut, UserButton } from '@clerk/nextjs';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import ReactMarkdown from 'react-markdown';

export default function Home() {
  const { getToken } = useAuth();
  
  // Form States
  const [company, setCompany] = useState('');
  const [output, setOutput] = useState('');
  const [loading, setLoading] = useState(false);

  // Submit Handler
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setOutput('');
    setLoading(true);

    // 1. Get Clerk JWT Token
    const jwt = await getToken();
    if (!jwt) {
      setOutput('❌ Error: Authentication required. Please sign in.');
      setLoading(false);
      return;
    }

    let buffer = '';
    const controller = new AbortController();

    try {
      // 2. Open SSE stream with FastAPI backend
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
      await fetchEventSource(`${apiUrl}/api/generate-report`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${jwt}`,
        },
        body: JSON.stringify({ company }),
        signal: controller.signal,
        
        // 3. Catch streaming words
        onmessage(ev) {
          if (ev.data === '[DONE]') {
            setLoading(false);
            return;
          }
          try {
            const parsedData = JSON.parse(ev.data);
            if (parsedData.text) {
              buffer += parsedData.text;
              setOutput(buffer); // Live UI update
            }
          } catch (err) {
            console.error("Error parsing stream data:", err);
          }
        },
        onerror(err) {
          console.error('SSE Error:', err);
          setLoading(false);
          controller.abort();
        }
      });
    } catch (err) {
      console.error("Fetch request failed:", err);
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 text-gray-900 p-8">
      <div className="max-w-2xl mx-auto">
        
        {/* Header & Auth Section */}
        <header className="flex justify-between items-center mb-10 bg-white p-4 rounded-xl shadow-sm">
          <h1 className="text-2xl font-bold text-blue-600">Financial Analyst Agent</h1>
          <div>
            <SignedOut>
              <SignInButton mode="modal">
                <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                  Sign In
                </button>
              </SignInButton>
            </SignedOut>
            <SignedIn>
              <UserButton afterSignOutUrl="/" />
            </SignedIn>
          </div>
        </header>

        {/* Input Form (Protected) */}
        <SignedIn>
          <div className="bg-white p-6 rounded-xl shadow-sm mb-8">
            <form onSubmit={handleSubmit} className="flex gap-4">
              <input
                type="text"
                required
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="Enter company name (e.g., Tesla or Apple)"
                className="flex-1 border border-gray-300 p-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button 
                type="submit" 
                disabled={loading}
                className="bg-gray-900 text-white px-6 py-3 rounded-lg hover:bg-gray-800 disabled:opacity-50 transition-colors whitespace-nowrap"
              >
                {loading ? 'Analyzing...' : 'Generate Report'}
              </button>
            </form>
          </div>

          {/* Streaming Output Box */}
          {output && (
            <div className="bg-white p-6 rounded-xl shadow-sm border-l-4 border-blue-600">
              <div className="prose prose-blue max-w-none">
                <ReactMarkdown>{output}</ReactMarkdown>
              </div>
            </div>
          )}
        </SignedIn>

        {/* Logged Out Message */}
        <SignedOut>
          <div className="text-center mt-20 text-gray-500">
            Please sign in to access the AI assistant.
          </div>
        </SignedOut>

      </div>
    </main>
  );
}