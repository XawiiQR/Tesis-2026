#Pedir la lista de modelos disponibles en Groq
'''# import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://api.groq.com/openai/v1"
)

# Obtener la lista de modelos
modelos = client.models.list()

print("Modelos disponibles en Groq:")
for modelo in modelos:
    print(f"- {modelo.id}")
    '''


import os
from openai import OpenAI
from dotenv import load_dotenv

# 1. Cargar configuración
load_dotenv()

class MiAsistente:
    def __init__(self):
        self.client = OpenAI(base_url="https://api.groq.com/openai/v1")
        self.modelo = "llama-3.1-8b-instant"
        self.historial = [
            {"role": "system", "content": "Eres un asistente técnico útil integrado en el sistema de mi tesis. Responde de forma clara, técnica y concisa."}
        ]

    def preguntar(self, mensaje_usuario):
        # Añadimos la pregunta al historial para que "recuerde" la charla
        self.historial.append({"role": "user", "content": mensaje_usuario})
        
        try:
            respuesta = self.client.chat.completions.create(
                model=self.modelo,
                messages=self.historial
            )
            
            contenido = respuesta.choices[0].message.content
            # Guardamos la respuesta en el historial
            self.historial.append({"role": "assistant", "content": contenido})
            return contenido
        
        except Exception as e:
            return f"Error de conexión: {e}"

# --- USO DEL ASISTENTE ---
asistente = MiAsistente()

print("Asistente listo. Escribe 'salir' para terminar.")
while True:
    pregunta = input("\nTú: ")
    if pregunta.lower() == "salir":
        break
    
    respuesta = asistente.preguntar(pregunta)
    print(f"Asistente: {respuesta}")