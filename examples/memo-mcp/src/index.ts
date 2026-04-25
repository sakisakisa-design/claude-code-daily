import { McpAgent } from "agents/mcp";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

interface Env {
  AI: Ai;
  MEMO_INDEX: Vectorize;
  MCP_OBJECT: DurableObjectNamespace;
  API_KEY?: string;
}

const EMBED_MODEL = "@cf/google/embeddinggemma-300m";

async function embed(env: Env, text: string): Promise<number[]> {
  const res = await env.AI.run(EMBED_MODEL as any, { text: [text] }) as { data: number[][] };
  return res.data[0];
}

export class MemoMCP extends McpAgent<Env> {
  server = new McpServer({ name: "memo-kb", version: "0.1.0" });

  async init() {
    this.server.tool(
      "write_memory",
      "Save or upsert a memory. If id is provided, overwrites that record (use for updates). Otherwise a new uuid is assigned. Returns the id.",
      {
        content: z.string().describe("The text to remember"),
        tags: z.array(z.string()).optional().describe("Optional tags for filtering"),
        id: z.string().optional().describe("Optional explicit id. If provided, upserts (overwrites) that record. Use search_memory first to find existing ids."),
        source_id: z.string().optional().describe("Optional pointer to an external source record (e.g. source memo id). Stored as metadata."),
      },
      async ({ content, tags, id, source_id }) => {
        const values = await embed(this.env, content);
        const finalId = id ?? crypto.randomUUID();
        const metadata: Record<string, unknown> = {
          content,
          tags: tags ?? [],
          created_at: new Date().toISOString(),
        };
        if (source_id) metadata.source_id = source_id;
        await this.env.MEMO_INDEX.upsert([{ id: finalId, values, metadata }]);
        return {
          content: [{ type: "text", text: `id=${finalId}` }],
        };
      },
    );

    this.server.tool(
      "search_memory",
      "Semantic search over saved memories. Returns top matches as JSON lines with id, score, content, tags, source_id. Use the id with delete_memory or write_memory(id=...) for updates.",
      {
        query: z.string().describe("What to look for"),
        topK: z.number().int().min(1).max(20).default(5),
        tag: z.string().optional().describe("If set, only return memories that have this tag"),
      },
      async ({ query, topK, tag }) => {
        const values = await embed(this.env, query);
        const result = await this.env.MEMO_INDEX.query(values, {
          topK,
          returnMetadata: "all",
          filter: tag ? { tags: { $in: [tag] } } : undefined,
        });
        const lines = result.matches.map((m) => {
          const md = (m.metadata ?? {}) as {
            content?: string;
            tags?: string[];
            source_id?: string;
            created_at?: string;
          };
          return JSON.stringify({
            id: m.id,
            score: Number(m.score.toFixed(4)),
            content: md.content ?? "",
            tags: md.tags ?? [],
            source_id: md.source_id,
            created_at: md.created_at,
          });
        });
        return {
          content: [
            { type: "text", text: lines.length ? lines.join("\n") : "(no matches)" },
          ],
        };
      },
    );

    this.server.tool(
      "get_memory",
      "Fetch one or more memories by id. Returns same JSON shape as search_memory.",
      {
        ids: z.array(z.string()).min(1).max(50).describe("List of memory ids"),
      },
      async ({ ids }) => {
        const result = await this.env.MEMO_INDEX.getByIds(ids);
        const lines = result.map((m) => {
          const md = (m.metadata ?? {}) as {
            content?: string;
            tags?: string[];
            source_id?: string;
            created_at?: string;
          };
          return JSON.stringify({
            id: m.id,
            content: md.content ?? "",
            tags: md.tags ?? [],
            source_id: md.source_id,
            created_at: md.created_at,
          });
        });
        return {
          content: [
            { type: "text", text: lines.length ? lines.join("\n") : "(not found)" },
          ],
        };
      },
    );

    this.server.tool(
      "delete_memory",
      "Delete one or more memories by id.",
      { ids: z.array(z.string()).min(1).max(50).describe("List of memory ids to delete") },
      async ({ ids }) => {
        await this.env.MEMO_INDEX.deleteByIds(ids);
        return { content: [{ type: "text", text: `deleted ${ids.length} id(s): ${ids.join(", ")}` }] };
      },
    );
  }
}

