from requests_html import HTMLSession
from datetime import datetime, timedelta
import configparser
import logging
import fileinput
import time
import random


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
        self.ctime = datetime.strptime(datetime.strftime(datetime.today(), "%B %d, %Y, %I:%M:%S %p"), "%B %d, %Y, %I:%M:%S %p")
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
        self, topic_id, message
    ):  # Replies to a given topic number with a specified message
        reply_uri = "https://bitcointalk.org/index.php?action=post;topic={}.0".format(
            topic_id
        )
        reply_uri_2 = "https://bitcointalk.org/index.php?action=post2;topic={}.0".format(
            topic_id
        )
        resp = self.session.get(reply_uri)
        data = {
            "topic": resp.html.xpath("//input[@name='topic']/@value"),
            "subject": resp.html.xpath("//input[@name='subject']/@value"),
            "message": message,
            "sc": resp.html.xpath("//input[@name='sc']/@value"),
            "seqnum": resp.html.xpath("//input[@name='seqnum']/@value"),
        }  # Required POST data for topic reply
        self.logger.info("Attempting to reply to TID: {}".format(topic_id))
        r = self.session.post(reply_uri_2, data=data)
        assert not r.html.xpath("//tr[@id='errors']")
        r = self.session.get("https://bitcointalk.org/index.php?action=profile;sa=showPosts")
        del_link = r.html.xpath("//span[@class='middletext']/a/@href")[3]
        # Getting deletion link via profile page (latest post)
        self.logger.info("Success, your post will now be scheduled for deletion.")
        with open("scheduled.txt", "a+") as f:  # Scheduling deletions in file
            f.write("{} | {}".format(self.ctime.strftime("%B %d, %Y, %I:%M:%S %p"), del_link))
            self.logger.info("Post successfully scheduled!")
        return

    def get_last_reply(self, topic):  # Get's timestamp of last post on a topic
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
        with fileinput.FileInput("scheduled.txt", inplace=True) as file:
            self.logger.info("Checking scheduled deletions")
            for post in [line.split("|") for line in file]:  # Parsing scheduled posts
                self.logger.info("Checking for scheduled posts that are 24 hours or older.")
                if datetime.strptime(post[0], "%B %d, %Y, %I:%M:%S %p") + timedelta(hours=24):
                    self.logger.info("Attempting to delete post: {}".format(post[1]))
                    self.delete(post[1])
                    post.replace("|".join([post[0], post[1]]), "")
                    self.logger.info("Post successfully deleted and removed from the schedule.")
        self.logger.info("Queueing {} topics.".format(len(topics.split(","))))
        while True:  # Loop through topics, getting last reply time to either pass or post on the topic
            for topic in topics.split(","):
                self.logger.info("Checking last reply time for {}".format(topic))
                ctime = datetime.strptime(
                    datetime.today().strftime("%B %d, %Y, %I:%M:%S %p"),
                    "%B %d, %Y, %I:%M:%S %p",
                )
                if ctime > (
                        self.get_last_reply(topic) + timedelta(hours=24)
                ):  # Checking if last reply was more than 24 hours ago
                    self.logger.info("Last reply more than 24 hours ago, replying...")
                    self.reply(topic, random.choice(messages.split("|")))
                else:
                    self.logger.info("Last reply less than 24 hours ago, do nothing.")
            self.logger.info("Sleeping for {} seconds".format(interval))
            time.sleep(int(interval))

    def delete(self, link):  # Was able to delete posts via link just using a GET request
        self.session.get(link)
        return self.logger.info("Post successfully deleted.")


if __name__ == "__main__":
    AutoReply()
