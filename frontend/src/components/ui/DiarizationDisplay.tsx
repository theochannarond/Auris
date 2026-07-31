interface DiarizationSegment {
  speaker: string;
  start:   number;
  end:     number;
  text:    string;
}

interface DiarizationDisplayProps {
  segments: DiarizationSegment[];
}

// Palette de couleurs par locuteur
const SPEAKER_COLORS = [
  { bg: "#E3F2FD", border: "#1565C0", text: "#0D3B7A" },
  { bg: "#E8F5E9", border: "#2E7D32", text: "#1B4D1E" },
  { bg: "#FFF3E0", border: "#E65100", text: "#7A2D00" },
  { bg: "#F3E5F5", border: "#6A1B9A", text: "#3D0D5C" },
  { bg: "#FCE4EC", border: "#AD1457", text: "#6B0C35" },
  { bg: "#E0F7FA", border: "#00695C", text: "#003D35" },
];

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function DiarizationDisplay({ segments }: DiarizationDisplayProps) {
  if (!segments || segments.length === 0) return null;

  // Associe chaque locuteur unique à une couleur
  const speakerList = Array.from(new Set(segments.map(s => s.speaker)));
  const colorMap: Record<string, typeof SPEAKER_COLORS[0]> = {};
  speakerList.forEach((speaker, index) => {
    colorMap[speaker] = SPEAKER_COLORS[index % SPEAKER_COLORS.length];
  });

  return (
    <div style={{ width: "100%", maxWidth: "680px", margin: "0 auto" }}>

      {/* Légende des locuteurs */}
      <div style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "8px",
        marginBottom: "20px"
      }}>
        {speakerList.map(speaker => (
          <span
            key={speaker}
            style={{
              padding: "4px 12px",
              borderRadius: "99px",
              fontSize: "0.8rem",
              fontWeight: 600,
              background: colorMap[speaker].bg,
              color:      colorMap[speaker].text,
              border:     `1px solid ${colorMap[speaker].border}`
            }}
          >
            {speaker}
          </span>
        ))}
      </div>

      {/* Segments dans l'ordre chronologique */}
      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {segments.map((segment, index) => {
          const colors = colorMap[segment.speaker];
          return (
            <div
              key={index}
              style={{
                padding:      "12px 16px",
                borderRadius: "8px",
                background:   colors.bg,
                borderLeft:   `4px solid ${colors.border}`,
              }}
            >
              <div style={{
                display:        "flex",
                justifyContent: "space-between",
                alignItems:     "center",
                marginBottom:   "6px"
              }}>
                <span style={{
                  fontWeight: 600,
                  fontSize:   "0.85rem",
                  color:      colors.text
                }}>
                  {segment.speaker}
                </span>
                <span style={{
                  fontSize: "0.75rem",
                  color:    "#9CA3AF",
                  fontVariantNumeric: "tabular-nums"
                }}>
                  {formatTime(segment.start)} — {formatTime(segment.end)}
                </span>
              </div>
              <p style={{
                margin:     0,
                fontSize:   "0.9rem",
                color:      "#1C1C1C",
                lineHeight: "1.55"
              }}>
                {segment.text}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}