from flask import Flask, jsonify, request, send_from_directory
import pandas as pd
import numpy as np
import os
from pathlib import Path

from agente import MotorAnalisis

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
FRONT_DIR = BASE_DIR / "front"

# Asegúrate de que esta ruta sea la correcta para tu archivo
CSV_PATH = '../data/PRSA_Data_Wanshouxigong_20130301-20170228.csv'
df = pd.read_csv(CSV_PATH)


@app.after_request
def permitir_frontend_externo(response):
    """Permite probar el frontend desde Live Server o una vista previa del IDE."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


def ejecutar_llm(funcion):
    """Ejecuta una acción del agente y convierte errores en respuestas JSON."""
    try:
        return jsonify({"respuesta": funcion()})
    except Exception as error:
        return jsonify({"error": str(error)}), 500


@app.route('/', methods=['GET'])
def inicio():
    return send_from_directory(FRONT_DIR, 'index.html')


@app.route('/front/<path:archivo>', methods=['GET'])
def archivos_front(archivo):
    return send_from_directory(FRONT_DIR, archivo)

@app.route('/api/tarjeta-identidad', methods=['GET'])
def get_tarjeta():
    
    # 2. Calcular el peso del archivo en MB
    tamano_bytes = os.path.getsize(CSV_PATH)
    peso_mb = round(tamano_bytes / (1024 * 1024), 2)
    
    # 3. Lógica para detectar fecha
    cobertura = "No determinado"
    cols_fecha = ['year', 'month', 'day']
    
    if all(col in df.columns for col in cols_fecha):
        try:
            fechas = pd.to_datetime(df[cols_fecha])
            cobertura = f"{fechas.min().date()} a {fechas.max().date()}"
        except:
            pass
    else:
        for col in df.columns:
            if 'date' in col.lower() or 'time' in col.lower():
                try:
                    fechas = pd.to_datetime(df[col])
                    cobertura = f"{fechas.min().date()} a {fechas.max().date()}"
                    break
                except:
                    continue

    # 4. Retornar JSON completo
    return jsonify({
        "filas": int(df.shape[0]),
        "columnas": int(df.shape[1]),
        "peso_mb": peso_mb,
        "cobertura_temporal": cobertura
    })

# Supongamos que ya tienes cargado tu dataframe aquí


@app.route('/api/diagnostico-calidad', methods=['GET'])
def diagnostico_calidad():
    # 1. Nulos
    nulos_detalle = df.isnull().sum()
    nulos_dict = nulos_detalle[nulos_detalle > 0].to_dict()
    
    # 2. Outliers (Método IQR)
    outliers_dict = {}
    numericas = df.select_dtypes(include=[np.number]).columns
    for col in numericas:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        count = df[(df[col] < lower_bound) | (df[col] > upper_bound)].shape[0]
        if count > 0:
            outliers_dict[col] = int(count)

    # 3. Estructura Temporal
    cols_necesarias = {'year', 'month', 'day', 'hour'}
    if cols_necesarias.issubset(df.columns):
        estado_temporal = {"formato": "separado , necesita transformacion", "columnas": list(cols_necesarias)}
    else:
        estado_temporal = {"formato": "completo"}

    return jsonify({
        "filas": int(df.shape[0]),
        "nulos": nulos_dict,
        "outliers": outliers_dict,
        "estructura_temporal": estado_temporal
    })

@app.route('/api/taxonomia-variables', methods=['GET'])
def taxonomia_variables():
    taxonomia = {
        "temporales": [],
        "numericas": [],
        "categoricas": []
    }
    
    for col in df.columns:
        # Lógica simple de clasificación
        if col.lower() in ['year', 'month', 'day', 'hour', 'date', 'time']:
            taxonomia["temporales"].append(col)
        elif pd.api.types.is_numeric_dtype(df[col]):
            taxonomia["numericas"].append(col)
        else:
            taxonomia["categoricas"].append(col)
            
    return jsonify(taxonomia)


@app.route('/api/validar-pregunta', methods=['POST', 'OPTIONS'])
def validar_pregunta():
    if request.method == 'OPTIONS':
        return '', 204
    datos = request.get_json(silent=True) or {}
    pregunta = str(datos.get("pregunta", "")).strip()
    if not pregunta:
        return jsonify({"error": "La pregunta es obligatoria."}), 400

    motor = MotorAnalisis()
    return ejecutar_llm(lambda: motor.validar_pregunta_F1_1(pregunta))


@app.route('/api/describir-variables', methods=['GET'])
def describir_variables():
    motor = MotorAnalisis()
    return ejecutar_llm(motor.generar_descripcion_variables)


@app.route('/api/preguntas-sugeridas', methods=['GET'])
def preguntas_sugeridas():
    motor = MotorAnalisis()
    return ejecutar_llm(motor.generar_tres_preguntas_sugeridas)


@app.route('/api/prescribir-pregunta', methods=['POST', 'OPTIONS'])
def prescribir_pregunta():
    if request.method == 'OPTIONS':
        return '', 204
    datos = request.get_json(silent=True) or {}
    preguntas = datos.get("preguntas", [])
    if not isinstance(preguntas, list) or len(preguntas) != 3:
        return jsonify({"error": "Se requieren exactamente tres preguntas."}), 400

    motor = MotorAnalisis()
    return ejecutar_llm(lambda: motor.prescribir_pregunta(preguntas))

if __name__ == '__main__':
    app.run(port=5000)
