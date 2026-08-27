const LIMIT = 30;
// Usa Flask incluso si el archivo se abre desde Live Server, VS Code o file://.
const API_BASE = window.location.port === '5000' ? '' : 'http://127.0.0.1:5000';
const state = { level: 1, variables: null, questions: [], timerId: null, seconds: LIMIT, history: [], phase2Failures: 0, phase1Objective: '' };
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

function setScreen(title, sectionTitle, description) {
  stopTimer();
  conversation.innerHTML = '';
  interaction.innerHTML = '';
  $('.sidebar h1').textContent = sectionTitle;
  $('.sidebar-copy').textContent = description;
  $('.topbar h2').textContent = title;
  document.title = `${sectionTitle} | Data Tutor`;
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
  state.phase1Objective = question;
  $('#session-status').textContent = 'Consulta definida';
  addMessage('Fase 1 completada', `La consulta seleccionada es: ${question}\n\nYa puedes usarla como punto de partida para el análisis y las visualizaciones.`, 'success');
  const button = document.createElement('button');
  button.textContent = 'Continuar a la Fase 2: planear';
  button.addEventListener('click', startPhase2);
  interaction.append(button);
}

function phase2Result(text) {
  const porcentaje = Number(text.match(/PORCENTAJE_CUMPLIMIENTO\s*:\s*\[?\s*(\d{1,3})/i)?.[1] ?? 0);
  const estado = text.match(/ESTADO\s*:\s*\[([^\]]+)\]/i)?.[1]?.trim() || 'ERROR';
  const nivel = text.match(/NIVEL_ACTIVADO\s*:\s*\[([^\]]+)\]/i)?.[1]?.trim() || 'No identificado';
  const feedback = text.match(/FEEDBACK_GUIA\s*:\s*\[([\s\S]*?)\]\s*(?:OPCION_CORRECTA|$)/i)?.[1]?.trim() || text;
  const correctOption = Number(text.match(/OPCION_CORRECTA\s*:\s*\[?\s*([1-3])/i)?.[1] ?? 0);
  return { porcentaje: Math.min(100, porcentaje), estado, nivel, feedback, correctOption };
}

function phase2Alternatives(feedback) {
  return feedback.split('\n').map((line) => line.match(/^\s*([1-3])[.)]\s*(.+)$/))
    .filter(Boolean).map((match) => ({ number: Number(match[1]), text: match[2].trim() }));
}

async function choosePhase2Alternative(option, result) {
  if (option.number !== result.correctOption) {
    addMessage('Alternativa no adecuada', 'Esta opción no aborda correctamente todas las alertas. Se prescribirá el plan final.', 'warning');
    state.phase2Failures = 2;
    await evaluateStrategy('El usuario eligió una alternativa no adecuada del Nivel 3.');
    return;
  }
  interaction.innerHTML = '';
  addMessage('Alternativa correcta', option.text, 'success');
  try {
    const { respuesta } = await api('/api/fase2/explicar-alternativa-correcta', {
      method: 'POST', body: JSON.stringify({ alternativa: option.text, objetivo_fase1: state.phase1Objective }),
    });
    addMessage('¿Por qué es correcta?', respuesta, 'success');
    addHistory('Fase 2: alternativa correcta explicada');
  } catch (error) { addMessage('No se pudo generar la explicación', error.message, 'warning'); }
  $('#session-status').textContent = 'Lista para Fase 3';
  addMessage('Fase 2 completada', 'La alternativa elegida deja el dataset preparado para la siguiente fase.', 'success');
}

function showPhase2Alternatives(result) {
  const options = phase2Alternatives(result.feedback);
  if (options.length !== 3 || !result.correctOption) {
    addMessage('Error al generar alternativas', 'No se recibieron tres alternativas válidas. Intenta nuevamente.', 'warning');
    renderStrategyForm();
    return;
  }
  interaction.innerHTML = '';
  addMessage('Nivel 3 · Elige una alternativa', 'Selecciona una opción. Después de acertar se explicará por qué es adecuada.');
  const box = document.createElement('section'); box.className = 'suggestions';
  box.innerHTML = '<strong>Responde con una alternativa</strong><div class="suggestion-grid"></div>';
  options.forEach((option) => {
    const button = document.createElement('button'); button.className = 'suggestion';
    button.innerHTML = `<b>OPCIÓN ${option.number}</b>${option.text}`;
    button.addEventListener('click', () => choosePhase2Alternative(option, result));
    box.querySelector('.suggestion-grid').append(button);
  });
  interaction.append(box);
}

function renderStrategyForm() {
  interaction.innerHTML = $('#strategy-template').innerHTML;
  $('.strategy-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const proposal = $('#strategy-input').value.trim();
    if (proposal) await evaluateStrategy(proposal);
  });
  const back = document.createElement('button');
  back.type = 'button'; back.className = 'secondary'; back.textContent = 'Volver y reiniciar Fase 1';
  back.addEventListener('click', restartPhase1);
  interaction.append(back);
  startTimer(handleStrategyTimeout);
}

function listaContexto(items, etiquetaVacia) {
  const entries = Object.entries(items || {});
  return entries.length
    ? entries.map(([name, value]) => `- ${name}: ${value}`).join('\n')
    : `- ${etiquetaVacia}`;
}

