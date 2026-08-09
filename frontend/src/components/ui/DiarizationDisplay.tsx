interface DiarizationSegment {
  speaker: string;
  start:   number;
  end:     number;
  text:    string;
}

interface DiarizationDisplayProps {
  segments: DiarizationSegment[];
}

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

  const speakerList = Array.from(new Set(segments.map(s => s.speaker)));
  const colorMap: Record<string, typeof SPEAKER_COLORS[0]> = {};
  speakerList.forEach((speaker, index) => {
    colorMap[speaker] = SPEAKER_COLORS[index % SPEAKER_COLORS.length];
  });

  return (
    <div className="w-full max-w-[680px] mx-auto">

      {/* Légende */}
      <div className="flex flex-wrap gap-2 mb-5">
        {speakerList.map(speaker => (
          <span
            key={speaker}
            className="px-3 py-1 rounded-full text-xs font-semibold border"
            style={{
              background: colorMap[speaker].bg,
              color:      colorMap[speaker].text,
              borderColor: colorMap[speaker].border
            }}
          >
            {speaker}
          </span>
        ))}
      </div>

      {/* Segments */}
      <div className="flex flex-col gap-2.5">
        {segments.map((segment, index) => {
          const colors = colorMap[segment.speaker];
          return (
            <div
              key={index}
              className="px-4 py-3 rounded-lg"
              style={{
                background:  colors.bg,
                borderLeft:  `4px solid ${colors.border}`
              }}
            >
              <div className="flex justify-between items-center mb-1.5">
                <span
                  className="font-semibold text-sm"
                  style={{ color: colors.text }}
                >
                  {segment.speaker}
                </span>
                <span className="text-xs text-gray-400 tabular-nums">
                  {formatTime(segment.start)} — {formatTime(segment.end)}
                </span>
              </div>
              <p className="m-0 text-sm text-[#1C1C1C] leading-snug">
                {segment.text}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}