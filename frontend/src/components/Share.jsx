export default function Share({ data, onBack }) {
  const copy = (label, value) => {
    navigator.clipboard.writeText(value || "")
    // tiny toast could go here; keep simple
  }

  return (
    <div className="max-w-md mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-red-700 mb-2">Share practice</h2>
        <p className="text-slate-600">No accounts. No database. Just a link.</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6 space-y-4">
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Send this practice to a family member</p>
          <div className="flex gap-2">
            <input
              type="text"
              value={data?.practiceUrl || ""}
              readOnly
              className="flex-1 px-4 py-3 rounded-lg border border-slate-300 text-sm"
            />
            <button
              onClick={() => copy("practice", data?.practiceUrl)}
              className="px-4 py-3 rounded-lg bg-red-600 text-white font-semibold hover:bg-red-700"
            >
              Copy
            </button>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            Pre-selects scenario and language for the person you share with.
          </p>
        </div>

        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Copy link to your weak-spot card</p>
          <div className="flex gap-2">
            <input
              type="text"
              value={data?.weakSpotUrl || ""}
              readOnly
              className="flex-1 px-4 py-3 rounded-lg border border-slate-300 text-sm"
            />
            <button
              onClick={() => copy("weakspot", data?.weakSpotUrl)}
              className="px-4 py-3 rounded-lg bg-red-600 text-white font-semibold hover:bg-red-700"
            >
              Copy
            </button>
          </div>
        </div>
      </div>

      <div className="text-center">
        <button
          onClick={onBack}
          className="px-6 py-3 rounded-lg bg-red-600 text-white font-semibold hover:bg-red-700 transition"
        >
          Back to debrief
        </button>
      </div>
    </div>
  )
}