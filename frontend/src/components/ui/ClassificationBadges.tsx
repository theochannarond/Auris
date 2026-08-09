import Badge from "./Badge";

interface ClassificationBadgesProps {
  theme: string | null;
  tone:  string | null;
}

const TONE_LABELS: Record<string, string> = {
  formal:    "Formel",
  informal:  "Informel",
  technical: "Technique",
};

export default function ClassificationBadges({ theme, tone }: ClassificationBadgesProps) {
  if (!theme && !tone) return null;

  const toneLabel = tone ? TONE_LABELS[tone] ?? tone : null;

  return (
    <div className="flex gap-2 flex-wrap items-center">
      {theme && <Badge label={`📋 ${theme}`} variant="warning" />}
      {toneLabel && <Badge label={`🎯 ${toneLabel}`} variant="info" />}
    </div>
  );
}