import { http } from "../http";

export interface Character {
  id: string;
  project_id: string;
  name: string;
  role: string;
  profile: string;
}

export const charactersApi = {
  list: (projectId: string) =>
    http.get<Character[]>(`/api/projects/${projectId}/characters`),
  upsert: (
    projectId: string,
    body: { id?: string; name: string; role?: string; profile?: string },
  ) => http.post<Character>(`/api/projects/${projectId}/characters`, body),
  remove: (projectId: string, id: string) =>
    http.del<void>(`/api/projects/${projectId}/characters/${id}`),
};
