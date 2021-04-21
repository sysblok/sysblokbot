from datetime import datetime


TIME_FORMAT = '%d.%m.%Y %H:%M:%S'


def convert_excel_datetime_to_string(excel_datetime: float) -> str:
    # https://stackoverflow.com/questions/981655/how-to-represent-a-datetime-in-excel
    seconds = (excel_datetime - 25569) * 86400.0
    return datetime.utcfromtimestamp(seconds).strftime(TIME_FORMAT)
