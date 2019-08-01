from requests_html import HTMLSession
from datetime import datetime, timedelta
import logging
import configparser
import time


class AutoReply:
    def __init__(self):
        # Script configuration
        config = configparser.ConfigParser()
        config.read("config.ini")
        logging.basicConfig(
            level=logging.INFO,
            filename="auto-reply.log",
            format="%(asctime)s: %(message)s",
            datefmt="[%I:%M %p]",
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("==SESSION STARTED==")
        self.logger.info(self.ctime.strftime("==[%m-%d-%Y]=="))
        self.session = self.login(**config["LOGIN_CREDENTIALS"])
        self.start(**config["AUTO_REPLY"])  # Starting program with specified targets

    def login(
        self, username, password, captcha_code
    ):  # Attempts login with specified credentials and returns session
        self.logger.info("Attempting login...")
        session = HTMLSession()
        login_uri = "https://bitcointalk.org/index.php?action=login2;ccode={}".format(
            captcha_code
        )
        r = session.post(login_uri, data={"user": username, "passwrd": password})
        assert r.status_code is 200 and "logout" in r.text, self.logger.error(
            "Login failed! Status Code: ".format(r.status_code)
        )  # Verifying that login was successful
        self.logger.info("Login successful!")
        return session

    def reply(
        self, topic, message
    ):  # Replies to a given topic number with a specified message
        reply_uri = "https://bitcointalk.org/index.php?action=post;topic={}.0".format(
            topic
        )
        reply_uri_2 = "https://bitcointalk.org/index.php?action=post2;topic={}.0".format(
            topic
        )
        resp = self.session.get(reply_uri)
        data = {
            "topic": resp.html.xpath("//input[@name='topic']/@value"),
            "subject": resp.html.xpath("//input[@name='subject']/@value"),
            "message": message,
            "sc": resp.html.xpath("//input[@name='sc']/@value"),
            "seqnum": resp.html.xpath("//input[@name='seqnum']/@value"),
        }  # Required POST data for topic reply
        self.logger.info("Replying to {}: \n{}\n".format(topic, message))
        self.session.post(reply_uri_2, data=data)
        return

    def get_last_replytime(self, topic):  # Get's timestamp of last post on a topic
        last_page = self.session.get(
            "https://bitcointalk.org/index.php?topic={}.999999999".format(topic)
        )
        post_time = last_page.html.xpath("(//div[@class='smalltext'])[last()]")[0].text
        bt_date = (
            "%B %d, %Y, %I:%M:%S %p"
        )  # Timestamp format: July 26, 2019, 04:23:34 PM
        if "Today" in post_time:
            post_time = post_time[post_time.index("Today at ") + 9 :]
            post_time = datetime.today().strftime("%B %d, %Y, ") + post_time
            datetime.strptime(post_time, bt_date)
        post_time = datetime.strptime(post_time, bt_date)
        return post_time

    def start(
        self, topics, messages, interval
    ):  # Start monitoring topics on a given interval
        self.logger.info("Monitoring started.")
        self.logger.info("Queueing {} topics.".format(len(topics.split(","))))
        while True:
            for topic in topics.split(","):
                self.logger.info("Checking last reply time for {}".format(topic))
                ctime = datetime.strptime(
                    datetime.today().strftime("%B %d, %Y, %I:%M:%S %p"),
                    "%B %d, %Y, %I:%M:%S %p",
                )
                if ctime > (
                    self.get_last_replytime(topic) + timedelta(hours=24)
                ):  # Checking if last reply was more than 24 hours ago
                    self.logger.info("Last reply more than 24 hours ago, replying...")
                    self.reply(topic, random.choice(messages.split("|")))
                else:
                    self.logger.info("Last reply less than 24 hours ago, do nothing.")
            self.logger.info("Sleeping for {} seconds".format(interval))
            time.sleep(int(interval))


if __name__ == "__main__":
    AutoReply()
