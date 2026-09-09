import { useEffect, useMemo, useState } from 'react';
import { getEvaluationDashboard } from '../api/chatService';
import './EvaluationDashboard.css';

function display(value) {
  if (value === null || value === undefined || value === '') return 'Not available';
  if (typeof value === 'number') return value.toFixed(2);
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return typeof value === 'string' ? value : JSON.stringify(value);
}

function formatDate(value) {
  if (!value) return 'Not available';
  return new Date(value).toLocaleString();
}

function scoreClass(value) {
  if (typeof value !== 'number') return 'score-empty';
  if (value >= 0.8) return 'score-good';
  if (value >= 0.5) return 'score-mid';
  return 'score-low';
}

function statusLabel(status) {
  if (status === 'unscored') return 'Pending';
  if (status === 'evaluated') return 'Evaluated';
  if (status === 'error') return 'Error';
  return status || 'Unknown';
}

function metricAverage(rows, metric) {
  const values = rows
    .map(row => row.scores[metric.key]?.value)
    .filter(value => typeof value === 'number' && Number.isFinite(value));
  if (!values.length) return { value: null, count: 0 };
  return {
    value: values.reduce((total, value) => total + value, 0) / values.length,
    count: values.length,
  };
}

function SummaryCards({ data }) {
  const metrics = data.metrics.filter(metric => metric.type === 'NUMERIC');
  const evaluated = data.rows.filter(row => row.status === 'evaluated').length;
  const pending = data.rows.filter(row => row.status === 'unscored').length;

  return <div className="evaluation-summary">
    <article className="summary-card">
      <span className="summary-label">Rows</span>
      <strong>{data.rows.length}</strong>
      <small>{evaluated} evaluated, {pending} pending</small>
    </article>
    {metrics.map(metric => {
      const average = metricAverage(data.rows, metric);
      return <article className="summary-card" key={metric.key} title={metric.description || ''}>
        <span className="summary-label">{metric.label}</span>
        <strong className={scoreClass(average.value)}>{average.value == null ? '-' : average.value.toFixed(2)}</strong>
        <small>{average.count} scored on this page</small>
      </article>;
    })}
  </div>;
}

function PerformancePanel({ performance }) {
  if (!performance?.length) return null;
  return <section className="dashboard-panel">
    <div className="section-heading">
      <div>
        <h3>Performance</h3>
        <p>Aggregated model operations for the selected period.</p>
      </div>
    </div>
    <div className="performance-grid">
      {performance.map(item => <article className="performance-card" key={item.name}>
        <strong>{item.name}</strong>
        <dl>
          <div><dt>Count</dt><dd>{item.count_count ?? '-'}</dd></div>
          <div><dt>Avg duration</dt><dd>{item.avg_latency == null ? '-' : `${(Number(item.avg_latency) / 1000).toFixed(2)} s`}</dd></div>
          <div><dt>Tokens</dt><dd>{item.sum_totalTokens ?? '-'}</dd></div>
          <div><dt>Cost</dt><dd>{item.sum_totalCost == null ? '-' : `$${Number(item.sum_totalCost).toFixed(6)}`}</dd></div>
        </dl>
      </article>)}
    </div>
  </section>;
}

function ScoreCell({ score }) {
  const value = score?.value;
  return <div className="score-cell">
    <span className={`score-pill ${scoreClass(value)}`}>{display(value)}</span>
    {score?.comment && <details>
      <summary>Reasoning</summary>
      <p>{score.comment}</p>
    </details>}
    {!score && <small>Awaiting Langfuse</small>}
  </div>;
}

