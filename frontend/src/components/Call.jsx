export default function Call({
  callerLine,
  tactics,
  stage,
  decisionCard,
  callEnded,
  inputMasked,
  userInput,
  onUserInput,
  onSubmit,
  onDecision,
  onHangUp,
  loading,
  error,
}) {
  const tacticLabels = {
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

  return (
    <div className="max-w-md mx-auto px-4 py-4 h-[calc(100vh-4rem)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-slate-500 uppercase">
          Stage: {stage}
        </span>
        <button
          onClick={onHangUp}
          className="text-xs font-semibold text-red-600 hover:underline flex items-center gap-1"
        >
          📞 Hang up
        </button>
      </div>

      {/* Masked warning */}
      {inputMasked && (
        <div className="mb-3 p-2 rounded bg-amber-100 border border-amber-200 text-xs text-amber-800">
          Some of your input was masked before being sent (no personal data is logged).
        </div>
      )}

      {error && (
        <div className="mb-3 p-2 rounded bg-red-100 border border-red-200 text-xs text-red-800">
          {error}
        </div>
      )}

      {/* Transcript area */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-4 pr-2">
        {decisionCard ? null : (
          <div className="flex flex-start">
            <div className="bg-red-600 text-white text-xs rounded-lg px-3 py-2 max-w-[80%]">
              {callerLine}
            </div>
          </div>
        )}
        {tactics.length > 0 && !decisionCard && (
          <div className="flex flex-start">
            <div className="ml-3">
              {tactics.map((t) => (
                <span
                  key={t}
                  className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mt-0.5"
                >
                  {tacticLabels[t] || t}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Decision modal overlay */}
      {decisionCard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md border border-slate-200"
          >
            <h3 className="font-semibold text-lg mb-3">Decision</h3>
            <p className="text-slate-700 mb-4">{decisionCard.prompt}</p>
            <div className="space-y-2">
              {decisionCard.options.map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => onDecision(opt.id)}
                  className="w-full text-left py-3 px-4 rounded-lg border border-slate-200 text-left text-slate-700 hover:bg-slate-50 transition"
                >
                  {opt.text}
                </button>
              ))}
            </div>
            <p className="text-[11px] text-slate-400 mt-4 text-center">
              Pick an option to continue the call.
            </p>
          </div>
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
            onClick={onDecision} // clicking backdrop does nothing; requires explicit option
          />
        </div>
      )}

      {/* Input area */}
      {!callEnded && !decisionCard && (
        <div className="mt-auto pt-4 border-t border-slate-200">
          <form onSubmit={onSubmit} className="flex gap-2">
            <input
              type="text"
              value={userInput}
              onChange={(e) => onUserInput(e.target.value)}
              placeholder="Type your response…"
              disabled={loading}
              className="flex-1 px-4 py-3 rounded-lg border border-slate-300 focus:ring-2 focus:ring-red-500 focus:border-transparent outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={loading || !userInput.trim()}
              className="px-5 py-3 rounded-lg bg-red-600 text-white font-semibold hover:bg-red-700 disabled:opacity-50 transition"
            >
              Send
            </button>
          </form>
        </div>
      )}

      {callEnded && (
        <div className="mt-auto pt-4 text-center">
          <p className="text-sm text-slate-500 mb-4">The call has ended.</p>
          <button
            onClick={onHangUp}
            className="px-6 py-3 rounded-lg bg-red-600 text-white font-semibold hover:bg-red-700 transition"
          >
            Go to debrief
          </button>
        </div>
      )}
    </div>
  )
}