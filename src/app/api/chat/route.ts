import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { streamText } from "ai";
import { NextResponse } from "next/server";
import { getCurrentTime } from "~/utils/currentTime";

const SYSTEM_PROMPT = env.LLM_SYSTEM_PROMPT || [
  '- You are LLM named Bubby.',
  '- Do not attempt to guess or elaborate. Do not speculate or fill in gaps.',
  '- Be concise.'
];

const systemPrompt = Array.isArray(SYSTEM_PROMPT)
  ? SYSTEM_PROMPT.join(' ')
  : SYSTEM_PROMPT;

const provider = createOpenAICompatible({
  name: "llm-provider",
  baseURL: env.LLM_BASE_URL,
  apiKey: env.LLM_API_KEY,
  includeUsage: true,
});

const getSystemPrompt = () => {
  const currentTime = getCurrentTime();
  return `${systemPrompt}\n\nCurrent date and time: ${currentTime}`;
};

export async function POST(req: Request) {
  try {
    const { messages } = await req.json();

    const result = streamText({
      model: provider(env.LLM_MODEL),
      system: getSystemPrompt(),
      messages,
      stopSequences: ["ees", "<|eot_id|>", "<|end|>", "</s>"],
    });

    return result.toTextStreamResponse();
  } catch (error) {
    console.error(error);
    return NextResponse.json(
      { error: "An unexpected error occurred. Please try again later." },
      { status: 500 },
    );
  }
}
