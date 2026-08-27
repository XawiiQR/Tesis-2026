"""Prueba secuencial de la Fase 1: orientar preguntas sobre el dataset."""

import json
import re
import signal
from datetime import datetime
from pathlib import Path

import requests

from agente import MotorAnalisis


TIEMPO_LIMITE_SEGUNDOS = 30  # Variable fácil de cambiar durante las pruebas.
ARCHIVO_ESTADO = Path("estado_fase1.json")


class TiempoAgotado(Exception):
    pass


class EstadoFase1:
    """Variables temporales y el historial de la sesión de Fase 1."""

    def __init__(self, variables):
        self.fase_activa = "Datos / Data Understanding"
        self.tiempo_limite_segundos = TIEMPO_LIMITE_SEGUNDOS
        self.variables = variables
        self.preguntas_usuario = []
        self.preguntas_sugeridas = []
        self.historial_acciones = []

    def registrar(self, accion, estado, pregunta=None, detalle=None):
        evento = {
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "accion": accion,
            "estado": estado,
        }
        if pregunta:
            evento["pregunta"] = pregunta
            self.preguntas_usuario.append(pregunta)
        if detalle:
            evento["detalle"] = detalle
        self.historial_acciones.append(evento)
        self.guardar()

    def guardar(self):
        contenido = {
            "fase_activa": self.fase_activa,
            "tiempo_limite_segundos": self.tiempo_limite_segundos,
            "variables": self.variables,
            "preguntas_usuario": self.preguntas_usuario,
            "preguntas_sugeridas": self.preguntas_sugeridas,
            "historial_acciones": self.historial_acciones,
        }
        ARCHIVO_ESTADO.write_text(
            json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def pedir_con_tiempo(mensaje):
    """Lee desde la terminal hasta que se cumpla el límite de tiempo en macOS/Linux."""
    def activar_timeout(signum, frame):
        raise TiempoAgotado

    anterior = signal.signal(signal.SIGALRM, activar_timeout)
    signal.setitimer(signal.ITIMER_REAL, TIEMPO_LIMITE_SEGUNDOS)
    try:
        respuesta = input(mensaje).strip()
        return respuesta if respuesta else None
    except TiempoAgotado:
        print("\n⏱️ Tiempo agotado.")
        return None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, anterior)


def imprimir_variables(taxonomia):
    print("\nVariables disponibles para orientar tu consulta:")
    for tipo, columnas in taxonomia.items():
        print(f"- {tipo.capitalize()}: {', '.join(columnas) if columnas else 'ninguna'}")


def evaluar_pregunta(motor, estado, pregunta, nivel):
    if pregunta is None:
        estado.registrar(f"nivel_{nivel}", "timeout")
        return False

    try:
        respuesta = motor.validar_pregunta_F1_1(pregunta)
    except Exception as error:
        estado.registrar(f"nivel_{nivel}", "error", pregunta, str(error))
        print(f"No se pudo validar la pregunta: {error}")
        return False

    viable = respuesta.lstrip().startswith("✅")
    estado.registrar(
        f"nivel_{nivel}", "viable" if viable else "no_viable", pregunta, respuesta
    )
    print(f"\n--- Resultado del LLM ---\n{respuesta}")
    return viable


def extraer_tres_preguntas(texto):
    preguntas = []
    for linea in texto.splitlines():
        coincidencia = re.match(r"\s*[1-3][.)]\s*(.+)", linea)
        if coincidencia:
            preguntas.append(coincidencia.group(1).strip())
    return preguntas[:3]


def extraer_eleccion_prescrita(texto):
    coincidencia = re.search(r"ELECCION\s*:\s*([1-3])", texto, re.IGNORECASE)
    return int(coincidencia.group(1)) if coincidencia else None


