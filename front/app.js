const LIMIT = 30;
// Usa Flask incluso si el archivo se abre desde Live Server, VS Code o file://.
const API_BASE = window.location.port === '5000' ? '' : 'http://127.0.0.1:5000';
const state = { level: 1, variables: null, questions: [], timerId: null, seconds: LIMIT, history: [] };
const $ = (selector) => document.querySelector(selector);
const conversation = $('#conversation');
const interaction = $('#interaction');
const timer = $('#timer strong');

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'No se pudo completar la solicitud.');
  return data;
}

function addMessage(title, text, kind = 'system') {
  const card = document.createElement('article');
  card.className = `message ${kind}`;
  card.innerHTML = `<h3>${title}</h3><p></p>`;
  card.querySelector('p').textContent = text;
  conversation.append(card);
  card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function addHistory(label) {
  state.history.push({ time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), label });
  localStorage.setItem('fase1_historial', JSON.stringify(state.history));
  $('#history').innerHTML = state.history.map((item) => `<li><b>${item.time}</b> — ${item.label}</li>`).join('');
}

function setLevel(level) {
  state.level = level;
  document.querySelectorAll('.levels li').forEach((item) => item.classList.toggle('active', Number(item.dataset.level) === level));
}

function stopTimer() { clearInterval(state.timerId); state.timerId = null; }
function startTimer(onTimeout) {
  stopTimer(); state.seconds = LIMIT;
  timer.textContent = `00:${String(LIMIT).padStart(2, '0')}`;
  state.timerId = setInterval(() => {
    state.seconds -= 1;
    timer.textContent = `00:${String(Math.max(0, state.seconds)).padStart(2, '0')}`;
    if (state.seconds <= 0) { stopTimer(); onTimeout(); }
  }, 1000);
}

function showQuestionForm(level) {
  interaction.innerHTML = $('#question-template').innerHTML;
  const form = $('.question-form');
  form.addEventListener('submit', async (event) => {
    event.preventDefault(); stopTimer();
    const question = $('#question-input').value.trim();
    if (question) await validateQuestion(question, level);
  });
  startTimer(() => handleQuestionFailure(level, '⏱️ No recibí una pregunta dentro del tiempo disponible.'));
}

async function validateQuestion(question, level) {
  interaction.classList.add('loading');
  addMessage('Tu pregunta', question);
  try {
    const { respuesta } = await api('/api/validar-pregunta', { method: 'POST', body: JSON.stringify({ pregunta: question }) });
    const valid = respuesta.trim().startsWith('✅');
    addMessage(valid ? 'Pregunta viable' : 'Retroalimentación del tutor', respuesta, valid ? 'success' : 'warning');
    addHistory(`Nivel ${level}: ${valid ? 'pregunta viable' : 'pregunta por mejorar'}`);
    if (valid) finish(question); else handleQuestionFailure(level);
  } catch (error) { addMessage('Error de conexión', error.message, 'warning'); }
  finally { interaction.classList.remove('loading'); }
}

async function handleQuestionFailure(level, timeoutMessage = '') {
  if (timeoutMessage) addMessage('Tiempo agotado', timeoutMessage, 'warning');
  if (level === 1) await showLevel2(); else await showLevel3();
}

async function showLevel2() {
  setLevel(2); interaction.innerHTML = '';
  addMessage('Nivel 2 · Orientar con las variables', 'Estas son las variables disponibles. Úsalas para reformular una pregunta que pueda responderse con el dataset.');
  renderVariables();
  try {
    const { respuesta } = await api('/api/describir-variables');
    addMessage('¿Qué significan las variables?', respuesta);
  } catch (error) { addMessage('No fue posible describir las variables', error.message, 'warning'); }
  showQuestionForm(2);
}

function renderVariables() {
  const wrap = document.createElement('div'); wrap.className = 'variables';
  Object.entries(state.variables).forEach(([type, names]) => {
    const group = document.createElement('div'); group.className = 'variable-group';
    group.innerHTML = `<strong>${type}</strong><span>${names.join(', ') || 'Sin variables'}</span>`;
    wrap.append(group);
  });
  conversation.append(wrap);
}

