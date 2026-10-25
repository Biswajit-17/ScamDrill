import { useEffect } from 'react'

export default function Home({ scenarios, startQuiz, startCall, error, loadScenarios }) {
  useEffect(() => {
    loadScenarios()
  }, [loadScenarios])

  const disclaimer =
    "Practice simulation. Everything here is fictional. Never type real personal data."

  return (
    <div className="max-w-md mx-auto px-4 py-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-red-700 mb-2">ScamDrill</h1>
        <p className="text-slate-600 mb-6">
          A practice simulator for recognising scam calls. Play through a fictional
          call, make decisions, and see which pressure tactics worked on you.
        </p>
      </div>

      {/* Disclaimer banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6 text-sm text-amber-800">
        {disclaimer}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-sm text-red-800">
          {error}
        </div>
      )}

      {/* Scenario picker */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-3">1. Pick a scenario</h2>
        <div className="space-y-3">
          {scenarios.length === 0 ? (
            <p className="text-slate-500">Loading scenarios…</p>
          ) : (
            scenarios.map((s) => (
              <button
                key={s.id}
                onClick={() => startCall(s.id, "en")}
                className="w-full text-left border border-slate-200 rounded-lg p-4 hover:bg-slate-50 hover:border-red-300 transition"
              >
                <div className="font-semibold">{s.title}</div>
                <div className="text-xs text-slate-500 mt-1">
                  {s.id === "bank_call"
                    ? "A fictional bank security call."
                    : "A fictional parcel delivery fee call."}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Pre-quiz */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-3">2. Take the pre-quiz (5 questions)</h2>
        <p className="text-sm text-slate-600 mb-4">
          Warm up before the call. This is not scored against you.
        </p>
        <button
          onClick={startQuiz}
          className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded-lg shadow"
        >
          Start pre-quiz
        </button>
      </div>

      <div className="text-center text-xs text-slate-400 mt-8">
        ScamDrill — practice tool. Not a study, not official advice.
      </div>
    </div>
  )
}