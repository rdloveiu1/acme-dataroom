import { useCallback, useEffect, useState } from 'react'
import { CloudDownload } from 'lucide-react'
import { Toaster, toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { ConnectDriveButton } from '@/components/ConnectDriveButton'
import { FileTable } from '@/components/FileTable'
import { ImportDriveDialog } from '@/components/ImportDriveDialog'
import { UploadButton } from '@/components/UploadButton'
import { api, type DataroomFile } from '@/lib/api'

function App() {
  const [files, setFiles] = useState<DataroomFile[]>([])
  const [filesLoading, setFilesLoading] = useState(true)
  const [driveConnected, setDriveConnected] = useState(false)
  const [importOpen, setImportOpen] = useState(false)

  const refreshFiles = useCallback(() => {
    setFilesLoading(true)
    api
      .listFiles()
      .then(setFiles)
      .catch(() => toast.error('Could not load files'))
      .finally(() => setFilesLoading(false))
  }, [])

  const refreshDriveStatus = useCallback(() => {
    api
      .driveStatus()
      .then((res) => setDriveConnected(res.connected))
      .catch(() => setDriveConnected(false))
  }, [])

  useEffect(() => {
    refreshFiles()
    refreshDriveStatus()

    const params = new URLSearchParams(window.location.search)
    if (params.get('drive_connected') === 'true') {
      toast.success('Google Drive connected')
    } else if (params.get('drive_error')) {
      toast.error('Could not connect Google Drive. Please try again.')
    }
    if (params.has('drive_connected') || params.has('drive_error')) {
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [refreshFiles, refreshDriveStatus])

  function handleNeedsReconnect() {
    setDriveConnected(false)
    toast.error('Your Google Drive connection expired. Please reconnect.')
  }

  return (
    <div className="mx-auto min-h-svh max-w-5xl px-6 py-10">
      <Toaster richColors position="top-right" />

      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Acme Data Room</h1>
          <p className="text-sm text-muted-foreground">
            Due-diligence document repository
          </p>
        </div>
        <div className="flex items-center gap-2">
          <ConnectDriveButton connected={driveConnected} />
          {driveConnected && (
            <Button variant="outline" onClick={() => setImportOpen(true)}>
              <CloudDownload className="size-4" />
              Import from Drive
            </Button>
          )}
          <UploadButton onUploaded={refreshFiles} />
        </div>
      </header>

      <FileTable files={files} loading={filesLoading} onDeleted={refreshFiles} />

      <ImportDriveDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        onImported={refreshFiles}
        onNeedsReconnect={handleNeedsReconnect}
      />
    </div>
  )
}

export default App
