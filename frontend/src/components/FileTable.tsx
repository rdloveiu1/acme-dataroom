import { useState } from 'react'
import { Cloud, FileIcon, Loader2, Trash2, Upload } from 'lucide-react'
import { toast } from 'sonner'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { api, type DataroomFile } from '@/lib/api'
import { formatBytes, formatDate } from '@/lib/format'

export function FileTable({
  files,
  loading,
  onDeleted,
  searchActive = false,
}: {
  files: DataroomFile[]
  loading: boolean
  onDeleted: () => void
  searchActive?: boolean
}) {
  const [pendingDelete, setPendingDelete] = useState<DataroomFile | null>(null)
  const [deleting, setDeleting] = useState(false)

  async function confirmDelete() {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await api.deleteFile(pendingDelete.id)
      toast.success(`Deleted ${pendingDelete.name}`)
      onDeleted()
    } catch {
      toast.error(`Failed to delete ${pendingDelete.name}`)
    } finally {
      setDeleting(false)
      setPendingDelete(null)
    }
  }

  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    )
  }

  if (files.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-20 text-center">
        <FileIcon className="size-8 text-muted-foreground" />
        <p className="mt-3 text-sm font-medium">
          {searchActive ? 'No matching files' : 'No files yet'}
        </p>
        <p className="text-sm text-muted-foreground">
          {searchActive
            ? 'Try a different search term.'
            : 'Import files from Google Drive or upload from your computer.'}
        </p>
      </div>
    )
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Source</TableHead>
            <TableHead>Size</TableHead>
            <TableHead>Added</TableHead>
            <TableHead>Added by</TableHead>
            <TableHead className="w-10" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {files.map((file) => (
            <TableRow key={file.id}>
              <TableCell className="max-w-xs">
                <a
                  href={api.fileViewUrl(file.id)}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-2 truncate font-medium hover:underline"
                >
                  <FileIcon className="size-4 shrink-0 text-muted-foreground" />
                  <span className="truncate">{file.name}</span>
                </a>
              </TableCell>
              <TableCell>
                <Badge variant="secondary" className="gap-1">
                  {file.source === 'google_drive' ? (
                    <Cloud className="size-3" />
                  ) : (
                    <Upload className="size-3" />
                  )}
                  {file.source === 'google_drive' ? 'Drive' : 'Uploaded'}
                </Badge>
              </TableCell>
              <TableCell className="text-muted-foreground">
                {formatBytes(file.sizeBytes)}
              </TableCell>
              <TableCell className="text-muted-foreground">{formatDate(file.createdAt)}</TableCell>
              <TableCell className="text-muted-foreground">
                {file.uploadedByEmail ?? '—'}
              </TableCell>
              <TableCell>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setPendingDelete(file)}
                  aria-label={`Delete ${file.name}`}
                >
                  <Trash2 className="size-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <AlertDialog open={pendingDelete !== null} onOpenChange={(open) => !open && setPendingDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete "{pendingDelete?.name}"?</AlertDialogTitle>
            <AlertDialogDescription>
              This removes the file from this Data Room only. If it was imported from Google
              Drive, the original file in your Drive is not affected. This can't be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} disabled={deleting}>
              {deleting && <Loader2 className="size-4 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
