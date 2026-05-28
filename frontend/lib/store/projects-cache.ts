/**
 * 全局项目缓存(stale-while-revalidate)。
 *
 * 解决 dev 模式下"主页 ↔ 工作区互跳"卡顿:
 *  - 每次 mount 时不再硬等待 GET 完成才渲染
 *  - 已访问过的页面立刻用缓存渲染,后台静默 refresh
 *  - 主页第一次拉到的项目摘要可以喂给工作区,工作区进来即时见 shell
 */
import { create } from "zustand";

import { projectsApi, type Project } from "@/lib/api/endpoints/projects";

interface ProjectsCacheState {
  list: Project[] | null;
  listLoading: boolean;
  listFetchedAt: number; // ms
  byId: Record<string, Project>;
  // 加载列表(SWR:有缓存就立即返回,后台刷新;无缓存就阻塞首次)
  loadList: (opts?: { force?: boolean }) => Promise<Project[]>;
  // 加载单项(同 SWR)
  loadOne: (id: string, opts?: { force?: boolean }) => Promise<Project>;
  // 直接喂入(创建/更新后写回)
  setOne: (p: Project) => void;
  // 删除
  removeOne: (id: string) => void;
}

export const useProjectsCache = create<ProjectsCacheState>((set, get) => ({
  list: null,
  listLoading: false,
  listFetchedAt: 0,
  byId: {},

  async loadList(opts) {
    const force = opts?.force ?? false;
    const { list, listLoading } = get();
    // 已有缓存:不阻塞,后台刷新
    if (list && !force) {
      if (!listLoading) {
        set({ listLoading: true });
        projectsApi
          .list()
          .then((items) => {
            const byId = { ...get().byId };
            for (const p of items) byId[p.id] = p;
            set({
              list: items,
              listLoading: false,
              listFetchedAt: Date.now(),
              byId,
            });
          })
          .catch(() => set({ listLoading: false }));
      }
      return list;
    }
    // 无缓存:阻塞拉一次
    set({ listLoading: true });
    const items = await projectsApi.list();
    const byId = { ...get().byId };
    for (const p of items) byId[p.id] = p;
    set({
      list: items,
      listLoading: false,
      listFetchedAt: Date.now(),
      byId,
    });
    return items;
  },

  async loadOne(id, opts) {
    const force = opts?.force ?? false;
    const cached = get().byId[id];
    if (cached && !force) {
      // 后台刷新
      projectsApi
        .get(id)
        .then((p) => set((s) => ({ byId: { ...s.byId, [p.id]: p } })))
        .catch(() => {});
      return cached;
    }
    const p = await projectsApi.get(id);
    set((s) => ({ byId: { ...s.byId, [p.id]: p } }));
    return p;
  },

  setOne(p) {
    set((s) => {
      const byId = { ...s.byId, [p.id]: p };
      const list = s.list
        ? s.list.some((x) => x.id === p.id)
          ? s.list.map((x) => (x.id === p.id ? p : x))
          : [...s.list, p]
        : s.list;
      return { byId, list };
    });
  },

  removeOne(id) {
    set((s) => {
      const byId = { ...s.byId };
      delete byId[id];
      const list = s.list ? s.list.filter((x) => x.id !== id) : s.list;
      return { byId, list };
    });
  },
}));
