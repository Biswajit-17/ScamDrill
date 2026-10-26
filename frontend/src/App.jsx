import { useState, useCallback, useEffect } from 'react'
import { api } from './api'
import Home from './components/Home'
import Quiz from './components/Quiz'
import Call from './components/Call'
import Debrief from './components/Debrief'
import Share from './components/Share'

const SCREENS = {
  HOME: 'home',
  QUIZ: 'quiz',
  CALL: 'call',
  DEBRIEF: 'debrief',
  SHARE: 'share',
}

export default function App() {
  const [screen, setScreen] = useState(SCREENS.HOME)
  const [scenarios, setScenarios] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // ---- Quiz state ----
  const [quizIndex, setQuizIndex] = useState(0)
  const [quizAnswers, setQuizAnswers] = useState({})
  const [quizScore, setQuizScore] = useState({ pre: 0, post: 0 })
  const [isPreQuiz, setIsPreQuiz] = useState(true)

  // ---- Call state ----
  const [state, setState] = useState(null)
  const [callerLine, setCallerLine] = useState("")
  const [tactics, setTactics] = useState([])
  const [stage, setStage] = useState("")
  const [decisionCard, setDecisionCard] = useState(null)
  const [callEnded, setCallEnded] = useState(false)
  const [userInput, setUserInput] = useState("")
  const [inputMasked, setInputMasked] = useState(false)

  // ---- Debrief state ----
  const [debrief, setDebrief] = useState(null)

  // ---- Share state ----
  const [shareData, setShareData] = useState(null)

  // ---- Lifecycle: load scenarios ----
  const loadScenarios = useCallback(async () => {
    try {
      const list = await api.listScenarios()
      setScenarios(list)
    } catch (e) {
      setError("Could not load scenarios. Is the backend running?")
    }
  }, [])

    useEffect(() => {
    loadScenarios()
  }, [loadScenarios])

  // ---- Quiz ----
  const QUIZ_PRE = [
    {
      id: "q1",
      question: "You get a call from someone claiming to be your bank. The caller ID shows the bank's number. Is this proof it's really the bank?",
      options: [
        { id: "a", text: "Yes, caller ID cannot be faked." },
        { id: "b", text: "No, caller ID can be spoofed." },
        { id: "c", text: "Only if they know your account details." },
      ],
      correct: "b",
    },
    {
      id: "q2",
      question: "A caller says there's a suspicious payment and asks for the one-time code just sent to your phone. What should you do?",
      options: [
        { id: "a", text: "Read the code out so they can stop the payment." },
        { id: "b", text: "Never share the code; hang up and call the bank on the number from your card." },
        { id: "c", text: "Give the code but ask them not to transfer money." },
      ],
      correct: "b",
    },
    {
      id: "q3",
      question: "A caller creates urgency, saying your account will be frozen in an hour unless you act now. What is the safest response?",
      options: [
        { id: "a", text: "Act immediately to avoid losing access." },
        { id: "b", text: "Take your time; hang up and call back through an official channel." },
        { id: "c", text: "Ask the caller to stay on the line while you check." },
      ],
      correct: "b",
    },
    {
      id: "q4",
      question: "You get a text saying a parcel is being held and you must pay a small redelivery fee via a link. What should you do?",
      options: [
        { id: "a", text: "Click the link and pay the fee right away." },
        { id: "b", text: "Ignore it and check the courier's official website or app yourself." },
        { id: "c", text: "Call the number in the text to confirm." },
      ],
      correct: "b",
    },
    {
      id: "q5",
      question: "A caller asks you to install a 'security app' on your phone to protect your account. What should you do?",
      options: [
        { id: "a", text: "Install it; the caller is from the bank's security team." },
        { id: "b", text: "Never install software a caller asks you to install." },
        { id: "c", text: "Install it but uninstall it after the call." },
      ],
      correct: "b",
    },
  ]

  const QUIZ_POST = [
    {
      id: "q6",
      question: "A caller says money is being moved to a 'safe account' to protect it. Is a safe account a real thing your bank would ask you to use?",
      options: [
        { id: "a", text: "Yes, banks move money to safe accounts during fraud." },
        { id: "b", text: "No, 'safe account' is a scam myth." },
        { id: "c", text: "Only if the caller confirms your details first." },
      ],
      correct: "b",
    },
    {
      id: "q7",
      question: "A caller knows your recent transaction amount and uses it to prove they're from your bank. Does this prove their identity?",
      options: [
        { id: "a", text: "Yes, only the bank would know that." },
        { id: "b", text: "No, scammers can obtain partial details." },
        { id: "c", text: "Only if they also know your full name." },
      ],
      correct: "b",
    },
    {
      id: "q8",
      question: "You're told not to hang up or tell anyone about the call. What does this indicate?",
      options: [
        { id: "a", text: "The bank genuinely needs secrecy." },
        { id: "b", text: "A common scam tactic to isolate you from outside advice." },
        { id: "c", text: "The matter is highly classified." },
      ],
      correct: "b",
    },
    {
      id: "q9",
      question: "What is the best way to call your bank back after a suspicious call?",
      options: [
        { id: "a", text: "Call the number the caller gave you." },
        { id: "b", text: "Call the number on the back of your bank card or statement." },
        { id: "c", text: "Call the number from a Google search." },
      ],
      correct: "b",
    },
    {
      id: "q10",
      question: "If you realize you may have shared details with a scammer, what should you do first?",
      options: [
        { id: "a", text: "Wait and see if money goes missing." },
        { id: "b", text: "Contact your bank immediately through an official channel." },
        { id: "c", text: "Change your email password only." },
      ],
      correct: "b",
    },
  ]

  const quizQuestions = isPreQuiz ? QUIZ_PRE : QUIZ_POST

  const startQuiz = () => {
    setIsPreQuiz(true)
    setQuizIndex(0)
    setQuizAnswers({})
    setQuizScore({ pre: 0, post: 0 })
    setScreen(SCREENS.QUIZ)
  }

  const answerQuiz = (optionId) => {
    const q = quizQuestions[quizIndex]
    const next = { ...quizAnswers, [q.id]: optionId }
    setQuizAnswers(next)
    if (quizIndex + 1 >= quizQuestions.length) {
      let score = 0
      quizQuestions.forEach((qq) => {
        const answered = quizAnswers[qq.id] !== undefined ? quizAnswers[qq.id] : (qq.id === q.id ? optionId : null)
        if (answered === qq.correct) score++
      })
      if (isPreQuiz) {
        setQuizScore({ ...quizScore, pre: score })
        setIsPreQuiz(false)
        setQuizIndex(0)
        setQuizAnswers({})
      } else {
        setQuizScore({ ...quizScore, post: score })
        setScreen(SCREENS.HOME)
      }
    } else {
      setQuizIndex(quizIndex + 1)
    }
  }

  // ---- Call ----
  const startCall = async (scenarioId, language = "en") => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.callStart({ scenario_id: scenarioId, language })
      const newState = {
        scenario_id: scenarioId,
        language,
        current_stage_id: res.stage,
        stage_turns: res.stage_turns,
        total_turns: 0,
        hang_up: false,
        call_ended: res.call_ended,
        transcript: [{ role: "caller", content: res.caller_line, tactics: res.tactics }],
        decisions_taken: [],
        weak_spot_map: {},
        fallback_used: res.fallback_used,
      }
      setState(newState)
      setCallerLine(res.caller_line)
      setTactics(res.tactics)
      setStage(res.stage)
      setDecisionCard(res.decision_card)
      setCallEnded(res.call_ended)
      setScreen(SCREENS.CALL)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleUserInput = async (e) => {
    e.preventDefault()
    if (!userInput.trim()) return
    const msg = userInput
    setUserInput("")
    setLoading(true)
    try {
      const res = await api.callTurn({ state, user_message: msg })
      setState(res.state || state)
      setCallerLine(res.caller_line)
      setTactics(res.tactics)
      setStage(res.stage)
      setDecisionCard(res.decision_card)
      setCallEnded(!!res.call_ended)
      setInputMasked(!!res.masked)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDecision = async (optionId) => {
    if (!decisionCard) return
    setLoading(true)
    try {
      const res = await api.callDecision({
        state,
        decision_id: decisionCard.id,
        option_id: optionId,
      })
      const optText = (decisionCard.options.find((o) => o.id === optionId) || {}).text || ""
      setDecisionCard(null)
      const next = await api.callTurn({ state: res.state, user_message: optText })
      setState(next.state || res.state)
      setCallerLine(next.caller_line)
      setTactics(next.tactics)
      setStage(next.stage)
      setDecisionCard(next.decision_card)
      setCallEnded(!!next.call_ended)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleHangUp = () => {
    setCallEnded(true)
    setScreen(SCREENS.DEBRIEF)
  }

  // ---- Debrief ----
  const goDebrief = async () => {
    setLoading(true)
    try {
      const res = await api.callDebrief({ state })
      setDebrief(res)
      setScreen(SCREENS.DEBRIEF)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // ---- Share ----
  const buildShare = () => {
    if (!state) return
    const params = new URLSearchParams({ scenario: state.scenario_id, lang: state.language })
    setShareData({
      weakSpotUrl: window.location.origin + window.location.pathname + "?" + params.toString() + "#weakspot",
      practiceUrl: window.location.origin + window.location.pathname + "?" + params.toString(),
    })
    setScreen(SCREENS.SHARE)
  }

  // ---- Render ----
  return (
    <div className="min-h-screen">
      {screen === SCREENS.HOME && (
        <Home
          scenarios={scenarios}
          startQuiz={startQuiz}
          startCall={startCall}
          error={error}
          loadScenarios={loadScenarios}
        />
      )}
      {screen === SCREENS.QUIZ && (
        <Quiz
          questions={quizQuestions}
          index={quizIndex}
          answers={quizAnswers}
          isPreQuiz={isPreQuiz}
          onAnswer={answerQuiz}
        />
      )}
      {screen === SCREENS.CALL && (
        <Call
          callerLine={callerLine}
          tactics={tactics}
          stage={stage}
          decisionCard={decisionCard}
          callEnded={callEnded}
          inputMasked={inputMasked}
          userInput={userInput}
          onUserInput={setUserInput}
          onSubmit={handleUserInput}
          onDecision={handleDecision}
          onHangUp={handleHangUp}
          loading={loading}
          error={error}
        />
      )}
      {screen === SCREENS.DEBRIEF && (
        <Debrief
          debrief={debrief}
          state={state}
          onGoDebrief={goDebrief}
          onShare={buildShare}
          onRestart={() => setScreen(SCREENS.HOME)}
        />
      )}
      {screen === SCREENS.SHARE && (
        <Share data={shareData} onBack={() => setScreen(SCREENS.DEBRIEF)} />
      )}
    </div>
  )
}