import SourceCard from './SourceCard.jsx'

export default function SourceList({ sources }) {
  if (!sources || sources.length === 0) return null

  return (
    <div className="source-list">
      <div className="source-list__row">
        {sources.slice(0, 3).map((source, i) => (
          <SourceCard key={i} source={source} />
        ))}
      </div>
    </div>
  )
}
