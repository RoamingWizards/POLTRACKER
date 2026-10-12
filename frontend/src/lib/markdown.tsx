import type { ReactNode } from 'react';
import Link from '@mui/material/Link';

/** Inline `code`, **bold** and <https://links> or [text](url): all the policy file uses. Nothing is parsed as HTML. */
function inline(text: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /`([^`]+)`|\*\*([^*]+)\*\*|<(https?:\/\/[^>\s]+)>|\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const k = out.length;
    if (m[1] !== undefined) out.push(<code key={k}>{m[1]}</code>);
    else if (m[2] !== undefined) out.push(<strong key={k}>{m[2]}</strong>);
    else {
      const href = m[3] ?? m[5];
      out.push(
        <Link key={k} href={href} target="_blank" rel="noreferrer noopener">
          {m[4] ?? href}
        </Link>,
      );
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export type Block = { type: 'h1' | 'h2' | 'p'; text: string } | { type: 'ul'; items: string[] };

/** Headings (#, ##), paragraphs and "- " lists: the subset PRIVACY.md is written in. */
export function parseBlocks(md: string): Block[] {
  const blocks: Block[] = [];
  let para: string[] = [];
  const flush = () => {
    if (para.length) blocks.push({ type: 'p', text: para.join(' ') });
    para = [];
  };
  for (const raw of md.split('\n')) {
    const line = raw.trimEnd();
    if (!line.trim()) flush();
    else if (line.startsWith('## ')) (flush(), blocks.push({ type: 'h2', text: line.slice(3) }));
    else if (line.startsWith('# ')) (flush(), blocks.push({ type: 'h1', text: line.slice(2) }));
    else if (line.startsWith('- ')) {
      flush();
      const last = blocks[blocks.length - 1];
      if (last?.type === 'ul') last.items.push(line.slice(2));
      else blocks.push({ type: 'ul', items: [line.slice(2)] });
    } else if (/^\s+\S/.test(line) && blocks[blocks.length - 1]?.type === 'ul' && !para.length) {
      const last = blocks[blocks.length - 1] as { type: 'ul'; items: string[] };
      last.items[last.items.length - 1] += ' ' + line.trim();
    } else para.push(line.trim());
  }
  flush();
  return blocks;
}

export { inline };
