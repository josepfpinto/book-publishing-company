const SEGMENTS = [
  { id: 'little_women',    label: 'Little Women' },
  { id: 'both',            label: 'Both Books' },
  { id: 'pride_prejudice', label: 'Pride & Prejudice' },
]

function BookGlyph() {
  return (
    <svg
      className="book-toggle__icon"
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      aria-hidden="true"
    >
      {/* open-book glyph — two pages with a spine crease */}
      <path
        d="M7 3.5C5.5 2.5 3 2 1 2.5V11c2-.5 4 0 6 1.5"
        stroke="currentColor"
        strokeWidth="1.1"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <path
        d="M7 3.5C8.5 2.5 11 2 13 2.5V11c-2-.5-4 0-6 1.5"
        stroke="currentColor"
        strokeWidth="1.1"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <line
        x1="7" y1="3.5" x2="7" y2="13"
        stroke="currentColor"
        strokeWidth="1.1"
        strokeLinecap="round"
      />
    </svg>
  )
}

export default function BookToggle({ selected, onSelect }) {
  return (
    <div className="book-toggle" role="group" aria-label="Book selection">
      {SEGMENTS.map(({ id, label }) => (
        <button
          key={id}
          className={`book-toggle__segment${selected === id ? ' book-toggle__segment--active' : ''}`}
          onClick={() => onSelect(id)}
          aria-pressed={selected === id}
        >
          <BookGlyph />
          {label}
        </button>
      ))}
    </div>
  )
}