function textoSaludDataset(calidad, escalado) {
  const bloques = [];
  if (Object.entries(calidad.nulos || {}).length) {
    bloques.push('🔴 Valores nulos detectados:', Object.entries(calidad.nulos).map(([name, count]) =>
      `- ${name}: ${count} nulos (${calidad.nulos_porcentaje?.[name] ?? 0}%)`).join('\n'));
  }
  if (Object.entries(calidad.outliers || {}).length) {
    bloques.push('⚠️ Outliers detectados por IQR:', listaContexto(calidad.outliers, ''));
  }
  const variablesEscalado = escalado.variables_numericas_evaluadas?.join(', ') || 'ninguna';
  const temporales = escalado.columnas_temporales_a_transformar?.join(', ') || 'ninguna';
  if (escalado.amerita_escalado_si_se_combinan_variables) {
    bloques.push('📏 Normalización / escalado:', `- Variables evaluadas: ${variablesEscalado}`, `- ${escalado.interpretacion}`);
  }
  if (escalado.requiere_transformacion_temporal) {
    bloques.push('🗓️ Transformación temporal:', `- Columnas: ${temporales}`, `- ${escalado.nota_transformacion}`);
  }
  return bloques.length ? bloques.join('\n\n') : 'No se detectaron alertas de calidad o preparación para mostrar.';
}

async function startPhase2() {
  setScreen('Planifica la preparación de tus datos', 'Estrategia, calidad y preparación', 'Define una estrategia segura para limpiar, escalar o transformar los datos.');
  document.querySelectorAll('.levels li').forEach((item) => item.classList.remove('active'));
  state.phase2Failures = 0;
  $('#session-status').textContent = 'Fase 2 activa';
  addMessage('Fase 2 · Estrategia, calidad y preparación', 'Describe cómo prepararías el dataset. Python aporta el diagnóstico de calidad y el tutor solo evalúa si tu estrategia es segura y coherente.');
  try {
    const [calidad, escalado] = await Promise.all([
      api('/api/diagnostico-calidad'),
      api(`/api/analisis-escalado-transformacion?objetivo=${encodeURIComponent(state.phase1Objective)}`),
    ]);
    addMessage('Salud del dataset', textoSaludDataset(calidad, escalado));
  } catch (error) {
    addMessage('No se pudo cargar la salud del dataset', error.message, 'warning');
  }
  renderStrategyForm();
}

async function evaluateStrategy(proposal) {
  stopTimer();
  interaction.classList.add('loading');
  addMessage('Tu estrategia', proposal);
  try {
    const { respuesta } = await api('/api/fase2/evaluar-estrategia', {
      method: 'POST', body: JSON.stringify({
        propuesta: proposal,
        intento_fallido: state.phase2Failures,
        objetivo_fase1: state.phase1Objective,
        nivel_forzado: state.phase2Failures === 1 ? 'NIVEL 3: Recomendar Alternativas' : null,
      }),
    });
    const result = phase2Result(respuesta);
    const success = result.estado.toUpperCase() === 'EXITO' || result.porcentaje === 100;
    if (!/NIVEL 3/i.test(result.nivel)) {
      addMessage(success ? 'Estrategia aprobada' : result.nivel, result.feedback, success ? 'success' : 'warning');
    }
    addHistory(`Fase 2: ${success ? 'estrategia aprobada' : result.nivel}`);
    if (success) {
      interaction.innerHTML = '';
      $('#session-status').textContent = 'Lista para Fase 3';
      addMessage('Fase 2 completada', 'Tu estrategia metodológica es viable. Puedes pasar a la Fase 3 de ejecución técnica.', 'success');
      return;
    }
    if (result.porcentaje >= 50) {
      addMessage('Estrategia parcialmente completa', `Cumplimiento estimado: ${result.porcentaje}%\n\nCompleta los elementos señalados y vuelve a enviar tu estrategia.`, 'warning');
      renderStrategyForm();
      return;
    }
    state.phase2Failures += 1;
    if (/NIVEL 3/i.test(result.nivel)) {
      showPhase2Alternatives(result);
    } else if (/NIVEL 4/i.test(result.nivel)) {
      interaction.innerHTML = '';
      $('#session-status').textContent = 'Plan prescrito';
      addMessage('Nivel 4 · Tu plan será', result.feedback, 'success');
      addMessage('Fase 2 completada', 'El plan prescrito deja el dataset preparado para la siguiente fase.', 'success');
    } else {
      renderStrategyForm();
    }
  } catch (error) { addMessage('No se pudo evaluar la estrategia', error.message, 'warning'); }
  finally { interaction.classList.remove('loading'); }
}

function handleStrategyTimeout() {
  addMessage('Tiempo agotado', 'No se recibió una estrategia dentro de los 30 segundos. El tutor te orientará con el diagnóstico disponible.', 'warning');
  evaluateStrategy('No se recibió una propuesta metodológica dentro del tiempo establecido.');
}

function restartPhase1() {
  state.phase2Failures = 0;
  state.phase1Objective = '';
  $('#session-status').textContent = 'Variables cargadas';
  setScreen('Explora tu CSV con propósito', 'Comprensión del dataset', 'Formula una duda y recibe orientación basada en las variables reales del CSV.');
  setLevel(1);
  addMessage('Nivel 1 · Preguntar y validar', 'Escribe tu pregunta o duda para analizar el CSV. El tutor verificará si se puede responder con las variables disponibles.');
  showQuestionForm(1);
}

async function init() {
  state.history = JSON.parse(localStorage.getItem('fase1_historial') || '[]');
  $('#history').innerHTML = state.history.map((item) => `<li><b>${item.time}</b> — ${item.label}</li>`).join('');
  $('#history-toggle').addEventListener('click', () => $('#history').classList.toggle('is-hidden'));
  try {
    state.variables = await api('/api/taxonomia-variables');
    $('#session-status').textContent = 'Variables cargadas';
    restartPhase1();
  } catch (error) { $('#session-status').textContent = 'Sin conexión'; addMessage('No se pudo iniciar', `${error.message}\nInicia Flask con: python3 app.py`, 'warning'); }
}

init();
