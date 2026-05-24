interface Props {
  data: number[];           // oldest -> newest, length = 7
  className?: string;
}

export default function Sparkline({ data, className }: Props) {
  const max = Math.max(1, ...data);
  return (
    <div className={`sparkline ${className ?? ""}`} aria-label="Doc updates, last 7 days">
      {data.map((v, i) => {
        const isToday = i === data.length - 1;
        const heightPct = v === 0 ? 0 : Math.max(18, (v / max) * 100);
        return (
          <div
            key={i}
            className={`sparkline-bar ${v > 0 ? "has-value" : ""} ${isToday ? "today" : ""}`}
            style={{ height: `${heightPct}%` }}
            title={`${v} update${v === 1 ? "" : "s"}`}
          />
        );
      })}
    </div>
  );
}
