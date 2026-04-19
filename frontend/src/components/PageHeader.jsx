// Заголовок страницы в стиле брендбука FITSIZ:
//   зелёная pill-метка («шрифт», «цвет») + БОЛЬШОЙ Russo One заголовок.
// Справа — слот для кнопок действий.
//
// accent: часть заголовка можно выделить зелёным цветом, как «заГОЛОВОКИ» из брендбука.
// Пример:  <PageHeader chip="обзор" title="Обзор" accent="зор" />  →  "Обзор" → «ОБ» белым, «ЗОР» зелёным.

export function PageHeader({ chip, title, accent, description, actions }) {
  // Разбиваем title на белую часть + зелёный accent (если передан)
  let beforeAccent = title
  let accentPart = ''
  if (accent && title?.toUpperCase().includes(accent.toUpperCase())) {
    const upper = title.toUpperCase()
    const upperAccent = accent.toUpperCase()
    const idx = upper.indexOf(upperAccent)
    beforeAccent = title.slice(0, idx)
    accentPart = title.slice(idx, idx + accent.length)
  }

  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-6">
      <div>
        {chip ? (
          <div className="mb-4">
            <span className="page-chip">{chip}</span>
          </div>
        ) : null}
        <h1 className="page-title">
          {beforeAccent}
          {accentPart ? (
            <span className="text-fitsiz-green">{accentPart}</span>
          ) : null}
        </h1>
        {description ? (
          <p className="mt-3 max-w-xl text-[15px] text-fitsiz-muted-light">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex flex-wrap gap-2">{actions}</div>
      ) : null}
    </div>
  )
}
