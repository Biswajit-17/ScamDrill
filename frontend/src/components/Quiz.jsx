import { useState } from "react"

export default function Quiz({
  questions,
  index,
  answers,
  isPreQuiz,
  done,
  score,
  preScore,
  preTaken,
  scenarios = [],
  onAnswer,
  onNext,
  onStartCall,
  onHome,
}) {
  const [seed] = useState(() => String(Math.random()))
  const hash = (s) => { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return h }
  const shuffled = (qq) => [...qq.options].sort((a, b) => hash(qq.id + a.id + seed) - hash(qq.id + b.id + seed))
  const total = questions.length
  const textOf = (q, id) => (q.options.find((o) => o.id === id) || {}).text

  if (done) {
    return (
      <div className="max-w-md mx-auto px-4 py-8">
        <h2 className="text-2xl font-bold text-red-700 text-center mb-2">
          {isPreQuiz ? "Pre-quiz results" : "Post-quiz results"}
        </h2>
        <p className="text-center text-slate-700 mb-6">
          You got {score} of {total} right.
        </p>

        {!isPreQuiz && preTaken && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6 text-center text-sm text-amber-800">
            Pre-quiz: {preScore} of {total}. Post-quiz: {score} of {total}.
            <div className="text-[11px] text-amber-700 mt-1">A short practice check, not a study.</div>
          </div>
        )}

        <div className="space-y-3 mb-8">
          {questions.map((q) => {
            const picked = answers[q.id]
            const ok = picked === q.correct
            return (
              <div key={q.id} className="bg-white rounded-lg border border-slate-200 p-4">
                <p className="text-sm font-medium text-slate-800 mb-1">
                  {ok ? "Correct: " : "Not quite: "}
                  {q.question}
                </p>
                {!ok && (
                  <p className="text-xs text-red-700">Your answer: {textOf(q, picked) || "No answer"}</p>
                )}
                <p className="text-xs text-green-700">
                  {ok ? "" : "Right answer: "}
                  {textOf(q, q.correct)}
                </p>
              </div>
            )
          })}
        </div>

        {isPreQuiz ? (
          <div>
            <h3 className="font-semibold mb-3 text-center">Now pick a call to practise</h3>
            <div className="space-y-3">
              {scenarios.map((s) => (
                <button
                  key={s.id}
                  onClick={() => onStartCall(s.id)}
                  className="w-full py-3 rounded-lg bg-red-600 text-white font-semibold hover:bg-red-700 transition"
                >
                  {s.title}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <button
            onClick={onHome}
            className="w-full py-3 rounded-lg bg-red-600 text-white font-semibold hover:bg-red-700 transition"
          >
            Back to start
          </button>
        )}
      </div>
    )
  }

  const q = questions[index]
  const picked = answers[q.id]
  const isLast = index + 1 >= total

  return (
    <div className="max-w-md mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
          {isPreQuiz ? "Pre-quiz" : "Post-quiz"}
        </span>
        <span className="text-sm font-medium text-slate-700">
          Question {index + 1} of {total}
        </span>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">{q.question}</h2>
        <div className="space-y-3">
          {shuffled(q).map((opt) => {
            let cls = "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
            if (picked) {
              if (opt.id === q.correct) cls = "bg-green-50 border-green-300 text-green-800"
              else if (opt.id === picked) cls = "bg-red-50 border-red-300 text-red-800"
              else cls = "bg-white border-slate-200 text-slate-400"
            }
            return (
              <button
                key={opt.id}
                onClick={() => onAnswer(opt.id)}
                disabled={!!picked}
                className={"w-full text-left py-3 px-4 rounded-lg border transition " + cls}
              >
                {opt.text}
              </button>
            )
          })}
        </div>
        {picked && (
          <p className="text-sm mt-4 text-slate-600">
            {picked === q.correct ? "Correct." : "Not quite. The right answer is in green."}
          </p>
        )}
      </div>

      <div className="flex justify-end">
        <button
          onClick={onNext}
          disabled={!picked}
          className={
            "px-6 py-2 rounded-lg font-semibold transition " +
            (!picked
              ? "bg-slate-300 text-slate-500 cursor-not-allowed"
              : "bg-red-600 text-white hover:bg-red-700")
          }
        >
          {isLast ? "See results" : "Next"}
        </button>
      </div>

      <div className="text-center text-xs text-slate-400 mt-8">
        ScamDrill: practice quiz. Not a study.
      </div>
    </div>
  )
}