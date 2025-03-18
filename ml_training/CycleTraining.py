import pandas as pd
from prophet import Prophet

import pickle

from ml_training.Parser import get_data_from_NASA


def training(longitude, latitude, city, path = '') -> list:
    df = get_data_from_NASA(start="20110101", end="20231231", longitude=longitude, latitude=latitude)

    df_prophet = pd.DataFrame({
        'ds': df['date'],
        'y': df['irradiance']
    })

    model = Prophet(yearly_seasonality=True, daily_seasonality=False)
    model.fit(df_prophet)
    if path:
        if path.endswith('/'):
            path= path.removesuffix('/')
        path += f'/{round(longitude, 2)}-{round(latitude, 2)}-{city}_prophet_model.pkl'
    else:
        path = f'api_v1/energy/ml_models/{round(longitude, 2)}-{round(latitude, 2)}-{city}_prophet_model.pkl'
    with open(path, 'wb') as f:
        pickle.dump(model, f)
        #print(f"Модель {city} готова.")
    return [longitude,latitude,city]



if __name__ == "__main__":
    cities = [
        [-74.0060, 40.7128, "New York"],
        [-118.2437, 34.0522, "Los Angeles"],
        [-87.6298, 41.8781, "Chicago"],
        [-95.3698, 29.7604, "Houston"],
        [-112.0740, 33.4484, "Phoenix"],
        [-75.1652, 39.9526, "Philadelphia"],
        [-98.4936, 29.4241, "San Antonio"],
        [-117.1611, 32.7157, "San Diego"],
        [-96.7970, 32.7767, "Dallas"],
        [-121.8863, 37.3382, "San Jose"],
        [-0.1278, 51.5074, "London"],
        [2.3522, 48.8566, "Paris"],
        [13.4050, 52.5200, "Berlin"],
        [-3.7038, 40.4168, "Madrid"],
        [12.4964, 41.9028, "Rome"],
        [23.7275, 37.9838, "Athens"],
        [28.9784, 41.0082, "Istanbul"],
        [-9.1393, 38.7223, "Lisbon"],
        [139.6917, 35.6895, "Tokyo"],
        [135.5023, 34.6937, "Osaka"],
        [126.9780, 37.5665, "Seoul"],
        [116.4074, 39.9042, "Beijing"],
        [121.4737, 31.2304, "Shanghai"],
        [114.1095, 22.3964, "Hong Kong"],
        [103.8198, 1.3521, "Singapore"],
        [72.8777, 19.0760, "Mumbai"],
        [77.1025, 28.7041, "Delhi"],
        [77.5946, 12.9716, "Bangalore"],
        [18.4241, -33.9249, "Cape Town"],
        [28.0473, -26.2041, "Johannesburg"],
        [151.2093, -33.8688, "Sydney"],
        [144.9631, -37.8136, "Melbourne"],
        [174.7633, -36.8485, "Auckland"],
        [-79.3832, 43.6532, "Toronto"],
        [-123.1207, 49.2827, "Vancouver"],
        [-99.1332, 19.4326, "Mexico City"],
        [-58.3816, -34.6037, "Buenos Aires"],
        [-46.6333, -23.5505, "São Paulo"],
        [-43.1729, -22.9068, "Rio de Janeiro"],
        [-77.0428, -12.0464, "Lima"],
        [-70.6693, -33.4489, "Santiago"],
        [31.2357, 30.0444, "Cairo"],
        [36.8219, -1.2921, "Nairobi"],
        [55.2708, 25.2048, "Dubai"],
        [7.4474, 46.9480, "Bern"],
        [18.0686, 59.3293, "Stockholm"],
        [10.7522, 59.9139, "Oslo"]
    ]
    for i in cities:
        training(longitude=i[0], latitude=i[1], city=i[2], path='ml_models')
