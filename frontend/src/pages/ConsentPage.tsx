import { useState } from "react";
import Button from "../components/ui/Button";

interface ConsentPageProps {
  onConsent: () => void;
}

export default function ConsentPage({ onConsent }: ConsentPageProps) {
  const [checked, setChecked] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  const handleConsent = async () => {
    if (!checked) return;
    setLoading(true);
    setError("");
    try {
      await fetch("/api/v1/consents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ given_at: new Date().toISOString() }),
      });
      onConsent();
    } catch {
      setError("Une erreur est survenue. Veuillez réessayer.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen font-sans px-6 py-8 max-w-[600px] mx-auto">
      <h1 className="text-3xl mb-2">Auris</h1>
      <h2 className="text-xl text-gray-500 mb-8 text-center">
        Consentement RGPD
      </h2>

      <div className="bg-[#F4F6FB] rounded-xl p-6 mb-8 w-full">
        <p className="mb-4 leading-relaxed">
          En utilisant Auris, vous acceptez que vos données audio soient
          traitées pour générer un compte-rendu de réunion.
        </p>
        <ul className="pl-5 space-y-2 leading-relaxed list-disc">
          <li>Vos données restent hébergées en Union Européenne</li>
          <li>Elles ne sont jamais utilisées pour réentraîner des modèles</li>
          <li>Vous pouvez demander leur suppression à tout moment</li>
          <li>Rétention maximale : 12 mois</li>
        </ul>
      </div>

      <label className="flex items-center gap-3 mb-6 cursor-pointer min-h-[44px] w-full">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => setChecked(e.target.checked)}
          className="w-[18px] h-[18px] flex-shrink-0"
        />
        <span>
          J'ai lu et j'accepte les conditions de traitement de mes données
        </span>
      </label>

      {error && (
        <p className="text-[#B91C1C] text-sm mb-4">{error}</p>
      )}

      <Button
        onClick={handleConsent}
        disabled={!checked || loading}
        loading={loading}
        fullWidth
      >
        {loading ? "Enregistrement..." : "Confirmer mon consentement"}
      </Button>

      <p className="mt-4 text-xs text-gray-400 text-center">
        Conformément au RGPD Art. 7 et Art. 9 — Données hébergées EU
      </p>
    </div>
  );
}