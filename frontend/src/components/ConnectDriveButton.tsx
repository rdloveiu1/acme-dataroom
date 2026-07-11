import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'

export function ConnectDriveButton({ connected }: { connected: boolean }) {
  if (connected) return null

  return (
    <Button onClick={() => (window.location.href = api.driveConnectUrl())}>
      Connect Google Drive
    </Button>
  )
}
