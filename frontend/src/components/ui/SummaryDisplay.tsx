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
    <div style={{ width: "100%", maxWidth: "680px", margin: "0 auto" }}>

      {/* Badges thème + ton */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "20px", flexWrap: "wrap" }}>
        {theme && (
          <span style={{
            padding: "4px 12px", borderRadius: "99px",
            fontSize: "0.8rem", fontWeight: 600,
            background: "#E3F2FD", color: "#0D3B7A",
            border: "1px solid #1565C0"
          }}>
            📋 {theme}
          </span>
        )}
        {tone && (
          <span style={{
            padding: "4px 12px", borderRadius: "99px",
            fontSize: "0.8rem", fontWeight: 600,
            background: "#F3E5F5", color: "#3D0D5C",
            border: "1px solid #6A1B9A"
          }}>
            🎯 {tone}
          </span>
        )}
        {processingMs != null && (
          <span style={{
            padding: "4px 12px", borderRadius: "99px",
            fontSize: "0.8rem",
            background: "#F4F6FB", color: "#6B7280",
            border: "1px solid #D1D5DB"
          }}>
            ⚡ Généré en {formatSeconds(processingMs)}
          </span>
        )}
      </div>

      {/* Résumé narratif */}
      <div style={{
        padding: "20px", borderRadius: "10px",
        background: "#F4F6FB", marginBottom: "20px",
        borderLeft: "4px solid #2C5F8A"
      }}>
        <h3 style={{ margin: "0 0 12px 0", fontSize: "0.95rem", color: "#2C5F8A" }}>
          Résumé
        </h3>
        <p style={{ margin: 0, lineHeight: "1.65", color: "#1C1C1C", fontSize: "0.9rem" }}>
          {content}
        </p>
      </div>

      {/* Décisions */}
      {decisions && decisions.length > 0 && (
        <div style={{
          padding: "20px", borderRadius: "10px",
          background: "#E8F5E9", marginBottom: "16px",
          borderLeft: "4px solid #2E7D32"
        }}>
          <h3 style={{ margin: "0 0 12px 0", fontSize: "0.95rem", color: "#1B5E20" }}>
            ✓ Décisions prises
          </h3>
          <ul style={{ margin: 0, paddingLeft: "20px" }}>
            {decisions.map((d, i) => (
              <li key={i} style={{
                fontSize: "0.9rem", color: "#1C1C1C",
                lineHeight: "1.6", marginBottom: "4px"
              }}>
                {d}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      {action_items && action_items.length > 0 && (
        <div style={{
          padding: "20px", borderRadius: "10px",
          background: "#FFF3E0",
          borderLeft: "4px solid #E65100"
        }}>
          <h3 style={{ margin: "0 0 12px 0", fontSize: "0.95rem", color: "#7A2D00" }}>
            → Actions à réaliser
          </h3>
          <ul style={{ margin: 0, paddingLeft: "20px" }}>
            {action_items.map((a, i) => (
              <li key={i} style={{
                fontSize: "0.9rem", color: "#1C1C1C",
                lineHeight: "1.6", marginBottom: "4px"
              }}>
                {a}
              </li>
            ))}
          </ul>
        </div>
      )}

    </div>
  );
}