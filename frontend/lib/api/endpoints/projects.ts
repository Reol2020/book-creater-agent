import { http } from "../http";

export interface Project {
  id: string;
  name: string;
  genre: string;
  synopsis: string;
  style: string;
  outline: string;
  created_at: string;
  updated_at: string;
}

export interface Chapter {
  id: string;
  project_id: string;
  title: string;
  summary: string;
  content: string;
  order_index: number;
  word_count: number;
  created_at: string;
  updated_at: string;
}

export const projectsApi = {
  list: () => http.get<Project[]>("/api/projects"),
  get: (id: string) => http.get<Project>(`/api/projects/${id}`),
  create: (body: Partial<Project> & { name: string }) =>
    http.post<Project>("/api/projects", body),
  update: (id: string, body: Partial<Project> & { name: string }) =>
    http.put<Project>(`/api/projects/${id}`, body),
  remove: (id: string) => http.del<void>(`/api/projects/${id}`),

  listChapters: (projectId: string) =>
    http.get<Chapter[]>(`/api/projects/${projectId}/chapters`),
  createChapter: (projectId: string, body: Partial<Chapter>) =>
    http.post<Chapter>(`/api/projects/${projectId}/chapters`, body),
  updateChapter: (
    projectId: string,
    chapterId: string,
    body: Partial<Chapter>,
  ) =>
    http.put<Chapter>(
      `/api/projects/${projectId}/chapters/${chapterId}`,
      body,
    ),
  removeChapter: (projectId: string, chapterId: string) =>
    http.del<void>(`/api/projects/${projectId}/chapters/${chapterId}`),
  reorderChapters: (projectId: string, ordered_ids: string[]) =>
    http.post<void>(`/api/projects/${projectId}/chapters/reorder`, {
      ordered_ids,
    }),
};
