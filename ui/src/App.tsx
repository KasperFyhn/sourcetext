import { useEffect, useState } from 'react'

interface PingResponse {
  message: string
  documentCount: number
}

function App() {
  const [ping, setPing] = useState<PingResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/ping')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json() as Promise<PingResponse>
      })
      .then(setPing)
      .catch((err: Error) => setError(err.message))
  }, [])

  return (
    <main>
      <h1>sourcetext</h1>
      {error && <p>Backend call failed: {error}</p>}
      {!error && !ping && <p>Calling backend...</p>}
      {ping && (
        <p>
          {ping.message} Documents in DB: {ping.documentCount}
        </p>
      )}
    </main>
  )
}

export default App
