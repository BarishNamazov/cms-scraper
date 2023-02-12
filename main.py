import typer
from dotenv import dotenv_values
from cms_scraper import CmsSession

# app = typer.Typer()


# @app.command()
# def say_hello(name: str):
#     print(f"Hello {name}")


# @app.command()
# def say_bye(name: str):
#     print(f"Bye {name}")


if __name__ == "__main__":
    config = dotenv_values(".env")
    cs = CmsSession(config["URL"], config["USERNAME"], config["PASSWORD"])
    # print(cs.get_contests(include={"config", "ranking"}))
    cs.get_tasks(download=True)
    # print(cs.get_contest_configuration("1"))
    # print(cs.get_ranking("1"))
    # app()
