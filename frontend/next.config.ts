import type { NextConfig } from "next";

/**
 * 两套构建模式由环境变量切换:
 *  - 开发 / 默认:`next dev`,前端跑 3000,通过 rewrites 把 /api/* 转发到 :8000
 *  - 静态导出:`BUILD_TARGET=static next build` → 输出 ./out,可被后端打包托管
 *
 * 静态导出模式下不能用 rewrites(没有 Node server 来转发),
 * 此时由前端 http.ts 直接请求同源 /api/*,后端 FastAPI 本身就提供这些路由。
 */
const isStatic = process.env.BUILD_TARGET === "static";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  ...(isStatic
    ? {
        output: "export",
        images: { unoptimized: true },
        trailingSlash: true,
      }
    : {
        async rewrites() {
          const backend =
            process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";
          return [
            { source: "/api/:path*", destination: `${backend}/api/:path*` },
          ];
        },
      }),
};

export default nextConfig;