def sugerir_y_elegir(motor, estado):
    print("\n🧭 NIVEL 3: Sugerir preguntas + explicar")
    print("Generando tres preguntas que sí pueden responderse con el dataset...")
    try:
        texto_llm = motor.generar_tres_preguntas_sugeridas()
        preguntas = extraer_tres_preguntas(texto_llm)
    except Exception as error:
        estado.registrar("nivel_3", "error", detalle=str(error))
        print(f"No se pudieron generar preguntas sugeridas: {error}")
        return

    if len(preguntas) != 3:
        estado.registrar("nivel_3", "formato_invalido", detalle=texto_llm)
        print("El LLM no devolvió las tres preguntas en el formato esperado. Inténtalo otra vez.")
        return

    estado.preguntas_sugeridas = preguntas
    estado.registrar("nivel_3", "preguntas_sugeridas", detalle=texto_llm)
    print("\n--- NIVEL 3: Preguntas sugeridas y su utilidad ---")
    print(texto_llm)
    print("\nElige una consulta sugerida:")
    for indice, pregunta in enumerate(preguntas, start=1):
        print(f"{indice}. {pregunta}")

    seleccion = pedir_con_tiempo(
        f"\nEscribe 1, 2 o 3 (tienes {TIEMPO_LIMITE_SEGUNDOS} segundos): "
    )
    if seleccion in {"1", "2", "3"}:
        elegida = preguntas[int(seleccion) - 1]
        estado.registrar("pregunta_final", "seleccion_usuario", elegida)
        print(f"\nElegiste esta pregunta para continuar el análisis:\n→ {elegida}")
        return

    print("\n✅ NIVEL 4: Prescribir + explicar")
    print("No hubo una selección válida; el LLM tomará la decisión recomendada.")
    try:
        prescripcion = motor.prescribir_pregunta(preguntas)
        indice = extraer_eleccion_prescrita(prescripcion)
    except Exception as error:
        estado.registrar("nivel_4", "error", detalle=str(error))
        print(f"No se pudo generar la prescripción: {error}")
        return

    if indice is None:
        estado.registrar("nivel_4", "formato_invalido", detalle=prescripcion)
        print("El LLM no indicó una elección válida para la prescripción.")
        return

    elegida = preguntas[indice - 1]
    estado.registrar("nivel_4", "pregunta_prescrita", elegida, prescripcion)
    print(f"\nPregunta prescrita para continuar el análisis:\n→ {elegida}")
    print(f"\n--- Decisión y utilidad de la prescripción ---\n{prescripcion}")


def ejecutar_fase_1():
    motor = MotorAnalisis()
    try:
        variables = motor.obtener_taxonomia()
    except requests.RequestException:
        print("No se puede conectar con la API. Inicia primero: python3 app.py")
        return
    except Exception as error:
        print(f"No se pudo iniciar la Fase 1: {error}")
        return

    estado = EstadoFase1(variables)
    estado.registrar("inicio_fase", "activa", detalle="Variables cargadas desde la API")
    print("\n=== FASE 1: COMPRENSIÓN DEL DATASET ===")
    print(f"Tienes {TIEMPO_LIMITE_SEGUNDOS} segundos por respuesta.")

    pregunta_1 = pedir_con_tiempo("\nEscribe tu pregunta o duda para analizar el CSV: ")
    if evaluar_pregunta(motor, estado, pregunta_1, nivel=1):
        print("\nPregunta validada. La Fase 1 puede continuar con esa consulta.")
    else:
        print("\n🎯 NIVEL 2: Mostrar variables, orientar y validar otra pregunta")
        print("La retroalimentación anterior indica qué falta o qué debes precisar.")
        imprimir_variables(estado.variables)
        try:
            descripcion = motor.generar_descripcion_variables()
            estado.registrar(
                "describir_variables", "completada", detalle=descripcion
            )
            print(f"\n--- ¿Qué significa cada variable? ---\n{descripcion}")
        except Exception as error:
            estado.registrar("describir_variables", "error", detalle=str(error))
            print(f"No se pudo generar la explicación de variables: {error}")
        pregunta_2 = pedir_con_tiempo(
            "\n¿Qué consulta desearías saber con estas variables? "
        )
        if evaluar_pregunta(motor, estado, pregunta_2, nivel=2):
            print("\nPregunta validada. La Fase 1 puede continuar con esa consulta.")
        else:
            sugerir_y_elegir(motor, estado)

    estado.registrar("fin_fase_1", "completada")
    print(f"\nHistorial y variables temporales guardados en {ARCHIVO_ESTADO}.")


if __name__ == "__main__":
    ejecutar_fase_1()
