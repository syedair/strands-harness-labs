const SUGGESTIONS = ["What's the weather?", "What's the weather in Paris?", "Pack for 4 days in Istanbul"];

export function EmptyState({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 text-center">
      <p className="eyebrow text-xs">Try it</p>
      <h2 className="font-display text-3xl font-semibold">
        Watch <span className="bg-gradient-to-r from-accent to-accent-2 bg-clip-text text-transparent">System 1</span> decide
      </h2>
      <div className="flex flex-wrap justify-center gap-3">
        {SUGGESTIONS.map((s) => (
          <button key={s} onClick={() => onPick(s)} className="glass rounded-full px-4 py-2 text-sm hover:border-accent/60">{s}</button>
        ))}
      </div>
    </div>
  );
}
