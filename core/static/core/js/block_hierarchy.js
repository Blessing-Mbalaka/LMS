document.addEventListener('DOMContentLoaded', () => {
  const blocks = Array.from(document.querySelectorAll('.block'));
  const mapByQn = {}, parents = {}, childrenCount = {};

  blocks.forEach(b => {
    const qn = b.dataset.qn;
    if (qn) mapByQn[qn] = b;
  });

  blocks.forEach(b => {
    if (b.dataset.type !== 'question') return;
    const parts = (b.dataset.qn || "").split('.');
    if (parts.length < 2) return;
    const parentKey = parts.slice(0, -1).join('.');
    const parentEl = mapByQn[parentKey];
    if (!parentEl) return;

    parents[b.dataset.id] = parentEl.dataset.id;
    childrenCount[parentEl.dataset.id] = (childrenCount[parentEl.dataset.id] || 0) + 1;

    let wrap = parentEl.querySelector('.children');
    if (!wrap) {
      wrap = document.createElement('div');
      wrap.className = 'children ms-4 mt-2';
      parentEl.appendChild(wrap);
    }
    wrap.appendChild(b);
  });

  blocks.forEach(b => {
    const id = b.dataset.id, header = b.querySelector('.d-flex') || b;
    let badge;
    if (childrenCount[id]) {
      badge = document.createElement('span');
      badge.textContent = `Parent of ${childrenCount[id]}`;
      badge.className = 'badge bg-primary text-white ms-2';
    } else if (parents[id]) {
      const pEl = document.querySelector(`.block[data-id="${parents[id]}"]`);
      const pQn = pEl?.dataset.qn || '';
      badge = document.createElement('span');
      badge.textContent = `Child of ${pQn}`;
      badge.className = 'badge bg-secondary text-white ms-2';
    }
    if (badge) header.appendChild(badge);
  });

  const form = document.getElementById('blocks-form');
  if (form) {
    form.addEventListener('submit', () => {
      const out = Array.from(document.querySelectorAll('.block')).map(b => {
        const type = b.dataset.type || '';
        const id = b.dataset.id;
        const text = b.querySelector('.block-text')?.value?.trim()
                  || b.querySelector('.block-text')?.textContent?.trim() || '';

        const content = Array.from(b.querySelectorAll('.block-content')).map(el => {
          if (el.tagName === 'IMG') {
            return { type: 'figure', data_uri: el.src };
          }
          if (el.tagName === 'TABLE') {
            const rows = Array.from(el.querySelectorAll('tr')).map(row =>
              Array.from(row.querySelectorAll('td')).map(cell => cell.innerText.trim())
            );
            return { type: 'table', rows: rows };
          }
          if (el.closest('.border.bg-light')) {
            return { type: 'case_study', text: el.innerText.trim() };
          }
          return { type: 'question_text', text: el.innerText.trim() };
        });

        return {
          id: id,
          number: b.dataset.qn || '',
          type: type,
          marks: b.dataset.marks || '',
          parent_id: parents[id] || null,
          text: text,
          content: content,
          ...(type === 'figure' ? { data_uri: b.querySelector('img')?.src || '' } : {})
        };
      });

      document.getElementById('nodes-json').value = JSON.stringify(out);
    });
  }
});
