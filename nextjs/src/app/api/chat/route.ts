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
    "- You are LLM named Buddy.",
    "- Do not attempt to guess or elaborate. Do not speculate or fill in gaps.",
    "- Be concise.",
  ];

  const systemPrompt = Array.isArray(basePrompt)
    ? basePrompt.join(" ")
    : basePrompt;

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
      stopSequences: ["<|im_end|>", "<|eot_id|>", "<|end|>", "</s>"],
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
