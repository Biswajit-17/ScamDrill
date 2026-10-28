const TACTIC_LABELS = {
  authority: "Authority",
  urgency: "Urgency",
  fear: "Fear",
  isolation: "Isolation",
  trust_building: "Trust building",
  verification_blocking: "Blocking verification",
  credential_request: "Credential request",
  remote_access: "Remote access",
  payment_request: "Payment request",
}

export default function Debrief({ debrief, state, onShare, onRestart, onPostQuiz }) {
  if (!debrief) {
    return (
      <div className="max-w-md mx-auto px-4 py-16 text-center text-slate-600">
        Preparing your debrief...
      </div>
    )
  }

  const taken = (state && state.decisions_taken) || []
  const outcomeFor = (id) => {
    const t = taken.find((d) => d.decision_id === id)
    return t ? t.outcome : null
  }
  const weak = Object.entries(debrief.weak_spot_map || {})
  const worked = weak.filter(([, v]) => v === "worked")
  const resisted = weak.filter(([, v]) => v !== "worked")
  const label = (t) => TACTIC_LABELS[t] || t.replace(/_/g, " ")

  return (
    <div className="max-w-md mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-red-700 mb-2">Call debrief</h2>
        <p className="text-slate-600">Here is how the pressure tactics landed on you.</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
        <h3 className="font-semibold mb-2">Summary</h3>
        <p className="text-slate-700">{debrief.summary}</p>
      </div>

      {debrief.moments && debrief.moments.length > 0 && (
        <div className="mb-6">
          <h3 className="font-semibold mb-3">Your key moments</h3>
          <div className="space-y-4">
            {debrief.moments.map((m, i) => {
              const outcome = outcomeFor(m.decision_id)
              return (
                <div key={i} className="border-l-4 border-slate-200 pl-4 py-1">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-medium text-slate-700">Moment {i + 1}</span>
                    {outcome && (
                      <span
                        className={
                          "text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded " +
                          (outcome === "safe"
                            ? "bg-green-100 text-green-700"
                            : "bg-red-100 text-red-700")
                        }
                      >
                        {outcome === "safe" ? "Safe" : "Risky"}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-600 mb-2">{m.what_happened}</p>
                  <p className="text-sm text-green-700">{m.say_instead}</p>
                </div>
              )
            })}
          </div>
        </div>
      )}

      <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 mb-6">
        <h3 className="font-semibold mb-2 text-amber-800">Your weak spots</h3>
        {worked.length > 0 ? (
          <>
            <p className="text-sm text-amber-700 mb-3">
              These tactics worked on you. Learn to spot them.
            </p>
            <ul className="space-y-1 mb-3">
              {worked.map(([t]) => (
                <li key={t} className="text-sm font-semibold text-red-700">
                  {label(t)}
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="text-sm text-amber-700 mb-3">No tactic got you this time. Nice work.</p>
        )}
        {resisted.length > 0 && (
          <>
            <p className="text-sm text-amber-700 mb-1">You resisted:</p>
            <ul className="space-y-1">
              {resisted.map(([t]) => (
                <li key={t} className="text-sm font-semibold text-green-700">
                  {label(t)}
                </li>
              ))}
            </ul>
          </>
        )}
      </div>

      {debrief.rules && debrief.rules.length > 0 && (
        <div className="mb-8">
          <h3 className="font-semibold mb-3">Three rules to remember</h3>
          <ol className="list-decimal list-inside space-y-2 text-sm text-slate-700">
            {debrief.rules.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ol>
        </div>
      )}

      {onPostQuiz && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 mb-6 text-center">
          <p className="text-sm text-slate-600 mb-3">Check what stuck: take a short 5-question follow-up quiz.</p>
          <button
            onClick={onPostQuiz}
            className="px-5 py-2 rounded-lg bg-slate-800 text-white font-semibold hover:bg-slate-900 transition"
          >
            Take the post-quiz
          </button>
        </div>
      )}
      <div className="flex gap-3">
        <button
          onClick={onShare}
          className="flex-1 py-3 rounded-lg border border-slate-300 text-slate-700 font-semibold hover:bg-slate-100 transition"
        >
          Share weak-spot card
        </button>
        <button
          onClick={onRestart}
          className="flex-1 py-3 rounded-lg bg-red-600 text-white font-semibold hover:bg-red-700 transition"
        >
          Try another scenario
        </button>
      </div>
    </div>
  )
}