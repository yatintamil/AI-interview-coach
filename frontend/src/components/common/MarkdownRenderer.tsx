import React from 'react';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

/**
 * Pure, safe React Markdown Renderer.
 * Converts markdown text into native React JSX elements without dangerouslySetInnerHTML.
 * Supports:
 * - Headings (#, ##, ###, ####)
 * - Fenced code blocks (```lang ... ```)
 * - Inline code (`code`)
 * - Bold (**text**, __text__) and Italic (*text*, _text_)
 * - Unordered lists (- or *) and Ordered lists (1., 2.)
 * - Markdown tables (| Header | ... |)
 * - Blockquotes (> quote)
 * - Horizontal rules (---, ***)
 * - Paragraphs with clean spacing
 */
export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className }) => {
  if (!content) return null;

  const blocks = parseMarkdownBlocks(content);

  return (
    <div className={`markdown-body-content ${className || ''}`}>
      {blocks.map((block, index) => renderBlock(block, index))}
    </div>
  );
};

// Types of parsed blocks
type BlockType =
  | { type: 'heading'; level: number; text: string }
  | { type: 'code_block'; lang: string; code: string }
  | { type: 'blockquote'; lines: string[] }
  | { type: 'table'; headers: string[]; rows: string[][] }
  | { type: 'ul'; items: string[] }
  | { type: 'ol'; items: string[] }
  | { type: 'hr' }
  | { type: 'paragraph'; text: string };

function parseMarkdownBlocks(rawText: string): BlockType[] {
  const lines = rawText.replace(/\r\n/g, '\n').split('\n');
  const blocks: BlockType[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // Skip empty lines
    if (!trimmed) {
      i++;
      continue;
    }

    // 1. Fenced Code Block
    if (trimmed.startsWith('```')) {
      const lang = trimmed.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      if (i < lines.length && lines[i].trim().startsWith('```')) {
        i++; // skip closing ```
      }
      blocks.push({
        type: 'code_block',
        lang,
        code: codeLines.join('\n'),
      });
      continue;
    }

    // 2. Horizontal Rule
    if (/^(---|___|\*\*\*)$/.test(trimmed)) {
      blocks.push({ type: 'hr' });
      i++;
      continue;
    }

    // 3. Headings (#, ##, ###, ####)
    const headingMatch = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      blocks.push({
        type: 'heading',
        level: headingMatch[1].length,
        text: headingMatch[2],
      });
      i++;
      continue;
    }

    // 4. Blockquotes (> line)
    if (trimmed.startsWith('>')) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('>')) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ''));
        i++;
      }
      blocks.push({
        type: 'blockquote',
        lines: quoteLines,
      });
      continue;
    }

    // 5. Markdown Table (header row with | and next line with |---|)
    if (trimmed.startsWith('|') && trimmed.endsWith('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const headers = splitTableRow(trimmed);
      i += 2; // skip header and separator
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        rows.push(splitTableRow(lines[i].trim()));
        i++;
      }
      blocks.push({
        type: 'table',
        headers,
        rows,
      });
      continue;
    }

    // 6. Unordered List (- or *)
    if (/^[-*]\s+/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*]\s+/, ''));
        i++;
      }
      blocks.push({
        type: 'ul',
        items,
      });
      continue;
    }

    // 7. Ordered List (1., 2., etc.)
    if (/^\d+\.\s+/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s+/, ''));
        i++;
      }
      blocks.push({
        type: 'ol',
        items,
      });
      continue;
    }

    // 8. Paragraph (collect lines until blank line or special block starter)
    const paraLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !lines[i].trim().startsWith('```') &&
      !lines[i].trim().startsWith('#') &&
      !lines[i].trim().startsWith('>') &&
      !/^(---|___|\*\*\*)$/.test(lines[i].trim()) &&
      !/^[-*]\s+/.test(lines[i].trim()) &&
      !/^\d+\.\s+/.test(lines[i].trim()) &&
      !(lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1]))
    ) {
      paraLines.push(lines[i]);
      i++;
    }

    if (paraLines.length > 0) {
      blocks.push({
        type: 'paragraph',
        text: paraLines.join('\n'),
      });
    }
  }

  return blocks;
}

function isTableSeparator(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed.startsWith('|') || !trimmed.endsWith('|')) return false;
  const inner = trimmed.slice(1, -1).split('|');
  return inner.every((cell) => /^[\s:-]+$/.test(cell.trim()) && cell.includes('-'));
}

function splitTableRow(rowStr: string): string[] {
  // Strip leading and trailing '|'
  const trimmed = rowStr.replace(/^\|/, '').replace(/\|$/, '');
  return trimmed.split('|').map((col) => col.trim());
}

