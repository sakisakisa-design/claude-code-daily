import { McpAgent } from "agents/mcp";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

interface Env {
  AI: Ai;
  MEMO_INDEX: Vectorize;
  MCP_OBJECT: DurableObjectNamespace;
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
      "Save a piece of text into the memory index. Returns the assigned id.",
      {
        content: z.string().describe("The text to remember"),
        tags: z.array(z.string()).optional().describe("Optional tags for filtering"),
      },
      async ({ content, tags }) => {
        const values = await embed(this.env, content);
        const id = crypto.randomUUID();
        await this.env.MEMO_INDEX.upsert([
          {
            id,
            values,
            metadata: {
              content,
              tags: tags ?? [],
              created_at: new Date().toISOString(),
            },
          },
        ]);
        return {
          content: [{ type: "text", text: `saved id=${id}` }],
        };
      },
    );

    this.server.tool(
      "search_memory",
      "Semantic search over saved memories. Returns top matches with content, score and tags.",
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
          const md = (m.metadata ?? {}) as { content?: string; tags?: string[] };
          return `[${m.score.toFixed(3)}] ${md.content ?? ""}  ${(md.tags ?? []).map((t) => "#" + t).join(" ")}`.trim();
        });
        return {
          content: [
            { type: "text", text: lines.length ? lines.join("\n") : "(no matches)" },
          ],
        };
      },
    );

    this.server.tool(
      "delete_memory",
      "Delete a memory by id.",
      { id: z.string() },
      async ({ id }) => {
        await this.env.MEMO_INDEX.deleteByIds([id]);
        return { content: [{ type: "text", text: `deleted id=${id}` }] };
      },
    );
  }
}

export default {
  fetch(request: Request, env: Env, ctx: ExecutionContext) {
    const url = new URL(request.url);

    if (url.pathname === "/mcp") {
      return MemoMCP.serve("/mcp").fetch(request, env, ctx);
    }
    if (url.pathname === "/sse" || url.pathname === "/sse/message") {
      return MemoMCP.serveSSE("/sse").fetch(request, env, ctx);
    }
    if (url.pathname === "/") {
      return new Response(
        "memo-mcp ok\nendpoints: /mcp (streamable http), /sse (legacy)\n",
        { headers: { "content-type": "text/plain" } },
      );
    }
    return new Response("not found", { status: 404 });
  },
};
