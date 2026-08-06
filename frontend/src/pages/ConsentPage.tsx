import { useState } from "react";

interface ConsentPageProps {
  onConsent: () => void;
}

export default function ConsentPage({ onConsent }: ConsentPageProps) {
  const [checked, setChecked] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleConsent = async () => {
    if (!checked) return;
    setLoading(true);
    try {
      await fetch("/api/v1/consents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          given_at: new Date().toISOString(),
        }),
      });
      onConsent();
    } catch (error) {
      console.error("Erreur consentement:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      height: "100vh",
      fontFamily: "Arial, sans-serif",
      padding: "0 24px",
      maxWidth: "600px",
      margin: "0 auto"
    }}>
      <h1 style={{ fontSize: "2rem", marginBottom: "8px" }}>Auris</h1>
      <h2 style={{ fontSize: "1.2rem", color: "#6B7280", marginBottom: "32px" }}>
        Consentement RGPD
      </h2>

      <div style={{
        background: "#F4F6FB",
        borderRadius: "12px",
        padding: "24px",
        marginBottom: "32px",
        width: "100%"
      }}>
        <p style={{ marginBottom: "16px", lineHeight: "1.6" }}>
          En utilisant Auris, vous acceptez que vos données audio soient
          traitées pour générer un compte-rendu de réunion.
        </p>
        <ul style={{ paddingLeft: "20px", lineHeight: "2" }}>
          <li>Vos données restent hébergées en Union Européenne</li>
          <li>Elles ne sont jamais utilisées pour réentraîner des modèles</li>
          <li>Vous pouvez demander leur suppression à tout moment</li>
          <li>Rétention maximale : 12 mois</li>
        </ul>
      </div>

      <label style={{
        display: "flex",
        alignItems: "center",
        gap: "12px",
        marginBottom: "24px",
        cursor: "pointer"
      }}>
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => setChecked(e.target.checked)}
          style={{ width: "18px", height: "18px" }}
        />
        <span>
          J'ai lu et j'accepte les conditions de traitement de mes données
        </span>
      </label>

      <button
        onClick={handleConsent}
        disabled={!checked || loading}
        style={{
          backgroundColor: checked ? "#2C5F8A" : "#9CA3AF",
          color: "white",
          border: "none",
          padding: "12px 48px",
          borderRadius: "8px",
          fontSize: "1rem",
          cursor: checked && !loading ? "pointer" : "not-allowed",
          transition: "background-color 0.2s"
        }}
      >
        {loading ? "Enregistrement..." : "Confirmer mon consentement"}
      </button>

      <p style={{ marginTop: "16px", fontSize: "0.75rem", color: "#9CA3AF" }}>
        Conformément au RGPD Art. 7 et Art. 9 — Données hébergées EU
      </p>
    </div>
  );
}