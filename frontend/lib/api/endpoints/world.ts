import { http } from "../http";

export interface WorldEntry {
  id: string;
  project_id: string;
  title: string;
  category: string;
  content: string;
}

export const worldApi = {
  list: (projectId: string) =>
    http.get<WorldEntry[]>(`/api/projects/${projectId}/world`),
  upsert: (
    projectId: string,
    body: { id?: string; title: string; category?: string; content?: string },
  ) => http.post<WorldEntry>(`/api/projects/${projectId}/world`, body),
  remove: (projectId: string, id: string) =>
    http.del<void>(`/api/projects/${projectId}/world/${id}`),
};
