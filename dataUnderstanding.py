import pandas as pd
import os
from io import StringIO
from openai import OpenAI
from dotenv import load_dotenv

# 1. Configuración
load_dotenv()

class MiAsistente:
    def __init__(self, data_info, data_describe):
        self.client = OpenAI(base_url="https://api.groq.com/openai/v1")
        self.modelo = "llama-3.1-8b-instant"
        
        # System Prompt Pedagógico que definimos
        system_prompt = """
        Actúa como un Tutor Experto en Ciencia de Datos y Pedagogía. Tu objetivo es ayudar a un estudiante 
        a entender y diagnosticar su dataset siguiendo la metodología de 'Data Understanding'.
        
        Recibirás la estructura (info) y estadísticas básicas (describe) del dataset. Tu labor es:
        1. Analizar la estructura: Identifica variables Categorical, Numerical y Datetime.
        2. Diagnóstico: Detecta valores faltantes comparando el total de filas con el 'Non-Null Count'.
        3. Interacción: Explica al estudiante qué tiene y qué problemas de calidad encontraste.
        4. Tono: Alentador, didáctico y profesional. No cambies datos, solo guía al usuario.
        """
        
        self.historial = [{"role": "system", "content": system_prompt}]
        
        # Pre-carga del diagnóstico técnico para que el tutor ya sepa qué hay
        contexto_inicial = f"""
        Aquí tienes el resumen técnico del dataset cargado:
        
        --- INFO ---
        {data_info}
        
        --- DESCRIBE ---
        {data_describe}
        
        Por favor, comienza saludando al estudiante y realiza un diagnóstico inicial de la calidad de sus datos.
        """
        self.historial.append({"role": "user", "content": contexto_inicial})

    def preguntar(self, mensaje_usuario):
        self.historial.append({"role": "user", "content": mensaje_usuario})
        try:
            respuesta = self.client.chat.completions.create(
                model=self.modelo,
                messages=self.historial
            )
            contenido = respuesta.choices[0].message.content
            self.historial.append({"role": "assistant", "content": contenido})
            return contenido
        except Exception as e:
            return f"Error de conexión: {e}"

# --- FLUJO PRINCIPAL ---

# 1. Cargar archivo
ruta_archivo = '../data/PRSA_Data_Wanshouxigong_20130301-20170228.csv'
archivo = pd.read_csv(ruta_archivo)

# 2. Capturar metadatos en texto
buffer_info = StringIO()
archivo.info(buf=buffer_info)
info_str = buffer_info.getvalue()
describe_str = archivo.describe().to_string()

# 3. Inicializar asistente con los metadatos
print("Inicializando Tutor Pedagógico...")
asistente = MiAsistente(info_str, describe_str)

# 4. Obtener diagnóstico inicial automáticamente
diagnostico_inicial = asistente.preguntar("Hazme el diagnóstico inicial de mi dataset.")
print(f"\nTutor: {diagnostico_inicial}")

# 5. Bucle de chat
while True:
    pregunta = input("\nTú: ")
    if pregunta.lower() == "salir":
        break
    
    respuesta = asistente.preguntar(pregunta)
    print(f"Tutor: {respuesta}")