/** Public transport metadata only. No server signing or provider secret enters it. */
export function publicMcpEndpoint(base: string) {
  try {
    const u = new URL(base);
    if (
      u.username ||
      u.password ||
      u.search ||
      u.hash ||
      u.pathname !== "/" ||
      !(
        u.protocol === "https:" ||
        (u.protocol === "http:" && ["localhost", "127.0.0.1"].includes(u.hostname))
      )
    ) {
      return "";
    }
    return u.origin + "/api/v1/mcp";
  } catch {
    return "";
  }
}

function assertValidEndpoint(endpoint: string): string {
  const u = new URL(endpoint);
  if (publicMcpEndpoint(u.origin) !== endpoint) {
    throw new Error("Invalid MCP endpoint");
  }
  return endpoint;
}

export function copilotConfiguration(endpoint: string) {
  const valid = assertValidEndpoint(endpoint);
  return JSON.stringify(
    {
      mcpServers: {
        planeByte: {
          type: "http",
          url: valid,
          headers: { Authorization: "Bearer ${PLANEBYTE_MCP_KEY}" },
          tools: ["search_intent_signals", "list_intent_monitors", "get_intent_signal"],
        },
      },
    },
    null,
    2
  );
}

export type McpClientId = "claude_code" | "cursor" | "codex" | "streamable_http";

export function mcpClientSnippet(client: McpClientId, endpoint: string): {
  title: string;
  filename: string;
  language: string;
  code: string;
  note: string;
} {
  const valid = endpoint.startsWith("http") ? endpoint : "https://app.planebyte.com/api/v1/mcp";

  if (client === "claude_code") {
    return {
      title: "Claude Code (.mcp.json or CLI)",
      filename: ".mcp.json",
      language: "json",
      code: JSON.stringify(
        {
          mcpServers: {
            planebyte: {
              type: "http",
              url: valid,
              headers: {
                Authorization: "Bearer ${PLANEBYTE_MCP_KEY}",
              },
            },
          },
        },
        null,
        2
      ),
      note: `Or register via CLI: claude mcp add --transport http planebyte ${valid} --header "Authorization: Bearer $PLANEBYTE_MCP_KEY"`,
    };
  }

  if (client === "cursor") {
    return {
      title: "Cursor (.cursor/mcp.json)",
      filename: ".cursor/mcp.json",
      language: "json",
      code: JSON.stringify(
        {
          mcpServers: {
            planebyte: {
              url: valid,
              headers: {
                Authorization: "Bearer ${PLANEBYTE_MCP_KEY}",
              },
            },
          },
        },
        null,
        2
      ),
      note: "Set PLANEBYTE_MCP_KEY in your environment before launching Cursor. Keys require both mcp:use and intent:read scopes.",
    };
  }

  if (client === "codex") {
    return {
      title: "OpenAI Codex CLI (~/.codex/config.toml)",
      filename: "~/.codex/config.toml",
      language: "toml",
      code: [
        "[mcp_servers.planebyte]",
        `url = "${valid}"`,
        'bearer_token_env_var = "PLANEBYTE_MCP_KEY"',
      ].join("\n"),
      note: "Export PLANEBYTE_MCP_KEY in your shell profile. Codex sends Authorization: Bearer automatically over Streamable HTTP.",
    };
  }

  return {
    title: "Streamable HTTP / MCP Inspector (cURL)",
    filename: "mcp-initialize.sh",
    language: "bash",
    code: [
      `curl -X POST "${valid}" \\`,
      `  -H "Authorization: Bearer $PLANEBYTE_MCP_KEY" \\`,
      `  -H "Content-Type: application/json" \\`,
      `  -H "Accept: application/json, text/event-stream" \\`,
      `  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"planebyte-check","version":"1.0.0"}}}'`,
    ].join("\n"),
    note: "Streamable HTTP clients must send Accept: application/json, text/event-stream along with Authorization: Bearer.",
  };
}
