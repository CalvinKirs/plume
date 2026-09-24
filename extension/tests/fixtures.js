const { JSDOM } = require('jsdom');

// Hand-built approximation of Gmail's compose markup. Not captured from live Gmail:
// keep it in sync with docs/selectors.md when the real markup is checked.
function composeHtml({ send = 'Send', discard = 'Discard draft', subject = 'Re: [VOTE] release', body, split = false } = {}) {
  const open = split ? '</div><div class="inner">' : '';
  return `
  <div class="compose"><div class="hdr">
    <div name="to"><span email="dev@apache.org" data-hovercard-id="dev@apache.org"></span><input type="hidden" name="to" value="dev@apache.org, Bob &lt;bob@example.org&gt;"></div>
    <div name="cc"><span email="carol@example.org"></span></div>
    <div name="bcc"></div>
    <input name="subjectbox" value="${subject}">
    ${open}
    <div role="textbox" g_editable="true" aria-label="Message Body">${body || '<div>+1</div><div><br></div><div>thanks</div>'}</div>
    <table><tr>
      <td><div role="button" class="T-I aoO" data-tooltip="${send}">${send}</div></td>
      <td><div role="button" class="og" data-tooltip="${discard}"></div></td>
    </tr></table>
  </div></div>`;
}

function page(html) {
  return new JSDOM(`<body>${html}</body>`).window.document;
}

module.exports = { composeHtml, page };
