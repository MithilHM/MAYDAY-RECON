export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between text-sm">
        <h1 className="text-4xl font-bold mb-4">MAYDAY RECON</h1>
        <p className="text-lg text-gray-400 mb-8">
          Reconnaissance and Analysis Platform
        </p>
        <div className="flex gap-4">
          <a
            href="/api/v1/health"
            className="rounded-lg bg-white/10 px-6 py-3 font-semibold transition hover:bg-white/20"
          >
            API Health Check
          </a>
        </div>
      </div>
    </main>
  );
}
