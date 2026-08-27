# 🧠 Arquitectura del Motor de Guidance Contextual

El **Motor de Guidance** opera de manera transversal a lo largo de las cinco fases del ciclo analítico (*Problema, Plan, Datos, Análisis y Conclusión*). Su propósito fundamental es monitorear la autonomía del usuario, detectar de manera oportuna brechas cognitivas o metodológicas, y dosificar el nivel de apoyo pedagógico de forma progresiva.

---

## ⚙️ 1. Lógica y Reglas Operativas del Motor

El motor opera como un sistema de toma de decisiones adaptativo que regula la interacción entre el usuario y las fases analíticas mediante las siguientes reglas internas:

### A. El Ciclo de Inicialización y el Contexto Global
*   **Ingreso al Estado Activo (`[ INICIO DE FASE ACTIVA ]`)**: El sistema identifica la etapa analítica actual del usuario y carga las directrices correspondientes.
*   **Inyección de Entradas Contextuales**: El núcleo de decisión recopila en tiempo real dos variables de estado clave:
    1. *Las características del dataset o problema actual* (para calibrar la complejidad técnica).
    2. *El historial acumulativo de acciones* (la memoria de interacciones previas, aciertos y niveles de ayuda consumidos).
*   **Temporizador de Fricción**: Se despliega el estímulo inicial de la fase y se arranca un cronómetro interno para medir el tiempo que tarda el usuario en dar una respuesta autónoma.

### B. La Regla de Decisión 0: La Ruta del Éxito (Sin Timeout)
Una vez iniciado el temporizador, el motor evalúa si el usuario ejecuta una acción autónoma a tiempo:
*   **Condición (SÍ)**: Si el usuario responde o resuelve el requerimiento de forma independiente *antes* de que expire el tiempo límite.
*   **Comportamiento del Sistema**: 
    *   **Omisión de Escalada**: El motor valida que el usuario cuenta con el dominio necesario, bloqueando y omitiendo por completo los niveles de ayuda (Niveles 1, 2 y 3).
    *   **Registro Directo**: La acción autónoma se captura y se envía de inmediato al registro histórico.
    *   **Continuidad**: Se da por superada la fase y se emite la señal para avanzar a la siguiente etapa del análisis.

### C. La Regla de Escalada Gradual (Ante Demoras o Timeout)
Si el temporizador expira sin aportes del usuario (**Respuesta NO / Timeout**), el sistema interpreta una brecha cognitiva o bloqueo, activando un andamiaje progresivo:
*   🎯 **Nivel 1 (Orientar + Explicar / Brecha Leve)**: Aplica la regla de *señalar qué observar*. El sistema filtra el contexto y muestra pistas sobre qué variables o métricas atender sin dar la respuesta directa.
*   🔀 **Nivel 2 (Dirigir + Explicar / Bloqueo Persistente)**: Aplica la regla de *recomendar alternativas*. Si el Nivel 1 falla, el sistema ofrece rutas metodológicas alternas justificando el impacto de cada opción.
*   ✅ **Nivel 3 (Prescribir + Explicar / Fricción Crítica)**: Aplica la regla de *acción con confirmación*. Ante un bloqueo total, el sistema formula o ejecuta una solución técnica directa solicitando confirmación explícita y explicando su fundamento.

### D. Convergencia y Cierre del Ciclo
Independientemente de la ruta tomada (la autónoma directa o cualquiera de los niveles de ayuda), **todas las interacciones convergen obligatoriamente en un único punto**: el registro en el historial. Esto actualiza la memoria de la sesión, valida el modelo mediante retroalimentación y da la orden de continuar el ciclo.

---

## 📊 2. Diagrama de Flujo del Motor (Graphviz)

Puedes renderizar este flujo copiando el siguiente código en plataformas compatibles como [GraphvizOnline](https://dreampuf.github.io/GraphvizOnline/):

```dot
digraph G {
    rankdir=TB;
    size="10,10";
    fontname="Helvetica";
    
    node [fontname="Helvetica", shape="box", style="rounded,filled", fillcolor="#F5F7FA", color="#2B6CB0", margin="0.2"];

    Entradas [label="ENTRADAS CONTEXTUALES GLOBALES\n• Características del dataset / problema\n• Historial acumulativo de acciones", fillcolor="#E2E8F0", shape="folder"];
    
    Inicio [label="[ INICIO DE FASE ACTIVA ]\n(Fases: Problema | Plan | Datos | Análisis | Conclusión)", fillcolor="#3182CE", fontcolor="white"];
    
    Estimulo [label="Despliegue de Estímulo / Mensaje Inicial\n[ Inicialización del Temporizador de Fricción ]"];
    
    Check0 [label="¿El usuario ejecuta una acción\nautónoma a tiempo?", shape="diamond", fillcolor="#FEFCBF"];
    
    Nivel1 [label="🎯 NIVEL 1: ORIENTAR + EXPLICAR\n• Estado: Detección de brecha leve\n• Aplicación regla: Señalar qué observar", fillcolor="#EDF2F7"];
    Check1 [label="¿El usuario responde al Nivel 1?", shape="diamond", fillcolor="#FEFCBF"];
    
    Nivel2 [label="🔀 NIVEL 2: DIRIGIR + EXPLICAR\n• Estado: Persistencia de brecha / Bloqueo\n• Aplicación regla: Recomendar alternativas", fillcolor="#EDF2F7"];
    Check2 [label="¿El usuario responde al Nivel 2?", shape="diamond", fillcolor="#FEFCBF"];
    
    Nivel3 [label="✅ NIVEL 3: PRESCRIBIR + EXPLICAR\n• Estado: Brecha crítica / Fricción máxima\n• Aplicación regla: Ejecución con confirmación", fillcolor="#EDF2F7"];
    
    Historial [label="REGISTRO EN EL HISTORIAL DE ACCIONES", fillcolor="#C6F6D5", color="#38A169"];
    
    Retro [label="[ RETROALIMENTACIÓN ]\nValidación del modelo y actualización de estado", fillcolor="#E2E8F0", shape="ellipse"];
    
    Continuar [label="[ CONTINUAR CICLO ]\nRetorno al monitoreo contextual o transición de fase", fillcolor="#3182CE", fontcolor="white"];

    // Definición de transiciones y flujo
    Entradas -> Inicio [color="#4A5568"];
    Inicio -> Estimulo [color="#4A5568"];
    Estimulo -> Check0 [color="#4A5568"];
    
    Check0 -> Historial [label=" SÍ (Autonomía / Sin Timeout) ", color="#38A169", fontcolor="#38A169"];
    Check0 -> Nivel1 [label=" NO / TIMEOUT ", color="#E53E3E", fontcolor="#E53E3E"];
    
    Nivel1 -> Check1 [color="#4A5568"];
    Check1 -> Historial [label=" SÍ ", color="#38A169", fontcolor="#38A169"];
    Check1 -> Nivel2 [label=" NO / TIMEOUT ", color="#E53E3E", fontcolor="#E53E3E"];
    
    Nivel2 -> Check2 [color="#4A5568"];
    Check2 -> Historial [label=" SÍ ", color="#38A169", fontcolor="#38A169"];
    Check2 -> Nivel3 [label=" NO / TIMEOUT ", color="#E53E3E", fontcolor="#E53E3E"];
    
    Nivel3 -> Historial [color="#4A5568"];
    
    Historial -> Retro [color="#4A5568"];
    Retro -> Continuar [color="#4A5568"];
    
    // Bucle de retorno para el siguiente ciclo
    Continuar -> Inicio [color="#3182CE", constraint=false, style="dashed"];# Tesis-2026
