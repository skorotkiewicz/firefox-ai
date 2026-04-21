"use client";

import { CheckFatIcon } from "@phosphor-icons/react/dist/icons/CheckFat";
import { CopyIcon } from "@phosphor-icons/react/dist/icons/Copy";
import type { Root } from "hast";
import type { JSX } from "react";
import {
  Children,
  Fragment,
  isValidElement,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import { jsx, jsxs } from "react/jsx-runtime";
import flattenChildren from "react-keyed-flatten-children";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/cjs/styles/prism";
import rehypeReact from "rehype-react";
import remarkGfm from "remark-gfm";
import remarkParse from "remark-parse";
import remarkRehype from "remark-rehype";
import type { Plugin } from "unified";
import { unified } from "unified";
import { visit } from "unist-util-visit";

// Rehype plugin to convert <p> inside <li> to <div>
const rehypeListItemParagraphToDiv: Plugin<[], Root> = () => {
  return (tree: Root) => {
    visit(tree, "element", (element) => {
      if (element.tagName === "li") {
        element.children = element.children.map((child) => {
          if (child.type === "element" && child.tagName === "p") {
            child.tagName = "div";
          }
          return child;
        });
      }
    });
    return tree;
  };
};

// Create components with dark mode support
const createComponents = (isDark: boolean) => ({
  a: ({
    href,
    children,
    isDark,
  }: JSX.IntrinsicElements["a"] & { isDark?: boolean }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={`font-semibold underline underline-offset-2 decoration-1 transition-colors ${
        isDark
          ? "text-neutral-300 hover:text-white"
          : "text-blue-700 hover:text-blue-800"
      }`}
    >
      {children}
    </a>
  ),
  h1: ({ children }: JSX.IntrinsicElements["h1"]) => (
    <h1
      className={`font-bold text-2xl mb-4 mt-4 ${isDark ? "text-white" : "text-gray-900"}`}
    >
      {children}
    </h1>
  ),
  h2: ({ children }: JSX.IntrinsicElements["h2"]) => (
    <h2
      className={`font-semibold text-xl mb-3 mt-3 ${isDark ? "text-white" : "text-gray-900"}`}
    >
      {children}
    </h2>
  ),
  h3: ({ children }: JSX.IntrinsicElements["h3"]) => (
    <h3
      className={`font-semibold text-lg mb-2 mt-2 ${isDark ? "text-white" : "text-gray-900"}`}
    >
      {children}
    </h3>
  ),
  p: ({ children }: JSX.IntrinsicElements["p"]) => (
    <p className={`text-sm mb-4 ${isDark ? "text-gray-100" : "text-gray-800"}`}>
      {children}
    </p>
  ),
  strong: ({ children }: JSX.IntrinsicElements["strong"]) => (
    <strong
      className={`font-semibold ${isDark ? "text-gray-50" : "text-gray-950"}`}
    >
      {children}
    </strong>
  ),
  em: ({ children }: JSX.IntrinsicElements["em"]) => <em>{children}</em>,
  code: ({ children, className }: JSX.IntrinsicElements["code"]) => {
    const [copied, setCopied] = useState(false);
    const code = String(children).replace(/\n$/, "");
    const languageMatch = className?.match(/language-(\w+)/);
    const language = languageMatch ? languageMatch[1] : "";
    const isCodeBlock = Boolean(className);

    useEffect(() => {
      if (copied) {
        const t = setTimeout(() => setCopied(false), 1500);
        return () => clearTimeout(t);
      }
    }, [copied]);

    const copy = useCallback(() => {
      navigator.clipboard.writeText(code);
      setCopied(true);
    }, [code]);

    // Inline code
    if (!isCodeBlock) {
      return (
        <code
          className={`px-1.5 py-0.5 rounded text-sm font-mono ${
            isDark
              ? "bg-neutral-800 text-neutral-300"
              : "bg-gray-100 text-blue-800"
          }`}
        >
          {children}
        </code>
      );
    }

    // Code block with syntax highlighting
    return (
      <div className="relative mb-4 group">
        <div className="flex">
          <div className="flex-1 overflow-hidden rounded-lg">
            <SyntaxHighlighter
              language={language || "text"}
              style={oneDark}
              customStyle={{
                margin: 0,
                padding: "1rem",
                fontSize: "0.875rem",
                borderRadius: "0.5rem",
                wordBreak: "break-word",
                whiteSpace: "pre-wrap",
              }}
              wrapLongLines
              wrapLines
            >
              {code}
            </SyntaxHighlighter>
          </div>
          <div className="flex flex-col gap-1 ml-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              type="button"
              onClick={copy}
              className="p-1.5 rounded bg-slate-700 hover:bg-slate-600 text-slate-300 transition-colors"
              title="Copy code"
            >
              {copied ? (
                <CheckFatIcon className="w-4 h-4" />
              ) : (
                <CopyIcon className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>
    );
  },
  pre: ({ children }: JSX.IntrinsicElements["pre"]) => <>{children}</>,
  blockquote: ({ children }: JSX.IntrinsicElements["blockquote"]) => (
    <blockquote
      className={`border-l-4 pl-4 italic my-4 ${
        isDark
          ? "border-gray-600 text-gray-300"
          : "border-gray-300 text-gray-700"
      }`}
    >
      {children}
    </blockquote>
  ),
  ul: ({ children }: JSX.IntrinsicElements["ul"]) => (
    <ul
      className={`flex flex-col gap-2 my-4 pl-4 ${isDark ? "text-gray-200" : "text-gray-800"}`}
    >
      {Children.map(
        flattenChildren(children).filter(isValidElement),
        (child, i) => (
          <li key={`${i + '-item-ul'}`} className="flex gap-2 items-start">
            <span
              className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${isDark ? "bg-gray-400" : "bg-gray-500"}`}
            />
            {child}
          </li>
        ),
      )}
    </ul>
  ),
  ol: ({ children }: JSX.IntrinsicElements["ol"]) => (
    <ol
      className={`flex flex-col gap-2 my-4 pl-4 ${isDark ? "text-gray-200" : "text-gray-800"}`}
    >
      {Children.map(
        flattenChildren(children).filter(isValidElement),
        (child, i) => (
          <li key={`${i + 'item-ol'}`} className="flex gap-2 items-start">
            <span
              className={`font-semibold min-w-[1.5ch] ${isDark ? "text-neutral-400" : "text-blue-700"}`}
            >
              {i + 1}.
            </span>
            {child}
          </li>
        ),
      )}
    </ol>
  ),
  li: ({ children }: JSX.IntrinsicElements["li"]) => (
    <div className="text-sm">{children}</div>
  ),
});

// Markdown Processor with dark mode support
export const useMarkdownProcessor = (
  content: string,
  isDark: boolean = false,
) => {
  const processor = useMemo(() => {
    const components = createComponents(isDark);
    return unified()
      .use(remarkParse)
      .use(remarkGfm)
      .use(remarkRehype)
      .use(rehypeListItemParagraphToDiv)
      .use(rehypeReact, { jsx, jsxs, Fragment, components });
  }, [isDark]);

  return useMemo(
    () => processor.processSync(content).result,
    [processor, content],
  );
};
