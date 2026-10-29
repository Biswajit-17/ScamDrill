import { useEffect, useRef } from "react"

export default function Call({
  transcript,
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
  const bottomRef = useRef(null)

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [transcript, decisionCard, loading])

  const messages = transcript || []

  return (
    <div className="max-w-md mx-auto px-4 py-4 h-[calc(100vh-4rem)] flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-slate-500 uppercase">Incoming call</span>
        <button
          onClick={onHangUp}
          className="text-xs font-semibold text-red-600 hover:underline"
        >
          Hang up
        </button>
      </div>

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

      <div className="flex-1 overflow-y-auto mb-4 space-y-3 pr-2">
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div
              className={
                (m.role === "user" ? "bg-slate-200 text-slate-800" : "bg-red-600 text-white") +
                " text-sm rounded-lg px-3 py-2 max-w-[80%]"
              }
            >
              {m.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-red-100 text-red-700 text-sm rounded-lg px-3 py-2">...</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {decisionCard && !callEnded && (
        <div className="mt-auto pt-3 border-t border-slate-200">
          <p className="text-sm font-semibold text-slate-800 mb-2">{decisionCard.prompt}</p>
          <div className="space-y-2">
            {decisionCard.options.map((opt) => (
              <button
                key={opt.id}
                onClick={() => onDecision(opt.id)}
                disabled={loading}
                className="w-full text-left py-3 px-4 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition"
              >
                {opt.text}
              </button>
            ))}
          </div>
        </div>
      )}

      {!callEnded && !decisionCard && (
        <div className="mt-auto pt-4 border-t border-slate-200">
          <form onSubmit={onSubmit} className="flex gap-2">
            <input
              type="text"
              value={userInput}
              onChange={(e) => onUserInput(e.target.value)}
              placeholder="Type your reply (use made-up details)..."
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