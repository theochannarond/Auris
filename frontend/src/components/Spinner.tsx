export default function Spinner({ size = 24 }: { size?: number }) {
  return (
    <>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
      <div
        style={{
          width: size, height: size,
          border: "3px solid #E5E7EB",
          borderTopColor: "#2C5F8A",
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite"
        }}
      />
    </>
  );
}