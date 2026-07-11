import { useEffect, useState } from 'react'
import { FileIcon, Loader2 } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { api, DriveAuthError, type DriveFile } from '@/lib/api'

export function ImportDriveDialog({
  open,
  onOpenChange,
  onImported,
  onNeedsReconnect,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onImported: () => void
  onNeedsReconnect: () => void
}) {
  const [driveFiles, setDriveFiles] = useState<DriveFile[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [importing, setImporting] = useState(false)

  useEffect(() => {
    if (!open) return
    setSelected(new Set())
    setLoading(true)
    api
      .listDriveFiles()
      .then((res) => setDriveFiles(res.files))
      .catch((err) => {
        if (err instanceof DriveAuthError) {
          onOpenChange(false)
          onNeedsReconnect()
        } else {
          toast.error('Could not load Drive files')
        }
      })
      .finally(() => setLoading(false))
  }, [open, onOpenChange, onNeedsReconnect])

  function toggle(fileId: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(fileId)) next.delete(fileId)
      else next.add(fileId)
      return next
    })
  }

  async function handleImport() {
    setImporting(true)
    let successCount = 0
    for (const fileId of selected) {
      try {
        await api.importDriveFile(fileId)
        successCount++
      } catch (err) {
        if (err instanceof DriveAuthError) {
          setImporting(false)
          onOpenChange(false)
          onNeedsReconnect()
          return
        }
        toast.error(`Failed to import ${driveFiles.find((f) => f.id === fileId)?.name ?? fileId}`)
      }
    }
    setImporting(false)
    if (successCount > 0) {
      toast.success(`Imported ${successCount} file${successCount === 1 ? '' : 's'}`)
      onImported()
      onOpenChange(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Import from Google Drive</DialogTitle>
          <DialogDescription>Select files to copy into this Data Room.</DialogDescription>
        </DialogHeader>

        <ScrollArea className="h-80 rounded-md border">
          {loading ? (
            <div className="flex h-full items-center justify-center py-16">
              <Loader2 className="size-5 animate-spin text-muted-foreground" />
            </div>
          ) : driveFiles.length === 0 ? (
            <p className="p-6 text-center text-sm text-muted-foreground">
              No files found in your Drive.
            </p>
          ) : (
            <ul className="divide-y">
              {driveFiles.map((file) => (
                <li key={file.id}>
                  <label className="flex cursor-pointer items-center gap-3 px-4 py-2.5 hover:bg-accent">
                    <Checkbox
                      checked={selected.has(file.id)}
                      onCheckedChange={() => toggle(file.id)}
                    />
                    <FileIcon className="size-4 shrink-0 text-muted-foreground" />
                    <span className="truncate text-sm">{file.name}</span>
                  </label>
                </li>
              ))}
            </ul>
          )}
        </ScrollArea>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={importing}>
            Cancel
          </Button>
          <Button onClick={handleImport} disabled={selected.size === 0 || importing}>
            {importing && <Loader2 className="size-4 animate-spin" />}
            Import {selected.size > 0 ? `(${selected.size})` : ''}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
