import { useCallback, useEffect, useState } from 'react'
import { CloudDownload, LogOut, Loader2 } from 'lucide-react'
import { Toaster, toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { AuthScreen } from '@/components/AuthScreen'
import { ConnectDriveButton } from '@/components/ConnectDriveButton'
import { FileTable } from '@/components/FileTable'
import { ImportDriveDialog } from '@/components/ImportDriveDialog'
import { SearchInput } from '@/components/SearchInput'
import { UploadButton } from '@/components/UploadButton'
import { api, AuthRequiredError, type DataroomFile } from '@/lib/api'
import { useAuth } from '@/lib/AuthContext'

function DataRoom() {
  const { user, logout, invalidate } = useAuth()
  const [files, setFiles] = useState<DataroomFile[]>([])
  const [filesLoading, setFilesLoading] = useState(true)
  const [driveConnected, setDriveConnected] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [search, setSearch] = useState('')

  const refreshFiles = useCallback(
    (query?: string) => {
      setFilesLoading(true)
      api
        .listFiles(query)
        .then(setFiles)
        .catch((err) => {
          if (err instanceof AuthRequiredError) {
            invalidate()
            return
          }
          toast.error('Could not load files')
        })
        .finally(() => setFilesLoading(false))
    },
    [invalidate],
  )

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

  // Debounce search-as-you-type instead of hitting the API on every keystroke.
  useEffect(() => {
    const timeout = setTimeout(() => refreshFiles(search), 300)
    return () => clearTimeout(timeout)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search])

  function handleNeedsReconnect() {
    setDriveConnected(false)
    toast.error('Your Google Drive connection expired. Please reconnect.')
  }

  return (
    <div className="mx-auto min-h-svh max-w-5xl px-6 py-10">
      <Toaster richColors position="top-right" />

      <header className="mb-8 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Acme Data Room</h1>
          <p className="text-sm text-muted-foreground">
            Due-diligence document repository
          </p>
        </div>
        <div className="flex items-center gap-2">
          <SearchInput value={search} onChange={setSearch} />
          <ConnectDriveButton connected={driveConnected} />
          {driveConnected && (
            <Button variant="outline" onClick={() => setImportOpen(true)}>
              <CloudDownload className="size-4" />
              Import from Drive
            </Button>
          )}
          <UploadButton onUploaded={() => refreshFiles(search)} />
        </div>
      </header>

      <div className="mb-4 flex items-center justify-between text-sm text-muted-foreground">
        <span>Signed in as {user?.email}</span>
        <button
          type="button"
          onClick={() => logout()}
          className="flex items-center gap-1 hover:text-foreground hover:underline"
        >
          <LogOut className="size-3.5" />
          Log out
        </button>
      </div>

      <FileTable
        files={files}
        loading={filesLoading}
        onDeleted={() => refreshFiles(search)}
        searchActive={search.trim().length > 0}
      />

      <ImportDriveDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        onImported={() => refreshFiles(search)}
        onNeedsReconnect={handleNeedsReconnect}
      />
    </div>
  )
}

function App() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex min-h-svh items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!user) {
    return <AuthScreen />
  }

  return <DataRoom />
}

export default App
