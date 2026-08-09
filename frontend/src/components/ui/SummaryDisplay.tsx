import Badge from "./Badge";

interface SummaryDisplayProps {
  content:      string;
  decisions:    string[] | null;
  action_items: string[] | null;
  tone:         string | null;
  theme:        string | null;
  processingMs: number | null;
}

function formatSeconds(ms: number): string {
  return `${(ms / 1000).toFixed(1)} s`;
}

export default function SummaryDisplay({
  content,
  decisions,
  action_items,
  tone,
  theme,
  processingMs
}: SummaryDisplayProps) {
  return (
    <div className="w-full max-w-[680px] mx-auto">

      {/* Badges thème + ton */}
      <div className="flex gap-2 mb-5 flex-wrap">
        {theme && <Badge label={`📋 ${theme}`} variant="primary" />}
        {tone && <Badge label={`🎯 ${tone}`} variant="info" />}
        {processingMs != null && (
          <Badge label={`⚡ Généré en ${formatSeconds(processingMs)}`} variant="neutral" />
        )}
      </div>

      {/* Résumé narratif */}
      <div className="p-5 rounded-xl bg-[#F4F6FB] mb-5 border-l-4 border-[#2C5F8A]">
        <h3 className="text-sm text-[#2C5F8A] mb-3 font-medium">Résumé</h3>
        <p className="text-sm text-[#1C1C1C] leading-relaxed m-0">
          {content}
        </p>
      </div>

      {/* Décisions */}
      {decisions && decisions.length > 0 && (
        <div className="p-5 rounded-xl bg-[#E8F5E9] mb-4 border-l-4 border-[#2E7D32]">
          <h3 className="text-sm text-[#1B5E20] mb-3 font-medium">✓ Décisions prises</h3>
          <ul className="m-0 pl-5">
            {decisions.map((d, i) => (
              <li key={i} className="text-sm text-[#1C1C1C] leading-relaxed mb-1">
                {d}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      {action_items && action_items.length > 0 && (
        <div className="p-5 rounded-xl bg-[#FFF3E0] border-l-4 border-[#E65100]">
          <h3 className="text-sm text-[#7A2D00] mb-3 font-medium">→ Actions à réaliser</h3>
          <ul className="m-0 pl-5">
            {action_items.map((a, i) => (
              <li key={i} className="text-sm text-[#1C1C1C] leading-relaxed mb-1">
                {a}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}