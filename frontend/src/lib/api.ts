const API_URL = import.meta.env.VITE_API_URL as string

export type DataroomFile = {
  id: string
  name: string
  mimeType: string
  sizeBytes: number
  source: 'upload' | 'google_drive'
  createdAt: string
}

export type DriveFile = {
  id: string
  name: string
  mimeType: string
  size?: string
  iconLink?: string
}

export class DriveAuthError extends Error {
  code: 'drive_not_connected' | 'drive_reauth_required'

  constructor(code: 'drive_not_connected' | 'drive_reauth_required') {
    super(code)
    this.code = code
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    credentials: 'include',
    ...init,
  })

  if (res.status === 401) {
    const body = await res.json().catch(() => ({}))
    if (body.error === 'drive_not_connected' || body.error === 'drive_reauth_required') {
      throw new DriveAuthError(body.error)
    }
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error || `Request failed: ${res.status}`)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  driveStatus: () => request<{ connected: boolean }>('/auth/google/status'),

  driveConnectUrl: () => `${API_URL}/auth/google/login`,

  driveDisconnect: () =>
    request<{ connected: boolean }>('/auth/google/disconnect', { method: 'POST' }),

  listDriveFiles: (pageToken?: string) =>
    request<{ files: DriveFile[]; nextPageToken?: string }>(
      `/drive/files${pageToken ? `?pageToken=${encodeURIComponent(pageToken)}` : ''}`,
    ),

  importDriveFile: (fileId: string) =>
    request<DataroomFile>('/drive/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fileId }),
    }),

  listFiles: () => request<DataroomFile[]>('/files'),

  uploadFile: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request<DataroomFile>('/files/upload', { method: 'POST', body: formData })
  },

  deleteFile: (id: string) => request<void>(`/files/${id}`, { method: 'DELETE' }),

  fileViewUrl: (id: string) => `${API_URL}/files/${id}`,
}
