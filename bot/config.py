import os


class Config:

    API_ID = int(os.environ.get("API_ID"))
    API_HASH = "96b46175824223a33737657ab943fd6a"
   
    BOT_TOKEN = "5410320498:AAGAPfA_Wnl4ZQRpCIWhxQR008O97_aIf7I"
    SESSION_NAME =  ":memory:"
    LOG_CHANNEL = -1001557165553
    DATABASE_URL = os.environ.get("DATABASE_URL")
    AUTH_USERS = 1425489930
    MAX_PROCESSES_PER_USER = 2
    MAX_TRIM_DURATION = 600
    TRACK_CHANNEL = False
    SLOW_SPEED_DELAY = 5
    HOST = ""
    TIMEOUT = 60 * 30
    DEBUG = bool(os.environ.get("DEBUG"))
    WORKER_COUNT = 20
    IAM_HEADER = os.environ.get("IAM_HEADER", "")

    COLORS = [
        "white",
        "black",
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "gold",
        "silver",
        "pink",
    ]
    FONT_SIZES_NAME = ["Small", "Medium", "Large"]
    FONT_SIZES = [30, 40, 50]
    POSITIONS = [
        "Top Left",
        "Top Center",
        "Top Right",
        "Center Left",
        "Centered",
        "Center Right",
        "Bottom Left",
        "Bottom Center",
        "Bottom Right",
    ]