function renderBlock(block: BlockType, key: number): React.ReactNode {
  switch (block.type) {
    case 'heading': {
      const headingContent = renderInlineFormatting(block.text);
      if (block.level === 1) {
        return (
          <h1 key={key} className="markdown-h1">
            {headingContent}
          </h1>
        );
      }
      if (block.level === 2) {
        return (
          <h2 key={key} className="markdown-h2">
            {headingContent}
          </h2>
        );
      }
      if (block.level === 3) {
        return (
          <h3 key={key} className="markdown-h3">
            {headingContent}
          </h3>
        );
      }
      return (
        <h4 key={key} className="markdown-h4">
          {headingContent}
        </h4>
      );
    }

    case 'code_block':
      return (
        <pre key={key} className="code-block-container" data-testid="markdown-code-block">
          {block.lang && <div className="code-lang-tag">{block.lang}</div>}
          <code>{block.code}</code>
        </pre>
      );

    case 'blockquote':
      return (
        <blockquote key={key} className="markdown-blockquote">
          {block.lines.map((l, lIdx) => (
            <p key={lIdx}>{renderInlineFormatting(l)}</p>
          ))}
        </blockquote>
      );

    case 'table':
      return (
        <div key={key} className="markdown-table-wrapper" data-testid="markdown-table">
          <table className="markdown-table">
            <thead>
              <tr>
                {block.headers.map((h, hIdx) => (
                  <th key={hIdx}>{renderInlineFormatting(h)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, rIdx) => (
                <tr key={rIdx}>
                  {row.map((cell, cIdx) => (
                    <td key={cIdx}>{renderInlineFormatting(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );

    case 'ul':
      return (
        <ul key={key} className="markdown-list">
          {block.items.map((item, idx) => (
            <li key={idx}>{renderInlineFormatting(item)}</li>
          ))}
        </ul>
      );

    case 'ol':
      return (
        <ol key={key} className="markdown-ordered-list">
          {block.items.map((item, idx) => (
            <li key={idx}>{renderInlineFormatting(item)}</li>
          ))}
        </ol>
      );

    case 'hr':
      return <hr key={key} className="markdown-hr" />;

    case 'paragraph': {
      // Split internal newlines to preserve deliberate soft breaks
      const parts = block.text.split('\n');
      return (
        <p key={key} className="markdown-paragraph">
          {parts.map((p, pIdx) => (
            <React.Fragment key={pIdx}>
              {renderInlineFormatting(p)}
              {pIdx < parts.length - 1 && <br />}
            </React.Fragment>
          ))}
        </p>
      );
    }

    default:
      return null;
  }
}

/**
 * Parses inline formatting:
 * - `code` -> <code className="inline-code">
 * - **bold** or __bold__ -> <strong className="markdown-bold">
 * - *italic* or _italic_ -> <em className="markdown-italic">
 * - [link](url) -> <a href=... target="_blank">
 */
export function renderInlineFormatting(text: string): React.ReactNode[] {
  if (!text) return [];

  // Match: `code`, **bold**, *italic*, [text](url)
  const regex = /(`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_|\[[^\]]+\]\([^)]+\))/g;
  const parts = text.split(regex);
  const elements: React.ReactNode[] = [];

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];
    if (!part) continue;

    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      elements.push(
        <code key={i} className="inline-code">
          {part.slice(1, -1)}
        </code>
      );
    } else if (
      (part.startsWith('**') && part.endsWith('**') && part.length >= 4) ||
      (part.startsWith('__') && part.endsWith('__') && part.length >= 4)
    ) {
      elements.push(
        <strong key={i} className="markdown-bold">
          {part.slice(2, -2)}
        </strong>
      );
    } else if (
      (part.startsWith('*') && part.endsWith('*') && part.length >= 2) ||
      (part.startsWith('_') && part.endsWith('_') && part.length >= 2)
    ) {
      elements.push(
        <em key={i} className="markdown-italic">
          {part.slice(1, -1)}
        </em>
      );
    } else if (part.startsWith('[') && part.includes('](') && part.endsWith(')')) {
      const match = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (match) {
        const linkText = match[1];
        const rawHref = match[2];
        // Enforce safe URLs
        const safeHref =
          rawHref.startsWith('http://') || rawHref.startsWith('https://') || rawHref.startsWith('/')
            ? rawHref
            : '#';
        elements.push(
          <a
            key={i}
            href={safeHref}
            target="_blank"
            rel="noopener noreferrer"
            className="markdown-link"
          >
            {linkText}
          </a>
        );
      } else {
        elements.push(part);
      }
    } else {
      elements.push(part);
    }
  }

  return elements;
}