async function handleSearch(request: Request, env: Env): Promise<Response> {
  let body: { query?: string; topK?: number; tag?: string };
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: "invalid json" }), {
      status: 400,
      headers: { "content-type": "application/json" },
    });
  }
  const query = body.query;
  if (!query || typeof query !== "string") {
    return new Response(JSON.stringify({ error: "query required" }), {
      status: 400,
      headers: { "content-type": "application/json" },
    });
  }
  const topK = Math.max(1, Math.min(20, Number(body.topK) || 5));
  const tag = body.tag;
  const values = await embed(env, query);
  const result = await env.MEMO_INDEX.query(values, {
    topK,
    returnMetadata: "all",
    filter: tag ? { tags: { $in: [tag] } } : undefined,
  });
  const matches = result.matches.map((m) => {
    const md = (m.metadata ?? {}) as {
      content?: string;
      tags?: string[];
      source_id?: string;
      created_at?: string;
    };
    return {
      id: m.id,
      score: Number(m.score.toFixed(4)),
      content: md.content ?? "",
      tags: md.tags ?? [],
      source_id: md.source_id,
      created_at: md.created_at,
    };
  });
  return new Response(JSON.stringify({ matches }), {
    headers: { "content-type": "application/json" },
  });
}

function checkAuth(request: Request, env: Env): Response | null {
  if (!env.API_KEY) return null;
  // 1. ?token=<key> query param — friendly to clients that only accept a URL
  const url = new URL(request.url);
  if (url.searchParams.get("token") === env.API_KEY) return null;
  // 2. x-api-key header
  if (request.headers.get("x-api-key") === env.API_KEY) return null;
  const auth = request.headers.get("authorization") ?? "";
  // 3. Authorization: Bearer <key>
  const bearer = auth.match(/^Bearer\s+(.+)$/i);
  if (bearer && bearer[1].trim() === env.API_KEY) return null;
  // 4. Authorization: Basic base64(user:pass) — accept the key in either slot
  const basic = auth.match(/^Basic\s+(.+)$/i);
  if (basic) {
    try {
      const decoded = atob(basic[1].trim());
      const idx = decoded.indexOf(":");
      const user = idx >= 0 ? decoded.slice(0, idx) : decoded;
      const pass = idx >= 0 ? decoded.slice(idx + 1) : "";
      if (user === env.API_KEY || pass === env.API_KEY) return null;
    } catch {
      // fall through
    }
  }
  return new Response("unauthorized", { status: 401 });
}

export default {
  fetch(request: Request, env: Env, ctx: ExecutionContext) {
    const url = new URL(request.url);

    if (url.pathname === "/") {
      return new Response(
        "memo-mcp ok\nendpoints: /mcp (streamable http), /sse (legacy)\n",
        { headers: { "content-type": "text/plain" } },
      );
    }

    const authFail = checkAuth(request, env);
    if (authFail) return authFail;

    if (url.pathname === "/mcp") {
      return MemoMCP.serve("/mcp").fetch(request, env, ctx);
    }
    if (url.pathname === "/sse" || url.pathname === "/sse/message") {
      return MemoMCP.serveSSE("/sse").fetch(request, env, ctx);
    }
    // Lightweight non-MCP search endpoint for hooks / clients that don't
    // want the JSON-RPC handshake overhead. POST /search with JSON body
    // {"query": "...", "topK": 8, "tag": "optional"}.
    if (url.pathname === "/search" && request.method === "POST") {
      return handleSearch(request, env);
    }
    return new Response("not found", { status: 404 });
  },
};
