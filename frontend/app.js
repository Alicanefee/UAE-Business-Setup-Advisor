// SSE client for /v1/chat/stream. All content is inserted with textContent,
// never innerHTML, so record text cannot inject markup.

const chat = document.getElementById('chat');
const form = document.getElementById('composer');
const msg = document.getElementById('msg');
const renew = document.getElementById('renew');
const docs = document.getElementById('docs');

let sessionId = null;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function append(node) {
  chat.appendChild(node);
  chat.scrollTop = chat.scrollHeight;
}

function source(key) {
  return el('span', 'src', ` [${key}]`);
}

function renderResult(answer) {
  const card = el('div', 'card');
  card.appendChild(el('h2', null, answer.title));

  const dl = el('dl');
  for (const row of answer.summary) {
    dl.appendChild(el('dt', null, row.label));
    const dd = el('dd', null, row.value);
    dd.appendChild(source(row.source));
    dl.appendChild(dd);
  }
  card.appendChild(dl);

  for (const section of answer.sections) {
    card.appendChild(el('h3', null, section.heading));
    const ul = el('ul');
    for (const item of section.items) {
      const li = el('li', null, item.text);
      li.appendChild(source(item.source));
      ul.appendChild(li);
    }
    card.appendChild(ul);
  }
  card.appendChild(el('div', 'disclaimer', answer.disclaimer));
  append(card);
}

function handle(type, data) {
  switch (type) {
    case 'session': sessionId = data.session_id; break;
    case 'question': append(el('div', 'bubble bot', data.text)); break;
    case 'result': renderResult(data.answer); break;
    case 'abstain': append(el('div', 'bubble warn', data.text)); break;
    case 'error': append(el('div', 'bubble warn', 'Something went wrong. Please try again.')); break;
  }
}

async function send(text) {
  const documents = renew.checked
    ? docs.value.split(';').map(s => s.trim()).filter(Boolean)
    : [];
  const res = await fetch('/v1/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      message: text,
      mode: renew.checked ? 'renew' : 'new',
      documents,
    }),
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop();
    for (const raw of events) {
      const lines = raw.split('\n');
      const type = (lines.find(l => l.startsWith('event:')) || '').slice(6).trim();
      const dataLine = lines.find(l => l.startsWith('data:')) || 'data: {}';
      handle(type, JSON.parse(dataLine.slice(5)));
    }
  }
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const text = msg.value.trim();
  if (!text && !(renew.checked && docs.value.trim())) return;
  append(el('div', 'bubble user', text || docs.value.trim()));
  msg.value = '';
  try {
    await send(text);
  } catch {
    handle('error', {});
  }
});

renew.addEventListener('change', () => docs.classList.toggle('hidden', !renew.checked));

document.getElementById('reset').addEventListener('click', () => {
  sessionId = null;
  chat.replaceChildren(chat.firstElementChild);
});