function parseSuggestions(text) {
  const lines = text.split('\n'); const items = [];
  let current = null;
  lines.forEach((line) => {
    const match = line.match(/^\s*([1-3])[.)]\s*(.+)$/);
    if (match) { current = { question: match[2].trim(), reason: '' }; items.push(current); }
    else if (current && /motivo/i.test(line)) current.reason = line.replace(/^\s*motivo\s*:\s*/i, '').trim();
  });
  return items.slice(0, 3);
}

async function showLevel3() {
  setLevel(3); interaction.innerHTML = '';
  addMessage('Nivel 3 · Preguntas sugeridas', 'Te propongo tres consultas viables. Cada una indica por qué puede ser útil. Elige una antes de que termine el tiempo.');
  try {
    const { respuesta } = await api('/api/preguntas-sugeridas');
    const suggestions = parseSuggestions(respuesta);
    if (suggestions.length !== 3) throw new Error('El LLM no devolvió tres sugerencias en el formato esperado.');
    state.questions = suggestions;
    const box = document.createElement('section'); box.className = 'suggestions';
    box.innerHTML = '<strong>Elige una pregunta</strong><div class="suggestion-grid"></div>';
    suggestions.forEach((item, index) => {
      const button = document.createElement('button'); button.className = 'suggestion';
      button.innerHTML = `<b>OPCIÓN 0${index + 1}</b>${item.question}<small>${item.reason || 'Pregunta formulada según las variables disponibles.'}</small>`;
      button.addEventListener('click', () => { stopTimer(); addHistory('Nivel 3: pregunta elegida por el usuario'); addMessage('Pregunta elegida', item.question, 'success'); finish(item.question); });
      box.querySelector('.suggestion-grid').append(button);
    });
    interaction.append(box);
    startTimer(showLevel4);
  } catch (error) { addMessage('No se pudieron generar sugerencias', error.message, 'warning'); }
}

async function showLevel4() {
  setLevel(4); interaction.innerHTML = '';
  addMessage('Nivel 4 · Prescribir una ruta', 'Como no hubo una selección, el tutor decidirá la pregunta más útil para continuar.');
  try {
    const { respuesta } = await api('/api/prescribir-pregunta', { method: 'POST', body: JSON.stringify({ preguntas: state.questions.map((item) => item.question) }) });
    const match = respuesta.match(/ELECCION\s*:\s*([1-3])/i);
    if (!match) throw new Error('El LLM no devolvió una elección válida.');
    const chosen = state.questions[Number(match[1]) - 1].question;
    addMessage('Pregunta prescrita', `${chosen}\n\n${respuesta}`, 'success');
    addHistory('Nivel 4: pregunta prescrita por el LLM');
    finish(chosen);
  } catch (error) { addMessage('No se pudo prescribir una pregunta', error.message, 'warning'); }
}

function finish(question) {
  stopTimer(); interaction.innerHTML = '';
  $('#session-status').textContent = 'Consulta definida';
  addMessage('Fase 1 completada', `La consulta seleccionada es: ${question}\n\nYa puedes usarla como punto de partida para el análisis y las visualizaciones.`, 'success');
}

async function init() {
  state.history = JSON.parse(localStorage.getItem('fase1_historial') || '[]');
  $('#history').innerHTML = state.history.map((item) => `<li><b>${item.time}</b> — ${item.label}</li>`).join('');
  $('#history-toggle').addEventListener('click', () => $('#history').classList.toggle('is-hidden'));
  try {
    state.variables = await api('/api/taxonomia-variables');
    $('#session-status').textContent = 'Variables cargadas';
    setLevel(1);
    addMessage('Nivel 1 · Preguntar y validar', 'Escribe tu pregunta o duda para analizar el CSV. El tutor verificará si se puede responder con las variables disponibles.');
    showQuestionForm(1);
  } catch (error) { $('#session-status').textContent = 'Sin conexión'; addMessage('No se pudo iniciar', `${error.message}\nInicia Flask con: python3 app.py`, 'warning'); }
}

init();
