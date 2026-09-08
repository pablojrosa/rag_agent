import { useEffect, useState } from 'react';
import { getEvaluationDashboard } from '../api/chatService';
import './TableStyles.css';
import './EvaluationDashboard.css';

function display(value) {
  if (value === null || value === undefined) return 'No score available';
  if (typeof value === 'number') return value.toFixed(2);
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return typeof value === 'string' ? value : JSON.stringify(value);
}

function Results({ data, title }) {
  return <section aria-label={title}>
    <h3>{title}</h3>
    <div className="metric-cards">
      {data.metrics.filter(metric => metric.type === 'NUMERIC').map(metric => {
        const values = data.rows.map(row => row.scores[metric.key]?.value)
          .filter(value => typeof value === 'number' && Number.isFinite(value));
        return <article key={metric.key} title={metric.description || ''}>
          <strong>{metric.label}</strong>
          <span>{values.length ? (values.reduce((a, b) => a + b, 0) / values.length).toFixed(2) : '—'}</span>
          <small>{values.length} scored items on this page</small>
        </article>;
      })}
    </div>
    {!data.rows.length ? <p>No results in the selected period.</p> : <div className="table-container">
      <table className="results-table">
        <thead><tr><th>Question</th><th>Answer</th>
          {data.metrics.map(metric => <th key={metric.key} title={metric.description || ''}>{metric.label}</th>)}
          <th>Duration</th><th>Status</th><th>Session / time</th><th>Trace</th>
        </tr></thead>
        <tbody>{data.rows.map(row => <tr key={row.id}>
          <td>{row.question}{row.expected_output && <details><summary>Reference answer</summary>{display(row.expected_output)}</details>}</td>
          <td>{display(row.answer)}</td>
          {data.metrics.map(metric => <td key={metric.key} title={row.scores[metric.key]?.comment || ''}>
            {display(row.scores[metric.key]?.value)}
            {row.scores[metric.key]?.comment && <details><summary>Reasoning</summary>{row.scores[metric.key].comment}</details>}
          </td>)}
          <td>{row.latency_seconds == null ? '—' : `${row.latency_seconds.toFixed(2)} s`}</td>
          <td>{row.status === 'unscored' ? 'No score available' : row.status}</td>
          <td>{row.session_id || '—'}<br />{new Date(row.timestamp).toLocaleString()}</td>
          <td>{row.trace_url ? <a href={row.trace_url} target="_blank" rel="noreferrer">Open trace</a> : '—'}</td>
        </tr>)}</tbody>
      </table>
    </div>}
  </section>;
}

export default function EvaluationDashboard({ mode }) {
  const [days, setDays] = useState('7');
  const [run, setRun] = useState('');
  const [compare, setCompare] = useState('');
  const [cursor, setCursor] = useState('');
  const [refresh, setRefresh] = useState(0);
  const [data, setData] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    Promise.all([
      getEvaluationDashboard(mode, { days, experiment_id: run, cursor }, controller.signal),
      compare ? getEvaluationDashboard(mode, { days, experiment_id: compare }, controller.signal) : Promise.resolve(null),
    ]).then(([primary, secondary]) => {
      setData(primary);
      setComparison(secondary);
    }).catch(err => {
      if (err.name !== 'AbortError') setError(err.message);
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [mode, days, run, compare, cursor, refresh]);

  return <div className="page-container">
    <h2>{mode === 'online' ? 'Conversation quality' : 'Evaluation experiments'}</h2>
    <p>Scores and metric definitions come from Langfuse. Evaluations arrive asynchronously; missing scores are not zero.</p>
    <div className="evaluation-controls">
      <label>Period <select value={days} onChange={event => { setDays(event.target.value); setCursor(''); setRun(''); setCompare(''); }}>
        <option value="1">Last day</option><option value="7">Last 7 days</option>
        <option value="30">Last 30 days</option><option value="90">Last 90 days</option>
      </select></label>
      {mode === 'offline' && data?.runs?.length > 0 && <>
        <label>Experiment <select value={run || data.experiment_id || ''} onChange={event => { setRun(event.target.value); setCursor(''); }}>
          {data.runs.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select></label>
        <label>Compare with <select value={compare} onChange={event => setCompare(event.target.value)}>
          <option value="">None</option>{data.runs.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select></label>
      </>}
      <button disabled={loading} onClick={() => setRefresh(value => value + 1)}>Refresh</button>
    </div>
    {loading ? <p role="status">Loading evaluations…</p> : error ? <p role="alert">{error}</p> : data && <>
      {!data.configured ? <p role="status">Monitoring is not configured. Connect Langfuse to view evaluations.</p> : <>
        {!data.metrics.length && <p>No visible metric definitions found in Langfuse.</p>}
        {mode === 'online' && data.performance?.length > 0 && <section>
          <h3>Performance across the selected period</h3>
          <div className="table-container"><table className="results-table">
            <thead><tr><th>Operation</th><th>Count</th><th>Average duration</th><th>Tokens</th><th>Cost (USD)</th></tr></thead>
            <tbody>{data.performance.map(item => <tr key={item.name}>
              <td>{item.name}</td><td>{item.count_count ?? '—'}</td>
              <td>{item.avg_latency == null ? '—' : `${(Number(item.avg_latency) / 1000).toFixed(2)} s`}</td>
              <td>{item.sum_totalTokens ?? '—'}</td>
              <td>{item.sum_totalCost == null ? '—' : Number(item.sum_totalCost).toFixed(6)}</td>
            </tr>)}</tbody>
          </table></div>
          <p>Tokens and costs belong to individual model operations; parent spans are not additional model calls.</p>
        </section>}
        <Results data={data} title={mode === 'offline' ? (data.runs.find(item => item.id === data.experiment_id)?.name || 'Experiment results') : 'Recent answers'} />
        <div className="evaluation-controls">
          {cursor && <button onClick={() => setCursor('')}>First page</button>}
          {data.next_cursor && <button onClick={() => setCursor(data.next_cursor)}>Next page</button>}
        </div>
        {comparison && <Results data={comparison} title="Comparison — first page" />}
        <p className="evaluation-note">Averages describe the displayed page, not the entire period or experiment. Hover over metric names for definitions.</p>
      </>}
    </>}
  </div>;
}
