"""Consola independiente para probar la Fase 2: estrategia y preparación."""

import json
import re
import signal
from datetime import datetime
from pathlib import Path

from agente import MotorAnalisis


TIEMPO_LIMITE_SEGUNDOS = 30
OBJETIVO_FASE1_POR_DEFECTO = (
    "Analizar la relación entre contaminantes y condiciones meteorológicas."
)
ARCHIVO_ESTADO = Path("estado_fase2.json")


class TiempoAgotado(Exception):
    """Indica que el estudiante no respondió dentro del tiempo definido."""


class EstadoFase2:
    def __init__(self, variables, calidad, escalado, objetivo):
        self.contenido = {
            "fase_activa": "Fase 2: Estrategia, calidad y preparación",
            "tiempo_limite_segundos": TIEMPO_LIMITE_SEGUNDOS,
            "objetivo_fase1": objetivo,
            "variables": variables,
            "diagnostico_calidad": calidad,
            "analisis_escalado_transformacion": escalado,
            "historial_acciones": [],
        }

    def registrar(self, accion, **datos):
        evento = {
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "accion": accion,
            **datos,
        }
        self.contenido["historial_acciones"].append(evento)
        ARCHIVO_ESTADO.write_text(
            json.dumps(self.contenido, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def pedir_con_tiempo(mensaje):
    def activar_timeout(signum, frame):
        raise TiempoAgotado

    anterior = signal.signal(signal.SIGALRM, activar_timeout)
    signal.setitimer(signal.ITIMER_REAL, TIEMPO_LIMITE_SEGUNDOS)
    try:
        respuesta = input(mensaje).strip()
        return respuesta or None
    except TiempoAgotado:
        print("\n⏱️ Tiempo agotado.")
        return None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, anterior)


def mostrar_salud(calidad, escalado):
    print("\n=== NIVEL 1: INFORMACIÓN Y OBSERVACIÓN ===")
    print("Alertas detectadas por Python/Pandas:")
    hay_alertas = False

    if calidad["nulos"]:
        hay_alertas = True
        print("\n🔴 Valores nulos detectados:")
        for columna, cantidad in calidad["nulos"].items():
            porcentaje = calidad.get("nulos_porcentaje", {}).get(columna, 0)
            print(f"- {columna}: {cantidad} nulos ({porcentaje}%)")

    if calidad["outliers"]:
        hay_alertas = True
        print("\n⚠️ Outliers detectados por IQR:")
        for columna, cantidad in calidad["outliers"].items():
            print(f"- {columna}: {cantidad} valores atípicos")

    if escalado["amerita_escalado_si_se_combinan_variables"]:
        hay_alertas = True
        print("\n📏 Normalización / escalado:")
        print(f"- Variables evaluadas: {', '.join(escalado['variables_numericas_evaluadas'])}")
        print(f"- {escalado['interpretacion']}")

    if escalado["requiere_transformacion_temporal"]:
        hay_alertas = True
        print("\n🗓️ Transformación temporal:")
        print(f"- {escalado['nota_transformacion']}")

    if not hay_alertas:
        print("\nNo se detectaron alertas de calidad o preparación para mostrar.")


def interpretar_respuesta(texto):
    porcentaje = re.search(r"PORCENTAJE_CUMPLIMIENTO\s*:\s*\[?\s*(\d{1,3})", texto, re.I)
    estado = re.search(r"ESTADO\s*:\s*\[([^\]]+)\]", texto, re.I)
    nivel = re.search(r"NIVEL_ACTIVADO\s*:\s*\[([^\]]+)\]", texto, re.I)
    feedback = re.search(
        r"FEEDBACK_GUIA\s*:\s*\[([\s\S]*?)\]\s*(?:OPCION_CORRECTA|$)",
        texto,
        re.I,
    )
    opcion_correcta = re.search(r"OPCION_CORRECTA\s*:\s*\[?\s*([1-3])", texto, re.I)
    return {
        "porcentaje": min(100, int(porcentaje.group(1))) if porcentaje else 0,
        "estado": estado.group(1).strip() if estado else "ERROR",
        "nivel": nivel.group(1).strip() if nivel else "No identificado",
        "feedback": feedback.group(1).strip() if feedback else texto,
        "opcion_correcta": int(opcion_correcta.group(1)) if opcion_correcta else None,
    }


def elegir_alternativa_nivel_3(motor, resultado, estado, objetivo):
    print("\n=== NIVEL 3: RECOMENDAR ALTERNATIVAS ===")
    print(resultado["feedback"])
    eleccion = pedir_con_tiempo("\nResponde únicamente 1, 2 o 3: ")
    estado.registrar("eleccion_nivel_3", eleccion=eleccion or "timeout")

    if eleccion and eleccion.isdigit() and int(eleccion) == resultado["opcion_correcta"]:
        print("\n✅ Elegiste la alternativa correcta.")
        alternativa = re.search(
            rf"^\s*{eleccion}[.)]\s*(.+)$", resultado["feedback"], re.MULTILINE
        )
        alternativa = alternativa.group(1) if alternativa else "La alternativa seleccionada"
        try:
            explicacion = motor.explicar_alternativa_correcta_fase2(alternativa, objetivo)
            print(f"\n¿Por qué es correcta?\n{explicacion}")
            estado.registrar("explicacion_alternativa_correcta", detalle=explicacion)
        except Exception as error:
            print(f"No se pudo generar la explicación: {error}")
        estado.registrar("fin_fase_2", estado="alternativa_correcta")
        return True

    print("\nNo se recibió una opción correcta. Se activará el Nivel 4.")
    return False


def ejecutar_fase_2():
    motor = MotorAnalisis()
    objetivo = OBJETIVO_FASE1_POR_DEFECTO
    try:
        variables = motor.obtener_taxonomia()
        calidad = motor.obtener_diagnostico_calidad()
        escalado = motor.obtener_analisis_escalado_transformacion(objetivo)
    except Exception as error:
        print(f"No se pudo cargar el contexto de Fase 2: {error}")
        print("Inicia primero la API en otra terminal con: python3 app.py")
        return

    estado = EstadoFase2(variables, calidad, escalado, objetivo)
    estado.registrar("inicio_fase_2")
    print("\n=== FASE 2: ESTRATEGIA, CALIDAD Y PREPARACIÓN ===")
    print(f"Objetivo heredado para la prueba: {objetivo}")
    print(f"Tienes {TIEMPO_LIMITE_SEGUNDOS} segundos por propuesta.")
    mostrar_salud(calidad, escalado)

    fallos_criticos = 0
    while True:
        propuesta = pedir_con_tiempo(
            "\n¿Cuál es tu plan para mejorar la salud del dataset y dejarlo listo para el análisis? "
        )
        if propuesta is None:
            propuesta = "No se recibió una propuesta metodológica dentro del tiempo establecido."
            estado.registrar("timeout")

        try:
            texto_llm = motor.evaluar_estrategia_fase2(
                propuesta,
                fallos_criticos,
                objetivo,
                "NIVEL 3: Recomendar Alternativas" if fallos_criticos == 1 else None,
            )
        except Exception as error:
            print(f"No se pudo evaluar la estrategia: {error}")
            estado.registrar("error_evaluacion", detalle=str(error))
            return

        resultado = interpretar_respuesta(texto_llm)

        # El primer fallo solo puede llegar al Nivel 2. Si el modelo ignora la
        # regla y salta de nivel, se solicita de nuevo el feedback correcto.
        if (
            fallos_criticos == 0
            and resultado["porcentaje"] < 50
            and "NIVEL 2" not in resultado["nivel"].upper()
        ):
            try:
                texto_llm = motor.evaluar_estrategia_fase2(
                    propuesta,
                    0,
                    objetivo,
                    "NIVEL 2: Consecuencias y Reflexión",
                )
                resultado = interpretar_respuesta(texto_llm)
            except Exception as error:
                print(f"No se pudo corregir el nivel de ayuda: {error}")
                estado.registrar("error_nivel_2", detalle=str(error))
                return

        estado.registrar("evaluar_estrategia", propuesta=propuesta, **resultado)
        print("\n--- Evaluación metodológica ---")
        print(f"Cumplimiento: {resultado['porcentaje']}%")
        print(f"Estado: {resultado['estado']}")
        print(f"Nivel: {resultado['nivel']}")
        if "NIVEL 3" not in resultado["nivel"].upper():
            print(f"Feedback: {resultado['feedback']}")

        if resultado["estado"].upper() == "EXITO" or resultado["porcentaje"] == 100:
            print("\n✅ Fase 2 superada. Puedes continuar a la Fase 3.")
            estado.registrar("fin_fase_2", estado="exito")
            return

        if resultado["porcentaje"] >= 50:
            print("\nTu estrategia está encaminada. Completa lo señalado y vuelve a intentarlo.")
            continue

        if "NIVEL 4" in resultado["nivel"].upper():
            print(resultado["feedback"])
            print("\n✅ Se ha prescrito el plan metodológico final.")
            print("Puedes continuar a la Fase 3 con el plan indicado.")
            estado.registrar("fin_fase_2", estado="plan_prescrito")
            return

        fallos_criticos += 1
        if "NIVEL 3" in resultado["nivel"].upper():
            if elegir_alternativa_nivel_3(motor, resultado, estado, objetivo):
                print("\n✅ Fase 2 superada. Puedes continuar a la Fase 3.")
                return
            try:
                texto_plan = motor.evaluar_estrategia_fase2(
                    "El usuario no pudo elegir una alternativa válida del Nivel 3.",
                    2,
                    objetivo,
                    "NIVEL 4: Prescribir Plan",
                )
                plan = interpretar_respuesta(texto_plan)
            except Exception as error:
                print(f"No se pudo prescribir el plan: {error}")
                estado.registrar("error_prescripcion", detalle=str(error))
                return

            estado.registrar("nivel_4_prescripcion", **plan)
            print("\n=== NIVEL 4: PRESCRIBIR PLAN ===")
            print(plan["feedback"])
            print("\n✅ Se ha prescrito el plan metodológico final.")
            print("Puedes continuar a la Fase 3 con el plan indicado.")
            estado.registrar("fin_fase_2", estado="plan_prescrito")
            return


if __name__ == "__main__":
    ejecutar_fase_2()
