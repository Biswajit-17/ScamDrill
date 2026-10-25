export default function Debrief({ debrief, state, onGoDebrief, onShare, onRestart }) {
  const outcomeLabel = (v) => (v === "worked" ? "Worked on you" : "You resisted")

  return (
    <div className="max-w-md mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-red-700 mb-2">Call debrief</h2>
        <p className="text-slate-600">
          Here's how the pressure tactics landed on you.
        </p>
      </div>

      {/* Summary */}
      {debrief && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
          <h3 className="font-semibold mb-2">Summary</h3>
          <p className="text-slate-700">{debrief.summary}</p>
          {debrief.fallback_used && (
            <p className="text-[11px] text-slate-400 mt-3">
              (Coach fallback used — the AI debrief was unavailable.)
            </p>
          )}
        </div>
      )}

      {/* Tactic timeline / moments */}
      <div className="mb-6">
        <h3 className="font-semibold mb-3">Tactic timeline</h3>
        <div className="space-y-3">
          {debrief?.moments.map((m, i) => (
            <div key={i} className="border-l-2 border-slate-200 pl-4 py-2">
              <div className="flex justify-between text-sm mb-1">
                <span className="font-medium text-slate-700">{m.decision_id}</span>
                <span className="text-[10px] font-bold uppercase tracking-wider">
                  {m.decision_id === "none" ? "n/a" : ""}
                </span>
              </div>
              <p className="text-sm text-slate-600 mb-1">{m.what_happened}</p>
              <p className="text-sm text-green-700">{m.say_instead}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Weak-spot card */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 mb-6">
        <h3 className="font-semibold mb-3 text-amber-800">Your weak spots</h3>
        <p className="text-sm text-amber-700 mb-3">
          These are the tactics that worked on you. Know them so you can spot them
          next time.
        </p>
        <div className="space-y-2">
          {Object.entries(debrief?.weak_spot_map || {}).map(([tactic, result]) => (
            <div
              key={tactic}
              className="flex justify-between items-center text-sm"
            >
              <span className={result === "worked" ? "text-red-700 font-semibold" : "text-green-700 font-semibold"}>
                {tactic.replace(/_/g, " ")}
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded border text-[10px] font-bold uppercase">
                {result === "worked" ? "worked" : "resisted"}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Rules */}
      <div className="mb-8">
        <h3 className="font-semibold mb-3">Three plain-language rules</h3>
        <ol className="list-disc list-inside space-y-2 text-sm text-slate-700">
          {debrief?.rules.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ol>
      </div>

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