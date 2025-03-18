import requests
import pandas as pd


# Параметры запроса:
# - parameters: параметры, запрашиваемые для анализа. Здесь:
#   ALLSKY_SFC_SW_DWN – суммарное значение падающего солнечного излучения на поверхности,
#   T2M – температура воздуха на высоте 2 м,
#   WS10M – скорость ветра на высоте 10 м,
#   RH2M – относительная влажность на высоте 2 м.
# - community: "RE" означает, что данные ориентированы на возобновляемые источники энергии.
# - latitude и longitude: координаты точки (в данном примере Москва).
# - start и end: начальная и конечная даты в формате YYYYMMDD.
# - format: формат ответа (JSON).
def get_data_from_NASA(start="20000101",end="20201231", longitude = 37.62, latitude = 55.75):
    # URL для получения ежедневных данных по заданной точке
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"

    params = {
        "parameters": "ALLSKY_SFC_SW_DWN",
        # Добавлю потом, пока солнце
        # "parameters": "ALLSKY_SFC_SW_DWN,T2M,WS10M,RH2M",
        "community": "RE",
        "longitude": longitude,
        "latitude": latitude,
        "start": start,
        "end": end,
        "format": "JSON"
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        #print("Данные NASA POWER для Центрального федерального округа (Москва):")

    else:
        print("Ошибка запроса:", response.status_code)
        print(response.text)

    irradiance = data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
    # Добавлю потом, пока солнце
    # temperature = data["properties"]["parameter"]["T2M"]
    # wind_speed = data["properties"]["parameter"]["WS10M"]
    # humidity = data["properties"]["parameter"]["RH2M"]

    # Преобразование словаря в DataFrame
    df = pd.DataFrame({
        "date": pd.to_datetime(list(irradiance.keys()), format="%Y%m%d"),
        "irradiance": list(irradiance.values()),
        # Добавлю потом, пока солнце
        # "temperature": list(temperature.values()),
        # "wind_speed": list(wind_speed.values()),
        # "humidity": list(humidity.values())
    })
    df.sort_values("date", inplace=True)
    return df


if __name__ == "__main__":
    df = get_data_from_NASA(start="19810101", end="20231231")
    print(df)