function Results({ data, title }) {
  return <section className="dashboard-panel" aria-label={title}>
    <div className="section-heading">
      <div>
        <h3>{title}</h3>
        <p>Averages use the rows currently displayed on this page.</p>
      </div>
    </div>
    <SummaryCards data={data} />
    {!data.rows.length ? <div className="empty-state">No results in the selected period.</div> : <div className="evaluation-table-wrap">
      <table className="evaluation-table">
        <thead>
          <tr>
            <th>Question and answer</th>
            {data.metrics.map(metric => <th key={metric.key} title={metric.description || ''}>{metric.label}</th>)}
            <th>Run data</th>
            <th>Trace</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map(row => <tr key={row.id}>
            <td className="qa-cell">
              <strong>{display(row.question)}</strong>
              <p>{display(row.answer)}</p>
              {row.expected_output && <details>
                <summary>Reference answer</summary>
                <p>{display(row.expected_output)}</p>
              </details>}
            </td>
            {data.metrics.map(metric => <td key={metric.key}>
              <ScoreCell score={row.scores[metric.key]} />
            </td>)}
            <td className="run-cell">
              <span className={`status-badge status-${row.status || 'unknown'}`}>{statusLabel(row.status)}</span>
              <dl>
                <div><dt>Duration</dt><dd>{row.latency_seconds == null ? '-' : `${row.latency_seconds.toFixed(2)} s`}</dd></div>
                <div><dt>Session</dt><dd>{row.session_id || '-'}</dd></div>
                <div><dt>Time</dt><dd>{formatDate(row.timestamp)}</dd></div>
              </dl>
            </td>
            <td className="trace-cell">{row.trace_url ? <a href={row.trace_url} target="_blank" rel="noreferrer">Open</a> : '-'}</td>
          </tr>)}
        </tbody>
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

  const selectedRunName = useMemo(() => {
    if (mode !== 'offline' || !data?.runs?.length) return null;
    return data.runs.find(item => item.id === data.experiment_id)?.name || 'Experiment results';
  }, [data, mode]);

  return <main className="evaluation-page">
    <header className="evaluation-hero">
      <div>
        <span className="eyebrow">{mode === 'online' ? 'Online monitoring' : 'Offline evaluation'}</span>
        <h2>{mode === 'online' ? 'Conversation quality' : 'Evaluation experiments'}</h2>
        <p>Scores, definitions, traces, and experiment runs are read from Langfuse.</p>
      </div>
      <button className="primary-action" disabled={loading} onClick={() => setRefresh(value => value + 1)}>
        {loading ? 'Refreshing' : 'Refresh'}
      </button>
    </header>

    <section className="toolbar" aria-label="Dashboard controls">
      <label>Period
        <select value={days} onChange={event => { setDays(event.target.value); setCursor(''); setRun(''); setCompare(''); }}>
          <option value="1">Last day</option>
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
          <option value="90">Last 90 days</option>
        </select>
      </label>
      {mode === 'offline' && data?.runs?.length > 0 && <>
        <label>Experiment
          <select value={run || data.experiment_id || ''} onChange={event => { setRun(event.target.value); setCursor(''); }}>
            {data.runs.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </label>
        <label>Compare
          <select value={compare} onChange={event => setCompare(event.target.value)}>
            <option value="">None</option>
            {data.runs.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </label>
      </>}
    </section>

    {loading ? <div className="state-panel" role="status">Loading evaluations...</div> : error ? <div className="state-panel error" role="alert">{error}</div> : data && <>
      {!data.configured ? <div className="state-panel">Connect Langfuse to view evaluations.</div> : <>
        {!data.metrics.length && <div className="state-panel">No visible metric definitions found in Langfuse.</div>}
        {mode === 'online' && <PerformancePanel performance={data.performance} />}
        <Results data={data} title={mode === 'offline' ? selectedRunName : 'Recent answers'} />
        <nav className="pagination-controls" aria-label="Pagination">
          {cursor && <button onClick={() => setCursor('')}>First page</button>}
          {data.next_cursor && <button onClick={() => setCursor(data.next_cursor)}>Next page</button>}
        </nav>
        {comparison && <Results data={comparison} title="Comparison first page" />}
      </>}
    </>}
  </main>;
}
