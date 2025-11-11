import logging, pathlib
def setup_logging():
    pathlib.Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        filename="logs/app.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
