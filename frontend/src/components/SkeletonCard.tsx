export default function SkeletonCard() {
  return (
    <>
      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
      `}</style>
      <div style={{
        height: "80px", borderRadius: "8px",
        backgroundColor: "#E5E7EB",
        animation: "pulse 1.5s ease-in-out infinite",
        marginBottom: "12px"
      }} />
    </>
  );
}