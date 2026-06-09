interface Props {
  text: string;
  keywords: string[];
}

export default function DiffHighlight({ text, keywords }: Props) {
  if (!keywords.length) return <pre className="whitespace-pre-wrap text-sm text-slate-300 leading-7">{text}</pre>;

  const escaped = keywords.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const regex = new RegExp(`(${escaped.join("|")})`, "gi");
  const parts = text.split(regex);

  return (
    <pre className="whitespace-pre-wrap text-sm text-slate-300 leading-7">
      {parts.map((part, i) =>
        keywords.some((k) => k.toLowerCase() === part.toLowerCase()) ? (
          <mark key={i} className="diff-add">{part}</mark>
        ) : (
          part
        )
      )}
    </pre>
  );
}
