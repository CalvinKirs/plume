// Converts Gmail's compose HTML to plain text. Quoted replies become lines that start with "> ",
// which is what mailing lists and PonyMail expect.
(function (root) {
  const P = (root.Plume = root.Plume || {});
  const BLOCK = new Set(['DIV', 'P', 'LI', 'UL', 'OL', 'TABLE', 'TR', 'PRE', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6']);

  function render(node) {
    if (node.nodeType === 3) return node.nodeValue.replace(/\u00a0/g, ' ').replace(/[\u200b\u200c\u200d\ufeff]/g, '');
    if (node.nodeType !== 1) return '';
    const tag = node.tagName;
    if (tag === 'BR') return '\n';
    if (tag === 'STYLE' || tag === 'SCRIPT') return '';
    let inner = '';
    for (const child of node.childNodes) {
      if (child.tagName === 'BLOCKQUOTE' && inner && !inner.endsWith('\n')) inner += '\n';
      inner += render(child);
    }
    if (tag === 'BLOCKQUOTE') {
      const lines = inner.replace(/^\n+|\n+$/g, '').split('\n');
      return lines.map((l) => (l ? '> ' + l : '>')).join('\n') + '\n';
    }
    if (BLOCK.has(tag)) return inner.endsWith('\n') ? inner : inner + '\n';
    return inner;
  }

  function domToText(el) {
    return render(el).replace(/^\n+/, '').replace(/\n+$/, '');
  }

  P.domToText = domToText;
  if (typeof module !== 'undefined') module.exports = { domToText };
})(typeof globalThis !== 'undefined' ? globalThis : this);
