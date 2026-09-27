import { CloudSun, Luggage, MapPin, Sparkles } from "lucide-react";

const SUGGESTIONS = [
  { text: "What's the weather?", Icon: CloudSun },
  { text: "What's the weather in Paris?", Icon: MapPin },
  { text: "Pack for 4 days in Rome", Icon: Luggage },
];

export function EmptyState({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="animate-rise flex flex-1 flex-col items-center justify-center gap-6 text-center">
      <p className="eyebrow flex items-center gap-2 text-xs"><Sparkles size={14} /> Try it</p>
      <h2 className="font-display text-3xl font-semibold">
        Watch <span className="bg-gradient-to-r from-accent to-accent-2 bg-clip-text text-transparent">System 1</span> decide
      </h2>
      <div className="flex flex-wrap justify-center gap-3">
        {SUGGESTIONS.map(({ text, Icon }) => (
          <button key={text} onClick={() => onPick(text)}
                  className="glass press flex items-center gap-2 rounded-full px-4 py-2 text-sm hover:-translate-y-0.5 hover:border-accent/60">
            <Icon size={15} className="text-accent" /> {text}
          </button>
        ))}
      </div>
    </div>
  );
}
