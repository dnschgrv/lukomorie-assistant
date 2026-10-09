(() => {
  if (window.__lukomorieAiLoaded) return;
  window.__lukomorieAiLoaded = true;
  const script = document.currentScript;
  const api = script?.dataset.api || new URL('/api/chat', script?.src || location.href).href;
  const css = new URL('/widget.css', script?.src || location.href).href;
  const link = document.createElement('link'); link.rel = 'stylesheet'; link.href = css; document.head.appendChild(link);

  const root = document.createElement('div'); root.id = 'luk-ai';
  root.innerHTML = `
    <button class="luk-launch" aria-label="Открыть чат с ИИ-ассистентом"><span class="luk-ai-mark">ИИ</span><span>Задать вопрос</span></button>
    <section class="luk-panel" role="dialog" aria-label="ИИ-ассистент Лукоморья" aria-hidden="true">
      <header><div><b>Лукоморье</b><small><span></span> ИИ-ассистент</small></div><button class="luk-close" aria-label="Закрыть">×</button></header>
      <div class="luk-notice">Не собираем и не сохраняем персональные данные — пожалуйста, не указывайте их в сообщениях. Ответы носят консультативный характер и не являются медицинским назначением. Точную информацию уточняйте: <a href="tel:+73536343356">8 (35363) 4-33-56</a>, <a href="tel:88005002840">8 (800) 500-28-40</a>.</div>
      <div class="luk-messages" aria-live="polite"><div class="luk-msg bot">Здравствуйте! Я ИИ-ассистент санатория-профилактория «Лукоморье». Могу рассказать об услугах, процедурах и ценах по нашей базе знаний. Чем помочь?</div></div>
      <form><textarea rows="1" maxlength="1500" placeholder="Например: сколько стоит соляная камера?" aria-label="Ваш вопрос"></textarea><button type="submit" aria-label="Отправить">➤</button></form>
      <div class="luk-foot">Ответ подготовлен ИИ по базе санатория</div>
    </section>`;
  document.body.appendChild(root);
  const launch = root.querySelector('.luk-launch'), panel = root.querySelector('.luk-panel'), close = root.querySelector('.luk-close');
  const form = root.querySelector('form'), input = root.querySelector('textarea'), messages = root.querySelector('.luk-messages');
  const history = [];
  const toggle = open => { panel.classList.toggle('open', open); panel.setAttribute('aria-hidden', String(!open)); if (open) input.focus(); };
  launch.onclick = () => toggle(!panel.classList.contains('open')); close.onclick = () => toggle(false);
  const add = (text, type) => { const el=document.createElement('div'); el.className=`luk-msg ${type}`; el.textContent=text; messages.appendChild(el); messages.scrollTop=messages.scrollHeight; return el; };
  const addTyping = () => {
    const el=document.createElement('div');
    el.className='luk-msg bot luk-typing';
    el.setAttribute('role','status');
    el.setAttribute('aria-label','ИИ-ассистент печатает');
    el.innerHTML='<span class="luk-typing-label">Ассистент печатает</span><span class="luk-typing-dots" aria-hidden="true"><i></i><i></i><i></i></span>';
    messages.appendChild(el); messages.scrollTop=messages.scrollHeight; return el;
  };
  form.addEventListener('submit', async e => {
    e.preventDefault(); const text=input.value.trim(); if (!text) return; input.value=''; add(text,'user');
    const wait=addTyping(); form.classList.add('busy');
    try {
      const controller=new AbortController(); const timer=setTimeout(()=>controller.abort(),30000);
      const res=await fetch(api,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,history:history.slice(-6)}),signal:controller.signal});
      clearTimeout(timer);
      const data=await res.json(); wait.remove(); add(data.answer || 'Не удалось получить ответ.','bot');
      history.push({role:'user',content:text},{role:'assistant',content:data.answer || ''});
    } catch (_) { wait.remove(); add('Сервис временно недоступен. Позвоните: 8 (35363) 4-33-56 или 8 (800) 500-28-40.','bot'); }
    finally { form.classList.remove('busy'); input.focus(); }
  });
  input.addEventListener('keydown', e => { if (e.key==='Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); } });
})();
