import { useState } from 'react';
import { aiApi } from '../../api';
import { errorMessage } from '../../api/client';
import ErrorMessage from '../../components/ErrorMessage';
import Loader from '../../components/Loader';

const EXAMPLES = [
  'Summarize my last five orders.',
  'Which of my orders are still not delivered?',
  'How much did I spend this week?',
  'Which food items have I ordered most frequently?',
];

export default function AIInsights() {
  const [question, setQuestion] = useState('');
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const ask = async (q) => {
    setLoading(true);
    setError('');
    try {
      const res = await aiApi.insights(q);
      setHistory((h) => [{ q: q || 'Summarize my order history', ...res }, ...h]);
      setQuestion('');
    } catch (e) {
      setError(errorMessage(e, 'AI request failed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container page narrow">
      <h1>✨ AI order insights</h1>
      <p className="muted">Ask anything about your own order history. Only your orders are shared with the AI.</p>
      <div className="card card-body">
        <form className="ask-form" onSubmit={(e) => { e.preventDefault(); ask(question.trim()); }}>
          <input placeholder="e.g. How much did I spend this month?" value={question} maxLength={500}
            onChange={(e) => setQuestion(e.target.value)} />
          <button className="btn" disabled={loading || !question.trim()}>Ask</button>
          <button type="button" className="btn btn-ghost" disabled={loading} onClick={() => ask('')}>Summarize</button>
        </form>
        <div className="chips">
          {EXAMPLES.map((ex) => (
            <button key={ex} className="chip" disabled={loading} onClick={() => ask(ex)}>{ex}</button>
          ))}
        </div>
      </div>
      <ErrorMessage message={error} />
      {loading && <Loader text="Thinking…" />}
      {history.map((h, i) => (
        <div key={i} className="card card-body insight">
          <p className="muted small">Q: {h.q}</p>
          <div className="insight-answer">{h.answer}</div>
          <p className="muted small">Based on {h.orders_considered} order(s) · {h.model}</p>
        </div>
      ))}
    </div>
  );
}
