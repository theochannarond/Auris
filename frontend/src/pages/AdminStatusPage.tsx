import { Link } from "react-router-dom";
import { useServiceStatus } from "../hooks/useServiceStatus";
import type { ServiceStatus } from "../hooks/useServiceStatus";
import SkeletonCard from "../components/SkeletonCard";

function formatCheckedAt(iso: string): string {
  return new Date(iso).toLocaleTimeString("fr-FR", {
    hour:   "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function ServiceRow({ service }: { service: ServiceStatus }) {
  const isUp = service.status === "up";

  return (
    <div className="flex items-start gap-3 px-4 py-3 rounded-xl bg-white border border-gray-200">
      {/* Le point coloré est doublé d'un libellé texte : la couleur seule
          exclurait les daltoniens, qui sont ~8 % des hommes. */}
      <span
        className={`mt-1.5 w-2.5 h-2.5 rounded-full shrink-0 ${isUp ? "bg-[#059669]" : "bg-[#B91C1C]"}`}
        aria-hidden="true"
      />

      <div className="flex-1 min-w-0">
        <div className="flex items-baseline justify-between gap-3">
          <span className="font-medium text-gray-800">{service.label}</span>
          <span className={`text-sm shrink-0 ${isUp ? "text-[#059669]" : "text-[#B91C1C]"}`}>
            {isUp ? "Disponible" : "Indisponible"}
          </span>
        </div>

        <p className="text-xs text-gray-500 mt-0.5">
          {service.name} · {service.latency_ms} ms
        </p>

        {service.error && (
          <p className="text-xs text-[#7F1D1D] mt-1.5 break-words">
            {service.error}
          </p>
        )}
      </div>
    </div>
  );
}

export default function AdminStatusPage() {
  const { report, loading, error, refresh } = useServiceStatus();

  const degraded = report?.overall === "degraded";
  const downCount = report?.services.filter(s => s.status === "down").length ?? 0;

  return (
    <div className="font-sans max-w-[760px] mx-auto px-6 py-12">
      <Link to="/dashboard" className="text-[#2C5F8A] text-sm no-underline">
        ← Retour au dashboard
      </Link>

      <h1 className="text-3xl mt-8 mb-2">Auris</h1>
      <h2 className="text-lg text-gray-500 mb-6 font-normal">
        État des services
      </h2>

      {loading && (
        <div>
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {error && (
        <div className="px-4 py-3 mb-5 rounded-xl bg-[#FEF2F2] border border-[#FECACA] text-[#7F1D1D] text-sm">
          {error}
        </div>
      )}

      {report && (
        <>
          <div
            className={`px-4 py-3 mb-5 rounded-xl border text-sm ${
              degraded
                ? "bg-[#FEF2F2] border-[#FECACA] text-[#7F1D1D]"
                : "bg-[#ECFDF5] border-[#A7F3D0] text-[#065F46]"
            }`}
          >
            <p className="font-medium">
              {degraded
                ? `${downCount} service${downCount > 1 ? "s" : ""} indisponible${downCount > 1 ? "s" : ""}`
                : "Tous les services sont disponibles"}
            </p>
            <p className="mt-0.5 text-xs">
              Dernier contrôle à {formatCheckedAt(report.checked_at)} · actualisation automatique toutes les 30 secondes
            </p>
          </div>

          <div className="flex flex-col gap-3">
            {report.services.map(service => (
              <ServiceRow key={service.name} service={service} />
            ))}
          </div>

          <button
            onClick={refresh}
            className="mt-6 px-4 py-2 rounded-lg border border-[#2C5F8A] text-[#2C5F8A] text-sm"
          >
            Actualiser maintenant
          </button>

          {/* Précision honnête plutôt qu'un voyant vert trompeur : cette page
              transite par nginx, donc s'il était réellement tombé elle ne se
              serait pas affichée. La surveillance côté serveur, elle, le
              contrôle depuis l'extérieur toutes les 5 minutes. */}
          <p className="mt-6 text-xs text-gray-500">
            Ces sondes sont émises depuis l'API. L'état du proxy nginx est donc
            indicatif : cette page ne peut pas s'afficher s'il est arrêté. La
            surveillance de fond et les alertes email s'exécutent sur le serveur,
            indépendamment du navigateur.
          </p>
        </>
      )}
    </div>
  );
}
