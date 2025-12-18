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
    
    # Nombres de columnas actualizados para FastF1 moderno
    # Usamos .get() o verificamos columnas para evitar KeyError
    available_cols = results.columns.tolist()
    target_cols = ['DriverNumber', 'Abbreviation', 'TeamName', 'Position', 'BestLapTime']
    
    # Mapeo de seguridad por si cambian los nombres
    col_map = {
        'DriverNumber': 'Number',
        'Abbreviation': 'Driver',
        'TeamName': 'Team',
        'Position': 'Pos',
        'BestLapTime': 'Time'
    }

    df_results = results[[c for c in target_cols if c in available_cols]].copy()
    df_results = df_results.rename(columns=col_map)
    
    # Formatear tiempo para JSON
    if 'Time' in df_results.columns:
        df_results['Time'] = df_results['Time'].apply(
            lambda x: str(x).split('days ')[-1][3:-3] if pd.notnull(x) else "N/A"
        )
    
    with open(os.path.join(DATA_DIR, 'qualifying_results.json'), 'w', encoding='utf-8') as f:
        json.dump(df_results.to_dict(orient='records'), f, indent=4, ensure_ascii=False)

    # --- MÉTRICAS DE TELEMETRÍA ---
    metric1_data = [] # Top Speed
    metric2_data = [] # Brake Efficiency index

    drivers = results['Abbreviation'].unique()

    for drv in drivers:
        try:
            lap = session.laps.pick_driver(drv).pick_fastest()
            if lap is None: continue
            
            # Solo descargamos telemetría de la vuelta más rápida (ligero)
            tel = lap.get_telemetry()
            
            # Métrica 1: Top Speed
            max_speed = int(tel['Speed'].max())
            metric1_data.append({
                "driver": drv,
                "value": max_speed,
                "pos": int(results.loc[results['Abbreviation'] == drv, 'Position'].iloc[0])
            })

            # Métrica 2: Brake Efficiency
            # Calculamos la desaceleración media durante el frenado activo
            tel['DeltaSpeed'] = tel['Speed'].diff()
            braking = tel[tel['Brake'] == True].copy()
            
            if not braking.empty:
                # Deceleración media (km/h por muestra)
                avg_decel = abs(braking['DeltaSpeed'].mean())
                # Escala arbitraria para visualización (0-10)
                brake_score = round(min(avg_decel * 10, 10), 2)
            else:
                brake_score = 0

            metric2_data.append({
                "driver": drv,
                "value": brake_score,
                "pos": int(results.loc[results['Abbreviation'] == drv, 'Position'].iloc[0])
            })

        except Exception as e:
            print(f"Error con {drv}: {e}")

    # Exportar JSONs agregados (muy pequeños, <10KB cada uno)
    with open(os.path.join(DATA_DIR, 'metrica1.json'), 'w', encoding='utf-8') as f:
        json.dump(metric1_data, f, indent=4, ensure_ascii=False)
        
    with open(os.path.join(DATA_DIR, 'metrica2.json'), 'w', encoding='utf-8') as f:
        json.dump(metric2_data, f, indent=4, ensure_ascii=False)

    print(f"Exportación exitosa. JSONs generados en {DATA_DIR}")

if __name__ == "__main__":
    extract_all_data()
