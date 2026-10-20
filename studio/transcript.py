"""Presentation-only transcript state and conservative Markdown formatting."""
import re


def markdown(text):
    """Return plain text and GTK tag spans; never interpret HTML or Pango markup."""
    output, spans = '', []
    fenced = None
    for line in text.splitlines(keepends=True):
        fence = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line.rstrip('\r\n'))
        if fence and (fenced is None or (fence[1][0] == fenced[0] and len(fence[1]) >= len(fenced) and not fence[2].strip())):
            fenced = fence[1] if fenced is None else None
            continue
        if fenced:
            start = len(output)
            output += line
            spans.append(('code', start, len(output)))
            continue
        heading = re.match(r'^#{1,6}\s+', line)
        if heading:
            line = line[heading.end():]
        start = len(output)
        cursor = 0
        for match in re.finditer(r'(`[^`\n]+`|\*\*[^*\n]+\*\*|\[[^]\n]+\]\([^\s)]+\))', line):
            output += line[cursor:match.start()]
            token = match.group()
            offset = len(output)
            if token.startswith('`'):
                output += token[1:-1]
                spans.append(('code', offset, len(output)))
            elif token.startswith('**'):
                output += token[2:-2]
                spans.append(('bold', offset, len(output)))
            else:
                label, url = token[1:].split('](', 1)
                output += label + ' (' + url
            cursor = match.end()
        output += line[cursor:]
        if heading:
            spans.append(('bold', start, len(output)))
    return output, spans


def matches(text, query):
    if not query:
        return []
    return [(m.start(), m.end()) for m in re.finditer(re.escape(query), text, re.IGNORECASE)]


class Transcript:
    def __init__(self):
        self.rows = []
        self.items = {}

    def add(self, role, text, key=None):
        row = {'role': role, 'text': text, 'type': '', 'done': False, 'output': ''}
        self.rows.append(row)
        if key:
            self.items[key] = row
        # Bound presentation memory independently of persistent Codex history.
        while len(self.rows) > 1000 or (len(self.rows) > 1 and sum(len(r['text']) for r in self.rows) > 300000):
            removed = self.rows.pop(0)
            self.items = {k: v for k, v in self.items.items() if v is not removed}
        row['text'] = row['text'][-300000:]
        return row

    def item(self, item, completed=False):
        kind = item.get('type', '')
        if kind not in ('agentMessage', 'commandExecution', 'fileChange', 'mcpToolCall', 'webSearch'):
            return
        key = item.get('id')
        row = self.items.get(key)
        if row is not None and row['done'] and not completed:
            return
        if row is None:
            row = self.add('Codex' if kind == 'agentMessage' else 'Tool', '', key)
        row['type'] = kind
        if kind == 'agentMessage':
            if 'text' in item:
                row['text'] = item['text'][-300000:]
        else:
            labels = {'commandExecution': 'Command', 'fileChange': 'Files',
                      'mcpToolCall': 'Tool call', 'webSearch': 'Search'}
            detail = item.get('command') or item.get('tool') or item.get('query') or ''
            if kind == 'fileChange':
                detail = ', '.join(c.get('path', '') for c in item.get('changes', []))
            status = item.get('status') or ('completed' if completed else 'inProgress')
            status = {'inProgress': 'running', 'completed': 'done'}.get(status, status)
            row['summary'] = labels[kind] + (' · ' + str(detail) if detail else '') + ' · ' + status
            if item.get('exitCode') is not None:
                row['summary'] += ' · exit ' + str(item['exitCode'])
            if 'aggregatedOutput' in item:
                row['output'] = (item.get('aggregatedOutput') or '')[-300000:]
            row['text'] = self.tool_text(row)
        row['done'] = row['done'] or completed

    @staticmethod
    def tool_text(row):
        # Keep noisy command output useful without letting it consume the chat.
        output = row['output'].strip()
        lines = output.splitlines()
        clipped = len(lines) > 8 or len(output) > 1600
        preview = '\n'.join(lines[:8])[:1600]
        return row.get('summary', 'Command · running') + ('\n' + preview if preview else '') + ('\n… output abbreviated' if clipped else '')

    def delta(self, params, tool=False):
        key = params.get('itemId') or ('stream-tool' if tool else 'stream-agent')
        row = self.items.get(key)
        if row is None:
            row = self.add('Tool' if tool else 'Codex', '', key)
        if not row['done']:
            if tool:
                row['output'] = (row['output'] + params.get('delta', ''))[-300000:]
                row['text'] = self.tool_text(row)
            else:
                row['text'] = (row['text'] + params.get('delta', ''))[-300000:]

    def render(self):
        text, spans = '', []
        for row in self.rows:
            start = len(text)
            text += row['role'] + '\n'
            spans.append(('role', start, len(text)))
            body, tags = markdown(row['text']) if row['role'] == 'Codex' else (row['text'], [])
            offset = len(text)
            text += body.rstrip() + '\n\n'
            if row['role'] == 'Tool':
                spans.append(('tool', offset, len(text) - 2))
            spans.extend((tag, offset + a, min(offset + b, len(text))) for tag, a, b in tags)
        return text, spans
