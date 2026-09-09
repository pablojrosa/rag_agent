import React from 'react';
import './Message.css';

function ChartArtifact({ chart }) {
  const values = chart.data.map(item => Number(item.y)).filter(Number.isFinite);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 1);
  const range = max - min || 1;
  const points = chart.data.map((item, index) => {
    const x = 62 + (index * 270) / Math.max(chart.data.length - 1, 1);
    const y = 178 - ((Number(item.y) - min) / range) * 140;
    return { ...item, x, y };
  });
  if (chart.type === 'bar') {
    const width = 300;
    const rows = chart.data.map((item, index) => ({ item, value: Number(item.y), y: 45 + index * 42 }));
    return <svg className="chart-svg horizontal-bar-chart" viewBox={`0 0 470 ${Math.max(190, rows.length * 42 + 50)}`} role="img" aria-label={chart.title}>
      {[0, .25, .5, .75, 1].map((step, index) => { const x = 145 + step * width; const value = min + step * range; return <g key={index}><line x1={x} y1="25" x2={x} y2={rows.length * 42 + 25} className="chart-grid" /><text x={x} y={rows.length * 42 + 43} textAnchor="middle" className="chart-tick">{Number(value).toFixed(value % 1 ? 2 : 0)}</text></g>; })}
      {rows.map(({ item, value, y }, index) => { const label = String(item.x); const lines = label.split(/\s+/); return <g key={index}><text x="138" y={y + 4} textAnchor="end" className="chart-label">{lines.slice(0, 2).map((line, lineIndex) => <tspan key={lineIndex} x="138" dy={lineIndex ? 11 : 0}>{line.slice(0, 22)}</tspan>)}</text><rect x="145" y={y - 12} width={Math.max(0, (value - min) / range * width)} height="24" rx="5" className="chart-bar" /></g>; })}
      <text x="295" y={rows.length * 42 + 63} textAnchor="middle" className="chart-axis-label">{chart.y_key || 'Value'}</text>
    </svg>;
  }
  if (chart.type === 'pie') {
    const total = values.reduce((sum, value) => sum + Math.max(value, 0), 0) || 1;
    let offset = 0;
    const slices = values.map((value, index) => {
      const start = offset; offset += (value / total) * Math.PI * 2;
      const end = offset; const large = end - start > Math.PI ? 1 : 0;
      const path = `M 110 100 L ${110 + 78 * Math.cos(start)} ${100 + 78 * Math.sin(start)} A 78 78 0 ${large} 1 ${110 + 78 * Math.cos(end)} ${100 + 78 * Math.sin(end)} Z`;
      return <path key={index} d={path} fill={['#2563eb', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444'][index % 5]} />;
    });
    return <svg className="chart-svg pie-chart" viewBox="0 0 220 200">{slices}</svg>;
  }
  const line = points.map(point => `${point.x},${point.y}`).join(' ');
  const tickValues = [0, .25, .5, .75, 1].map(step => min + range * step);
  return <svg className="chart-svg" viewBox="0 0 390 275" role="img" aria-label={chart.title}>
    {tickValues.map((value, index) => { const y = 178 - index * 35; return <g key={index}><line x1="48" y1={y} x2="350" y2={y} className="chart-grid" /><text x="40" y={y + 3} textAnchor="end" className="chart-tick">{Number(value).toFixed(value % 1 ? 2 : 0)}</text></g>; })}
    <line x1="48" y1="38" x2="48" y2="178" className="chart-axis" /><line x1="48" y1="178" x2="350" y2="178" className="chart-axis" />
    {points.map((point, index) => <rect key={index} x={point.x - 15} y={point.y} width="30" height={178 - point.y} rx="4" className="chart-bar" />)}
    {chart.type !== 'bar' ? <>
      <polyline points={line} className="chart-line" />
      {chart.type === 'scatter' || chart.type === 'line' ? points.map((point, index) => <circle key={index} cx={point.x} cy={point.y} r="4" className="chart-dot" />) : null}
    </> : null}
    {points.map((point, index) => { const words = String(chart.data[index].x).split(/\s+/); const lines = []; for (let i = 0; i < words.length; i += 2) lines.push(words.slice(i, i + 2).join(' ')); return <text key={index} x={point.x} y="202" textAnchor="middle" className="chart-label">{lines.slice(0, 2).map((line, lineIndex) => <tspan key={lineIndex} x={point.x} dy={lineIndex ? 12 : 0}>{line.slice(0, 20)}</tspan>)}</text>; })}
    <text x="198" y="258" textAnchor="middle" className="chart-axis-label">{chart.x_key || 'X'}</text><text x="12" y="110" textAnchor="middle" transform="rotate(-90 12 110)" className="chart-axis-label">{chart.y_key || 'Y'}</text>
  </svg>;
}

function Artifact({ artifact }) {
  if (artifact?.type !== 'bar' && artifact?.type !== 'line' && artifact?.type !== 'scatter' && artifact?.type !== 'pie') return null;
  return <div className="chart-artifact"><div className="chart-heading"><strong>{artifact.title}</strong><span>{artifact.type}</span></div><ChartArtifact chart={artifact} /></div>;
}

const Message = ({ sender, text, timestamp, artifacts = [] }) => {
  const messageClass = sender === 'user' ? 'user-message' : 'bot-message';

  return (
    <div className={`message-container ${messageClass}`}>
      <div className="message-content"><div className="message-bubble"><p className="message-text">{text}</p><span className="message-timestamp">{timestamp}</span></div>{sender !== 'user' && artifacts.map((artifact, index) => <div className="chart-bubble" key={index}><Artifact artifact={artifact} /></div>)}</div>
    </div>
  );
};


export default Message;
