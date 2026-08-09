/**
 * Chapter line rules (from plan §4, §5):
 *   - Always: "Chapter {n}"
 *   - Append "— {chapter_title}" only when chapter_title !== "Chapter {n}"
 *   - Append "· p. {page_start}" or "· pp. {page_start}–{page_end}" when pages are present
 */
function buildChapterLine({ chapter_number, chapter_title, page_start, page_end }) {
  const base = `Chapter ${chapter_number}`

  let line = base
  if (chapter_title && chapter_title !== base) {
    line += ` — ${chapter_title}`
  }

  if (page_start) {
    if (page_end && page_end !== page_start) {
      line += ` · pp. ${page_start}–${page_end}`
    } else {
      line += ` · p. ${page_start}`
    }
  }

  return line
}

export default function SourceCard({ source }) {
  const {
    book_title,
    chapter_number,
    chapter_title,
    page_start,
    page_end,
    excerpt,
  } = source

  const chapterLine = buildChapterLine({ chapter_number, chapter_title, page_start, page_end })

  return (
    <div className="source-card">
      <span className="source-card__book-title">{book_title}</span>
      <span className="source-card__chapter">{chapterLine}</span>
      {excerpt && (
        <p className="source-card__excerpt">&ldquo;{excerpt}&rdquo;</p>
      )}
    </div>
  )
}
