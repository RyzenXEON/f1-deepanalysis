from flask import Flask, render_template, request, jsonify
import fastf1
import numpy as np
from datetime import datetime

app = Flask(__name__)

fastf1.Cache.enable_cache('cache')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/circuits', methods=['GET'])
def get_circuits():
    year = request.args.get('year', default=2024, type=int)
    
    schedule = fastf1.get_event_schedule(year)
    circuits = [
        {
            'name': event['EventName'],
            'round': event['RoundNumber'],
            'circuit': event['OfficialEventName']
        }
        for _, event in schedule.iterrows()
    ]
    
    return jsonify(circuits)

@app.route('/api/years', methods=['GET'])
def get_years():
    # Return available years (FastF1 has reliable data from 2018)
    current_year = datetime.now().year
    years = list(range(2018, current_year + 1))
    return jsonify(years)

@app.route('/api/telemetry', methods=['GET'])
def get_telemetry():
    driver1 = request.args.get('driver1')
    driver2 = request.args.get('driver2')
    session = request.args.get('session')
    year = request.args.get('year', default=2024, type=int)
    circuit = request.args.get('circuit')
    
    # Load the session
    race = fastf1.get_session(year, circuit, session)
    race.load()
    
    # Get fastest laps for both drivers
    lap_driver1 = race.laps.pick_drivers(driver1).pick_fastest()
    lap_driver2 = race.laps.pick_drivers(driver2).pick_fastest()
    
    tel_driver1 = lap_driver1.get_telemetry()
    tel_driver2 = lap_driver2.get_telemetry()
    
    sectors_driver1 = {
        'sector1': lap_driver1['Sector1Time'].total_seconds(),
        'sector2': lap_driver1['Sector2Time'].total_seconds(),
        'sector3': lap_driver1['Sector3Time'].total_seconds(),
    }
    sectors_driver2 = {
        'sector1': lap_driver2['Sector1Time'].total_seconds(),
        'sector2': lap_driver2['Sector2Time'].total_seconds(),
        'sector3': lap_driver2['Sector3Time'].total_seconds(),
    }
    
    # Calculate mini sectors (25 meter segments for more detail)
    num_minisectors = 25  # Increased for more detailed visualization
    total_distance = max(tel_driver1['Distance'].max(), tel_driver2['Distance'].max())
    minisector_length = total_distance / num_minisectors
    
    # Create mini sector array
    tel_driver1['Minisector'] = tel_driver1['Distance'] // minisector_length
    tel_driver2['Minisector'] = tel_driver2['Distance'] // minisector_length
    
    # Compare mini sector times
    minisector_colors = []
    for i in range(num_minisectors):
        time1 = tel_driver1[tel_driver1['Minisector'] == i]['Time'].diff().sum()
        time2 = tel_driver2[tel_driver2['Minisector'] == i]['Time'].diff().sum()
        if time1 < time2:
            minisector_colors.append('red')  # Driver 1 faster
        else:
            minisector_colors.append('blue')  # Driver 2 faster
            
    telemetry_data = {
        'driver1': {
            'throttle': list(tel_driver1['Throttle']),
            'brake': list(tel_driver1['Brake']),
            'speed': list(tel_driver1['Speed']),
            'distance': list(tel_driver1['Distance']),
            'x': list(tel_driver1['X']),
            'y': list(tel_driver1['Y']),
            'time': list(tel_driver1['Time'].dt.total_seconds()),
            'gear': list(tel_driver1['nGear'].fillna(0).astype(int)),
            'sectors': sectors_driver1
        },
        'driver2': {
            'throttle': list(tel_driver2['Throttle']),
            'brake': list(tel_driver2['Brake']),
            'speed': list(tel_driver2['Speed']),
            'distance': list(tel_driver2['Distance']),
            'x': list(tel_driver2['X']),
            'y': list(tel_driver2['Y']),
            'time': list(tel_driver2['Time'].dt.total_seconds()),
            'gear': list(tel_driver2['nGear'].fillna(0).astype(int)),
            'sectors': sectors_driver2
        },
        'minisectors': {
            'colors': minisector_colors,
            'points': list(range(num_minisectors))
        },
        'circuit_info': {
            'name': circuit,
            'year': year
        }
    }
    
    return jsonify(telemetry_data)

if __name__ == '__main__':
    app.run(debug=True)