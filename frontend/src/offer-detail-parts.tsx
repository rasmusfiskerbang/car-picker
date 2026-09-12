import { type ReactNode } from "react";

export function SectionHeading({
  eyebrow,
  id,
  title,
}: {
  eyebrow: string;
  id: string;
  title: string;
}) {
  return (
    <header className="detail-section-heading">
      <p className="eyebrow">{eyebrow}</p>
      <h2 id={id}>{title}</h2>
    </header>
  );
}

export function FactRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="fact-row">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
