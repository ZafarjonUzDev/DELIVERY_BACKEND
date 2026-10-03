import math


def calculate_haversine_distance(
    lat1: float, 
    lon1: float, 
    lat2: float, 
    lon2: float
) -> float:
    """
    Ikki GPS koordinata (Latitude, Longitude) orasidagi masofani 
    Haversine formulasi bo'yicha kilometrda (km) hisoblab beradi.
    
    :param lat1: 1-nuqta (masalan, Kafe) kengligi
    :param lon1: 1-nuqta (masalan, Kafe) uzunligi
    :param lat2: 2-nuqta (masalan, Mijoz) kengligi
    :param lon2: 2-nuqta (masalan, Mijoz) uzunligi
    :return: Masofa (kilometrlarda)
    """
    # Yer radiusi (kilometrlarda)
    EARTH_RADIUS_KM = 6371.0

    # Graduslarni radianga o'tkazamiz
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(d_lat / 2) ** 2 +
        math.cos(math.radians(lat1)) * 
        math.cos(math.radians(lat2)) * 
        math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = EARTH_RADIUS_KM * c
    return round(distance, 2)