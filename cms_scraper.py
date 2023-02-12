import requests
from bs4 import BeautifulSoup
import urllib.parse
import json
import os
import csv

urljoin = urllib.parse.urljoin


def get_field_value(field):
    val = (
        field.get("value")
        if field.name == "input"
        else field.text
        if field.name == "textarea"
        else "NONE"
    )
    if val == "NONE":
        try:
            val = field.find("option", {"selected": True}).text
        except:
            pass
    return val


class CmsSession:
    def __init__(self, url, username, password):
        """Create a CMS Admin session, given the URL for admin dashboard and username and password for any enabled admin"""
        self.session = requests.Session()
        self.url = url
        self.login(username, password)

    def get_soup(self, url):
        r = self.session.get(url)
        r.encoding = "utf-8"
        return BeautifulSoup(r.text, "html.parser")

    def login(self, username, password):
        """Logs in to the CMS Admin Dashboard"""

        login_url = urllib.parse.urljoin(self.url, "login")
        self.xsrf_token = self.get_soup(login_url).select_one('input[name="_xsrf"]')[
            "value"
        ]
        self.session.post(
            login_url,
            data={
                "_xsrf": self.xsrf_token,
                "username": username,
                "password": password,
                "next": "/",
            },
        )

    def get_ranking(self, contest_id: str):
        """Gets CSV ranking of the contest"""
        ranking_url = urljoin(self.url, f"contest/{contest_id}/ranking/csv")
        r = self.session.get(ranking_url)
        r.encoding = "utf-8"
        return r.text

    def get_contest_configuration(self, contest_id: str):
        """Gets data about one contest"""

        config = {}

        contest_url = urljoin(self.url, f"contest/{contest_id}")
        soup = self.get_soup(contest_url).select_one("table")

        fields = soup.select("input, textarea, select")
        for field in fields:
            config[field["name"]] = get_field_value(field)

        return config

    def get_contests(self, include: set[str] = set(), files=True):
        """Gets list of contests"""

        contests = []

        contests_url = urljoin(self.url, "contests")
        rows = self.get_soup(contests_url).select("tbody tr")
        for row in rows:
            url_td, description_td = row.select("td")[1:]
            url_a = url_td.select_one("a")
            contest_id, contest_name = url_a["href"].split("/")[-1], url_a.text
            contest_description = description_td.text

            contest = {
                "id": contest_id,
                "name": contest_name,
                "description": contest_description,
            }

            if "config" in include:
                contest |= {"config": self.get_contest_configuration(contest_id)}

            if "ranking" in include:
                contest |= {"ranking": self.get_ranking(contest_id)}

            contests.append(contest)
            if files:
                filename = f"contests/{contest_id.zfill(3)}.json"
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(contest, f, indent=2, ensure_ascii=False)

        contests.sort(key=lambda contest: int(contest["id"]))
        os.makedirs(os.path.dirname("contests/all_contest.json"), exist_ok=True)
        with open("contests/all_contest.json", "w", encoding="utf-8") as f:
            json.dump(contests, f, indent=2, ensure_ascii=False)

        return contests

    def get_task_data(self, task_id):
        task_url = urljoin(self.url, f"task/{task_id}")
        soup = self.get_soup(task_url)

        config = {}
        fields = soup.select("input, textarea, select")
        for field in fields:
            if not field.has_attr("name"):
                continue
            config[field["name"]] = get_field_value(field)

        links = soup.select("a")
        statements = []
        checker = None
        for link in links:
            if not link.has_attr("href"):
                continue
            href, text = str(link["href"]), link.text
            if "statement.pdf" in href:
                statement_url = urljoin(task_url, href)
                statement_binary = self.session.get(statement_url).content
                clean_name = text.lower().replace('"', "").split()
                statement_name = "_".join([clean_name[0], clean_name[-1]]) + ".pdf"
                statements.append({"name": statement_name, "binary": statement_binary})

            if "testcases/download" in href:
                testcases_url = urljoin(task_url, href)
                testcases_zip = self.session.post(
                    testcases_url,
                    data={
                        "_xsrf": self.xsrf_token,
                        "zip_filename": "testcases.zip",
                        "input_template": "*.in",
                        "output_template": "*.out",
                    },
                ).content

            if "/checker" in href:
                checker_url = urljoin(task_url, href)
                checker = self.session.get(checker_url).content

        return {
            "config": config,
            "statements": statements,
            "testcases": testcases_zip,
            "checker": checker,
        }

    def get_tasks(self, download=False):
        """Gets list of tasks"""

        tasks = []

        contests_url = urljoin(self.url, "tasks")
        rows = self.get_soup(contests_url).select("tbody tr")
        for row in rows:
            url_td, title_td = row.select("td")[1:]
            url_a = url_td.select_one("a")
            task_id, task_name = url_a["href"].split("/")[-1], url_a.text
            task_title = title_td.text

            contest = {
                "id": task_id,
                "name": task_name,
                "title": task_title,
            }

            tasks.append(contest)
            if download:
                directory = f"tasks/{task_id.zfill(3)}_{task_name}/"
                config_file = os.path.join(directory, "config.json")
                statements_directory = os.path.join(directory, "statements/")

                os.makedirs(os.path.dirname(directory), exist_ok=True)
                os.makedirs(os.path.dirname(statements_directory), exist_ok=True)

                task_data = self.get_task_data(task_id)
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(task_data["config"], f, indent=2, ensure_ascii=False)

                statements = task_data["statements"]
                for statement in statements:
                    with open(statements_directory + statement["name"], "wb") as f:
                        f.write(statement["binary"])

                with open(directory + "testcases.zip", "wb") as f:
                    f.write(task_data["testcases"])

                if task_data["checker"] is not None:
                    with open(directory + "checker", "wb") as f:
                        f.write(task_data["checker"])

            # break

        tasks.sort(key=lambda contest: int(contest["id"]))
        os.makedirs(os.path.dirname("tasks/all_tasks.json"), exist_ok=True)
        with open("tasks/all_tasks.json", "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)

        return tasks


if __name__ == "__main__":
    cs = CmsSession()
