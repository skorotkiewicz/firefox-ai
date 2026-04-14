// app/api/chat/route.ts
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { convertToModelMessages, streamText } from "ai";
import { NextResponse } from "next/server";
import { getCurrentTime } from "@/app/utils/currentTime";

const provider = createOpenAICompatible({
  name: "llm-provider",
  apiKey: process.env.LLM_API_KEY || "dummy",
  baseURL: process.env.LLM_BASE_URL || "http://192.168.0.124:8888/v1",
  includeUsage: true,
});

const getSystemPrompt = () => {
  const currentTime = getCurrentTime();
  const basePrompt = process.env.LLM_SYSTEM_PROMPT || [
    '- You are LLM named Bubby.',
    '- Do not attempt to guess or elaborate. Do not speculate or fill in gaps.',
    '- Be concise.'
  ];

  const systemPrompt = Array.isArray(basePrompt) ? basePrompt.join(' ') : basePrompt;

  return `${systemPrompt}\n\n Current date and time: ${currentTime}`;
};

export async function POST(req: Request) {
  const { messages, model } = await req.json();

  try {
    // convertToModelMessages returns a Promise, need to await
    const modelMessages = await convertToModelMessages(messages);

    const result = streamText({
      model: provider(model || process.env.LLM_MODEL || "local"),
      system: getSystemPrompt(),
      messages: modelMessages,
      stopSequences: ["ees", "<|eot_id|>", "<|end|>", "</s>"],
    });

    return result.toTextStreamResponse();
  } catch (e) {
    console.error(e);
    return NextResponse.json(
      { error: "An unexpected error occurred. Please try again later." },
      { status: 500 },
    );
  }
}

/*

// app/api/chat/route.ts
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { convertToModelMessages, streamText } from "ai";
import { NextResponse } from "next/server";
import { getCurrentTime } from "@/app/utils/currentTime";

const provider = createOpenAICompatible({
  name: "llm-provider",
  apiKey: process.env.LLM_API_KEY || "dummy",
  baseURL: process.env.LLM_BASE_URL || "http://192.168.0.124:8888/v1",
  includeUsage: true,
});

const getSystemPrompt = () => {
  const currentTime = getCurrentTime();
  const basePrompt = process.env.LLM_SYSTEM_PROMPT || [
    '- You are LLM named Bubby.',
    '- Do not attempt to guess or elaborate. Do not speculate or fill in gaps.',
    '- Be concise.'
  ];

  const systemPrompt = Array.isArray(basePrompt) ? basePrompt.join(' ') : basePrompt;

  return `${systemPrompt} Current date and time: ${currentTime}`;
};

export async function POST(req: Request) {
  const { messages, model } = await req.json();

  try {
    const modelMessages = await convertToModelMessages(messages);

    const result = streamText({
      model: provider(model || process.env.LLM_MODEL || "local"),
      system: getSystemPrompt(),
      messages: modelMessages,
      stopSequences: ["ees", "<|eot_id|>", "<|end|>", "</s>"],
    });

    // Get the stream and transform it to strip leading newline
    const stream = result.toTextStreamResponse().body;
    if (!stream) {
      throw new Error("No stream available");
    }

    const reader = stream.getReader();
    let firstChunk = true;

    const transformedStream = new ReadableStream({
      async start(controller) {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) {
              controller.close();
              break;
            }

            // Decode the chunk
            const text = new TextDecoder().decode(value);

            // If it's the first chunk and starts with \n, remove it
            if (firstChunk && text.startsWith("\n")) {
              const stripped = text.slice(1);
              if (stripped) {
                controller.enqueue(new TextEncoder().encode(stripped));
              }
              firstChunk = false;
            } else {
              controller.enqueue(value);
              firstChunk = false;
            }
          }
        } catch (error) {
          controller.error(error);
        } finally {
          reader.releaseLock();
        }
      },
    });

    return new Response(transformedStream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });
  } catch (e) {
    console.error(e);
    return NextResponse.json(
      { error: "An unexpected error occurred. Please try again later." },
      { status: 500 },
    );
  }
}


*/
