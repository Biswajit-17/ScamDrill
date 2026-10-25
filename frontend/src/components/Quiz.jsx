export default function Quiz({ questions, index, answers, isPreQuiz, onAnswer }) {
  const q = questions[index]
  const isLast = index + 1 >= questions.length

  return (
    <div className="max-w-md mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
          {isPreQuiz ? "Pre-quiz" : "Post-quiz"}
        </span>
        <span className="text-sm font-medium text-slate-700">
          Question {index + 1} of {questions.length}
        </span>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">{q.question}</h2>
        <div className="space-y-3">
          {q.options.map((opt) => {
            const selected = answers[q.id] === opt.id
            return (
              <button
                key={opt.id}
                onClick={() => onAnswer(opt.id)}
                className={`w-full text-left py-3 px-4 rounded-lg border transition ${
                  selected
                    ? "bg-red-50 border-red-300 text-red-800"
                    : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                }`}
              >
                {opt.text}
              </button>
            )
          })}
        </div>
      </div>

      <div className="flex justify-between">
        {index > 0 && (
          <button
            onClick={() => onAnswer(null)}
            className="text-slate-500 hover:text-slate-700 text-sm"
            disabled
          >
            Previous
          </button>
        )}
        <button
          onClick={() => onAnswer(answers[q.id])}
          disabled={!answers[q.id]}
          className={`px-6 py-2 rounded-lg font-semibold transition ${
            !answers[q.id]
              ? "bg-slate-300 text-slate-500 cursor-not-allowed"
              : "bg-red-600 text-white hover:bg-red-700"
          }`}
        >
          {isLast ? "See results" : "Next"}
        </button>
      </div>

      <div className="text-center text-xs text-slate-400 mt-8">
        ScamDrill — practice quiz. Not a study.
      </div>
    </div>
  )
}