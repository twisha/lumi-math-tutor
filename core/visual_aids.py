"""
K-2 visual aids: emoji counting objects + hop-path number line.
Rendered as inline HTML inside Streamlit st.markdown(..., unsafe_allow_html=True).
"""

import re

_ADD = re.compile(r'\b(\d+)\s*(?:plus|\+)\s*(\d+)\b', re.IGNORECASE)
_SUB = re.compile(r'\b(\d+)\s*(?:minus|subtract[s]?|take\s+away|-)\s*(\d+)\b', re.IGNORECASE)


def _compact(html: str) -> str:
    """Strip newlines so Streamlit's markdown parser doesn't treat indented HTML as a code block."""
    return re.sub(r'\s{2,}', ' ', html.replace('\n', ' ')).strip()


def detect_k2_problem(text: str):
    """Return (a, b, op) for the first K-2-range math problem found, or None.

    Quoted examples (e.g. "5 + 3") are stripped first so that Lumi's
    illustrative examples don't trigger a spurious visual.
    """
    # Remove anything inside straight or curly quotes — these are examples, not problems
    cleaned = re.sub(r'"[^"]*"', '', text)
    cleaned = re.sub(r"'[^']*'", '', cleaned)
    cleaned = re.sub(r'“[^”]*”', '', cleaned)  # curly double quotes

    for pattern, op in [(_ADD, '+'), (_SUB, '-')]:
        m = pattern.search(cleaned)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if 0 <= a <= 20 and 0 <= b <= 20:
                return a, b, op
    return None


def _emoji_group(emoji: str, count: int) -> str:
    """Render count emojis, line-breaking every 5."""
    parts = []
    for i in range(count):
        parts.append(f'<span style="font-size:2.2rem">{emoji}</span>')
        if (i + 1) % 5 == 0 and i < count - 1:
            parts.append('<br>')
    return ''.join(parts) if parts else '<span style="color:#888;font-size:1.1rem">—</span>'


def _hop_path(start: int, hops: list[int], direction: str = 'up') -> str:
    """Render a large hop-by-hop path with color + shape + label differentiation.

    Accessibility: color is never the only signal — start is larger with a ★ and
    a START label; answer position has a dashed border and YOU label.
    This ensures the path is readable for children with color blindness.
    """
    arrow = '→' if direction == 'up' else '←'
    arr_style = 'font-size:1.5rem;color:#888;align-self:flex-start;margin:0 2px;padding-top:18px'

    def labelled(inner_html: str, label: str, label_color: str) -> str:
        return (
            f'<div style="display:inline-flex;flex-direction:column;align-items:center;margin:4px">'
            f'{inner_html}'
            f'<span style="font-size:0.72rem;font-weight:bold;color:{label_color};'
            f'margin-top:3px;letter-spacing:0.04em">{label}</span>'
            f'</div>'
        )

    parts = []

    # Start — larger circle, ★ prefix, orange, "START" label
    start_circle = (
        f'<span style="background:#FF8C00;color:white;border-radius:50%;'
        f'width:66px;height:66px;display:inline-flex;align-items:center;'
        f'justify-content:center;font-size:1.5rem;font-weight:bold;'
        f'border:3px solid rgba(255,255,255,0.4);flex-shrink:0">★{start}</span>'
    )
    parts.append(labelled(start_circle, 'START', '#FF8C00'))

    for n in hops:
        parts.append(f'<span style="{arr_style}">{arrow}</span>')
        hop_circle = (
            f'<span style="background:#FFD54F;color:#1a1a1a;border-radius:50%;'
            f'width:56px;height:56px;display:inline-flex;align-items:center;'
            f'justify-content:center;font-size:1.4rem;font-weight:bold;flex-shrink:0">{n}</span>'
        )
        parts.append(f'<div style="display:inline-flex;flex-direction:column;align-items:center;margin:4px">{hop_circle}<span style="font-size:0.72rem;color:transparent">hop</span></div>')

    # Answer — dashed border, "YOU!" label
    parts.append(f'<span style="{arr_style}">{arrow}</span>')
    answer_circle = (
        f'<span style="background:#333;color:#FFB300;border:3px dashed #FFB300;'
        f'border-radius:50%;width:56px;height:56px;display:inline-flex;align-items:center;'
        f'justify-content:center;font-size:1.6rem;font-weight:bold;flex-shrink:0">?</span>'
    )
    parts.append(labelled(answer_circle, 'YOU!', '#FFB300'))

    return (
        '<div style="display:flex;flex-wrap:wrap;justify-content:center;'
        'align-items:flex-start;padding:10px 4px">'
        + ''.join(parts)
        + '</div>'
    )


def render_k2_visual(a: int, b: int, op: str) -> str:
    """Return full HTML for the K-2 visual aid (emoji objects + hop-path).

    Hop-path colours match the count-on strategy Lumi teaches:
      🟠 orange  = starting number (larger for +, minuend for -)
      🟡 yellow  = each hop counted
      ❓ dashed  = where the child must land (answer intentionally hidden)
    """

    if op == '+':
        start = max(a, b)
        answer = a + b

        objects_html = f"""
        <div style="display:flex;align-items:flex-start;gap:20px;
                    justify-content:center;flex-wrap:wrap">
            <div style="text-align:center">
                <div style="line-height:2.0">{_emoji_group('🍎', a)}</div>
                <div style="font-size:1.4rem;font-weight:bold;color:#FF8A80;margin-top:6px">{a}</div>
            </div>
            <div style="font-size:2.4rem;color:#bbb;padding-top:8px">+</div>
            <div style="text-align:center">
                <div style="line-height:2.0">{_emoji_group('🍊', b)}</div>
                <div style="font-size:1.4rem;font-weight:bold;color:#FFB74D;margin-top:6px">{b}</div>
            </div>
            <div style="font-size:2.4rem;color:#bbb;padding-top:8px">=</div>
            <div style="font-size:3rem;padding-top:4px">❓</div>
        </div>"""

        # Hop path: start at larger, count up by smaller
        hop_numbers = list(range(start + 1, answer)) if answer <= 20 else []
        path_html = _hop_path(start, hop_numbers, direction='up')

    else:  # subtraction
        result = max(a - b, 0)
        kept = _emoji_group('🍎', result)
        faded = ''.join(
            f'<span style="font-size:2.2rem;opacity:0.22">🍎</span>'
            for _ in range(b)
        )
        objects_html = f"""
        <div style="text-align:center">
            <div style="line-height:2.0">{kept}{faded}</div>
            <div style="font-size:1.15rem;color:#ccc;margin-top:8px">
                {a} take away {b} = ❓
            </div>
        </div>"""

        # Hop path: start at minuend, count back to result+1, then ?
        hop_numbers = list(range(a - 1, result, -1))
        path_html = _hop_path(a, hop_numbers, direction='down')

    legend = (
        '<div style="font-size:0.95rem;color:#bbb;margin-top:6px">'
        '★ START &nbsp;·&nbsp; hop circles &nbsp;·&nbsp; ? YOU find it!'
        '</div>'
    )

    return _compact(f"""
    <div style="background:#2a2a2a;border:2px dashed #FFB300;border-radius:16px;
                padding:18px 22px;margin:4px 0 14px;text-align:center">
        <div style="font-size:0.85rem;color:#FFB300;letter-spacing:0.06em;
                    text-transform:uppercase;margin-bottom:12px">🎨 Visual Helper</div>
        {objects_html}
        <div style="border-top:1px solid #444;margin-top:14px;padding-top:10px">
            {path_html}
            {legend}
        </div>
    </div>""")
