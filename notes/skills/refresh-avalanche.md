# Refresh Avalanche · 多事件合并刷新

## 问题

agent 一轮调 N 个工具,每个 `tool_result` 都触发"对应面板 reload"。
若多个面板订阅同一类事件,**一轮 5 个工具 → 15+ 次 API 请求 + UI 重渲染**。

桌面版 PySide6 上表现为"程序未响应"(主线程被刷新塞死,见 `D:\extendCode\DEV_NOTES.md` #18.1)。
web 版表现为闪烁 + 网络面板瀑布图惊恐。

## 套路

### 1. 把 reload 调度收敛到 hook 内部

订阅方代码不变(`useDataChanged(projectId, ["tree"], reload)`),
hook 内部用 `setTimeout(N ms)` 合并 burst:

```ts
const COALESCE_MS = 120;

useEffect(() => {
  let timer: ReturnType<typeof setTimeout> | null = null;

  function schedule() {
    if (timer) return;            // 已经排队了,不重复
    timer = setTimeout(() => {
      timer = null;
      reloadRef.current();
    }, COALESCE_MS);
  }

  function handler(e: Event) {
    if (matches(e)) schedule();
  }
  window.addEventListener("data_changed", handler);
  return () => { window.removeEventListener(...); if (timer) clearTimeout(timer); };
}, [projectId]);
```

### 2. 用 ref 存最新 reload,避免依赖数组

```ts
const reloadRef = useRef(reload);
reloadRef.current = reload;       // 每次 render 同步最新值
```

否则要么 useEffect 依赖 `reload` 频繁重绑事件,要么得调用方 `useCallback` 包一层。

### 3. 桌面版的等价做法

PySide6 上同理:用 `QTimer.singleShot(120, self._do_reload)` 代替直接调用,
多次触发也只会推到下一帧合并。**不要**在 worker 线程算"够不够攒一批",
合并应该在 UI 线程做,逻辑最简单。

### 4. 选 coalesce 间隔

- 50ms — 太短,密集事件还是会多次 reload
- 120-200ms — 用户感知不到,刚好覆盖 LLM 工具串调间隔
- 500ms+ — 用户会感知到"页面慢半拍",尤其点按钮后再等数据
- 用 `requestAnimationFrame` 可以,但 RAF 在窗口失焦时会被冻结,
  agent 后台跑、用户切到别的 Tab 回来发现数据没刷,用户会以为坏了

## 反例

- ❌ 在订阅方调用 `lodash.debounce(reload, 200)`:
  每个组件自己 debounce,缓存对象数量等于订阅数,且不同组件可能用不同间隔,
  系统行为不可预测。
- ❌ 把 reload 拍成"全量项目数据 refetch"。粒度应该是**单个面板**,
  反正用户当前只能看到一个 section。
- ❌ 在 agent service 端做合并(攒一批 tool_result 再 emit):
  破坏 SSE 流式语义,中间状态用户看不到 → 失去 agent 透明度。
  **合并是 UI 关心的事,不是协议关心的事**。

## 真实位置

- web 版 hook: `frontend/lib/hooks/use-data-changed.ts`
- 桌面版同类问题: `D:\extendCode\DEV_NOTES.md` #18.1
- 桌面版 `refresh_after_agent` 把全量刷新留到 `on_done` 一次性做完
