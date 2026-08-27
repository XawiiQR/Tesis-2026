import requests
from openai import OpenAI
import prompts 
from dotenv import load_dotenv

# 1. Cargar configuración
load_dotenv()

class MotorAnalisis:
    def __init__(self):
        # La dirección base de tu servidor API
        self.base_url = "http://127.0.0.1:5000/api"
        self.client = OpenAI(base_url="https://api.groq.com/openai/v1")

    def obtener_taxonomia(self):
        """Obtiene todas las variables disponibles, agrupadas por tipo."""
        response = requests.get(
            f"{self.base_url}/taxonomia-variables", timeout=15
        )
        response.raise_for_status()
        return response.json()

    def generar_diagnostico(self, endpoint_name):
        # 1. Construir la URL completa uniendo la base y el nombre
        url_completa = f"{self.base_url}/{endpoint_name}"
        
        # 2. Consultar a la API
        response = requests.get(url_completa)
        datos = response.json()
        
        # 3. Unir con el prompt
        mensaje = prompts.obtener_prompt_diagnostico(datos)
        # 4. Llamar al LLM
        respuesta = self.client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": mensaje}]
        )
        return respuesta.choices[0].message.content
    def generar_diagnostico_calidad(self):
        # 1. Llamar al endpoint que acabamos de definir en app.py
        url_calidad = f"{self.base_url}/diagnostico-calidad"
        
        try:
            response = requests.get(url_calidad)
            datos_calidad = response.json()
            
            # 2. Generar el mensaje usando el prompt del "Consultor de Datos"
            mensaje = prompts.obtener_prompt_calidad(datos_calidad)
            
            # 3. Llamar al LLM para que analice y recomiende
            respuesta = self.client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[{"role": "user", "content": mensaje}]
            )
            return respuesta.choices[0].message.content
            
        except Exception as e:
            return f"Error al realizar el diagnóstico de calidad: {str(e)}"
    
    def generar_mapa_variables(self):
        datos = self.obtener_taxonomia()
        
        mensaje = prompts.obtener_prompt_taxonomia(datos)
        
        respuesta = self.client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": mensaje}]
        )
        return respuesta.choices[0].message.content

    def generar_descripcion_variables(self):
        """Describe de manera breve qué representa cada variable del dataset."""
        datos = self.obtener_taxonomia()
        mensaje = prompts.obtener_prompt_descripcion_variables(datos)

        respuesta = self.client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": mensaje}]
        )
        return respuesta.choices[0].message.content

    def generar_preguntas_relaciones(self):
        """Identifica el tema del dataset y propone preguntas entre sus variables."""
        datos = self.obtener_taxonomia()

        mensaje = prompts.obtener_prompt_preguntas_relaciones(datos)

        respuesta = self.client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": mensaje}]
        )
        return respuesta.choices[0].message.content

    def validar_pregunta_F1_1(self, pregunta):
        """Evalúa si una pregunta se puede responder con las variables del dataset."""
        if not pregunta.strip():
            return "⚠️ Escribe una pregunta para poder evaluarla."

        datos = self.obtener_taxonomia()
        mensaje = prompts.obtener_prompt_validacion_pregunta(pregunta, datos)

        respuesta = self.client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": mensaje}]
        )
        return respuesta.choices[0].message.content

    def generar_tres_preguntas_sugeridas(self):
        """Genera tres preguntas viables para orientar al estudiante."""
        datos = self.obtener_taxonomia()
        mensaje = prompts.obtener_prompt_tres_preguntas_sugeridas(datos)

        respuesta = self.client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": mensaje}]
        )
        return respuesta.choices[0].message.content

    def explicar_pregunta_elegida(self, pregunta):
        """Explica la utilidad de una pregunta seleccionada para el dataset."""
        datos = self.obtener_taxonomia()
        mensaje = prompts.obtener_prompt_explicacion_pregunta_elegida(pregunta, datos)

        respuesta = self.client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": mensaje}]
        )
        return respuesta.choices[0].message.content

    def prescribir_pregunta(self, preguntas):
        """Elige la mejor pregunta sugerida cuando el estudiante no selecciona una."""
        datos = self.obtener_taxonomia()
        opciones = "\n".join(
            f"{indice}. {pregunta}" for indice, pregunta in enumerate(preguntas, 1)
        )
        mensaje = prompts.obtener_prompt_prescripcion_pregunta(opciones, datos)

        respuesta = self.client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": mensaje}]
        )
        return respuesta.choices[0].message.content
    
if __name__ == "__main__":
    # Prueba aislada del agente. Para el flujo completo usa: python3 main.py
    motor = MotorAnalisis()
    pregunta_usuario = input("\nEscribe una pregunta sobre el dataset: ")
    resultado_validacion = motor.validar_pregunta_F1_1(pregunta_usuario)
    print("\n--- Validación de la Pregunta ---\n")
    print(resultado_validacion)
