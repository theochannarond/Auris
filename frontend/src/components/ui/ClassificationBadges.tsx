interface ClassificationBadgesProps {
  theme: string | null;
  tone:  string | null;
}

const TONE_CONFIG: Record<string, { label: string; bg: string; color: string; border: string }> = {
  formal:    { label: "Formel",     bg: "#E3F2FD", color: "#0D3B7A", border: "#1565C0" },
  informal:  { label: "Informel",   bg: "#E8F5E9", color: "#1B4D1E", border: "#2E7D32" },
  technical: { label: "Technique",  bg: "#F3E5F5", color: "#3D0D5C", border: "#6A1B9A" },
};

export default function ClassificationBadges({ theme, tone }: ClassificationBadgesProps) {
  if (!theme && !tone) return null;

  const toneConfig = tone ? TONE_CONFIG[tone] ?? TONE_CONFIG["formal"] : null;

  return (
    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
      {theme && (
        <span style={{
          padding:      "4px 12px",
          borderRadius: "99px",
          fontSize:     "0.8rem",
          fontWeight:   600,
          background:   "#FFF8E1",
          color:        "#7A4A00",
          border:       "1px solid #E65100"
        }}>
          📋 {theme}
        </span>
      )}
      {toneConfig && (
        <span style={{
          padding:      "4px 12px",
          borderRadius: "99px",
          fontSize:     "0.8rem",
          fontWeight:   600,
          background:   toneConfig.bg,
          color:        toneConfig.color,
          border:       `1px solid ${toneConfig.border}`
        }}>
          🎯 {toneConfig.label}
        </span>
      )}
    </div>
  );
}