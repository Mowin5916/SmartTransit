export async function askTransitAssistant(prompt: string) {
  const apiKey = process.env.NEXT_PUBLIC_GEMINI_API_KEY;

  if (!apiKey) {
    console.error('❌ Gemini API key missing');
    return 'AI assistant is not configured.';
  }

  const res = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [
          {
            role: 'user',
            parts: [
              {
                text: `
You are a helpful Bengaluru city bus transit assistant.
Answer clearly in 1–2 sentences.

User question:
${prompt}
`
              }
            ]
          }
        ]
      })
    }
  );

  const data = await res.json();

  // 🔍 DEBUG (temporarily)
  console.log('🧠 Gemini raw response:', data);

  if (data.error) {
    console.error('❌ Gemini API error:', data.error);
    return 'AI service is temporarily unavailable.';
  }

  const text =
    data?.candidates?.[0]?.content?.parts?.[0]?.text;

  return text || 'I could not generate a response for that.';
}
