import fastf1
import pandas as pd
import json
import os
import numpy as np

# Configuración de directorios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
CACHE_DIR = os.path.join(BASE_DIR, 'cache')

if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
if not os.path.exists(CACHE_DIR): os.makedirs(CACHE_DIR)

try:
    fastf1.Cache.enable_cache(CACHE_DIR)
except AttributeError:
    print("Aviso: No se pudo habilitar el caché con fastf1.Cache.")

def extract_all_data():
    # GP Abu Dhabi 2021 - Qualifying
    session = fastf1.get_session(2021, 'Abu Dhabi', 'Q')
    session.load()

    # --- 1. TABLA DE RESULTADOS ---
    results = session.results
    
    # En Qualifying, el mejor tiempo suele estar en Q1, Q2 o Q3
    # Creamos una columna 'BestTime' calculada
    q_columns = [col for col in ['Q1', 'Q2', 'Q3'] if col in results.columns]
    results['BestTime'] = results[q_columns].min(axis=1)

    # Seleccionamos columnas existentes para evitar KeyError
    target_map = {
        'DriverNumber': 'Number',
        'Abbreviation': 'Driver',
        'TeamName': 'Team',
        'Position': 'Pos',
        'BestTime': 'Time'
    }
    
    available_cols = [col for col in target_map.keys() if col in results.columns]
    df_results = results[available_cols].copy()
    df_results = df_results.rename(columns=target_map)
    
    # Limpieza de Posición y formateo de Tiempo
    if 'Pos' in df_results.columns:
        df_results['Pos'] = df_results['Pos'].fillna(0).astype(int)
    
    def format_time(x):
        if pd.isnull(x) or str(x) == 'NaT': return "No Time"
        ts = x.total_seconds()
        minutes = int(ts // 60)
        seconds = ts % 60
        return f"{minutes}:{seconds:06.3f}"

    if 'Time' in df_results.columns:
        df_results['Time'] = df_results['Time'].apply(format_time)
    
    with open(os.path.join(DATA_DIR, 'qualifying_results.json'), 'w', encoding='utf-8') as f:
        json.dump(df_results.to_dict(orient='records'), f, indent=4, ensure_ascii=False)

    # --- MÉTRICAS DE TELEMETRÍA ---
    metric1_data = [] # Top Speed
    metric2_data = [] # Brake Efficiency

    drivers = results['Abbreviation'].unique()

    for drv in drivers:
        try:
            lap = session.laps.pick_driver(drv).pick_fastest()
            if lap is None: continue
            
            tel = lap.get_telemetry()
            
            # Métrica 1: Top Speed (km/h)
            max_speed = int(tel['Speed'].max())
            metric1_data.append({
                "driver": drv,
                "value": max_speed,
                "pos": int(results.loc[results['Abbreviation'] == drv, 'Position'].iloc[0])
            })

            # Métrica 2: Brake Efficiency
            tel['DeltaSpeed'] = tel['Speed'].diff()
            braking = tel[tel['Brake'] == True].copy()
            
            if not braking.empty:
                avg_decel = abs(braking['DeltaSpeed'].mean())
                brake_score = round(avg_decel * 5, 2) 
            else:
                brake_score = 0

            metric2_data.append({
                "driver": drv,
                "value": brake_score,
                "pos": int(results.loc[results['Abbreviation'] == drv, 'Position'].iloc[0])
            })

        except Exception as e:
            print(f"Error con {drv}: {e}")

    # Exportar métricas
    with open(os.path.join(DATA_DIR, 'metrica1.json'), 'w', encoding='utf-8') as f:
        json.dump(metric1_data, f, indent=4, ensure_ascii=False)
        
    with open(os.path.join(DATA_DIR, 'metrica2.json'), 'w', encoding='utf-8') as f:
        json.dump(metric2_data, f, indent=4, ensure_ascii=False)

    print(f"Archivos JSON actualizados con éxito en {DATA_DIR}")

if __name__ == "__main__":
    extract_all_data()
