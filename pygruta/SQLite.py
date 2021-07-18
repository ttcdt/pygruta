#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

#   Gruta source SQLite

import base64
import sqlite3

from pygruta.base import Gruta


class SQLite(Gruta):
    def __init__(self, path):
        self.path = path

        self.db = sqlite3.connect(self.path)

        # init the base class
        super().__init__()

    def _flush(self):

        self.db.commit()

    def _close(self):

        self.db.commit()
        self.db.close()

    def id(self):
        return "SQLite (%s)" % self.path


    def _load_object(self, table, object, cond, tup):
        # generic object loading
        cur = self.db.cursor()

        cols = []

        for f in object.fields:
            cols.append(f)

        sql = "SELECT " + ", ".join(cols) + " FROM " + table + " WHERE " + cond

        cur.execute(sql, tup)
        res = cur.fetchall()

        if len(res):
            i = 0
            res = res[0]
            for f in object.fields:
                object.set(f, res[i])
                i += 1

            res = object
        else:
            res = None

        return res


    def _save_object(self, table, object, data=None):
        # generic object insertion into table
        cur = self.db.cursor()

        cols = []
        mrks = []
        vals = []

        if data is None:
            data = object.data

        for f in object.fields:
            cols.append(f)
            mrks.append("?")

            v = data.get(f)
            if v is None:
                v = ""
            else:
                v = str(v)

            vals.append(v)

        sql = "REPLACE INTO " + table + " (" + ", ".join(cols) + ") VALUES (" + ", ".join(mrks) + ")"

        cur.execute(sql, vals)

        return object


    # TOPICS

    def _load_topic(self, topic):

        return self._load_object("topics", topic, "id = ?", [topic.get("id")])

    def _save_topic(self, topic):

        return self._save_object("topics", topic)

    def topics(self, private=False):

        cur = self.db.cursor()

        if private is True:
            sql = "SELECT id FROM topics WHERE internal != '1'"
        else:
            sql = "SELECT id FROM topics"

        for line in cur.execute(sql):
            yield line[0]


    # STORIES

    def _load_story(self, story):

        ret = self._load_object("stories", story, "topic_id = ? AND id = ?",
            [story.get("topic_id"), story.get("id")])

        if ret is not None:
            story.set("tags", story.get("tags").split(","))

        return ret

    def _save_story(self, story):

        # create a copy of the data
        data = {}

        for f in story.fields:
            v = story.get(f)

            if f == "tags":
                v = ",".join(v)

            data[f] = v

        ret = self._save_object("stories", story, data)

        if ret is not None:
            topic_id = story.get("topic_id")
            id       = story.get("id")

            # delete tags
            cur = self.db.cursor()
            cur.execute("DELETE FROM tags WHERE topic_id = ? and id = ?", [topic_id, id])

            # insert all tags
            for tag in story.get("tags"):
                cur.execute("INSERT INTO tags (topic_id, id, tag) VALUES (?, ?, ?)", [
                    topic_id, id, tag])

        return ret

    def _delete_story(self, story):

        cur = self.db.cursor()
        sql = "DELETE FROM stories WHERE topic_id = ? AND id = ?"

        cur.execute(sql, [story.get("topic_id"), story.get("id")])

        return None

    def stories(self, topic_id):

        cur = self.db.cursor()
        sql = "SELECT id FROM stories WHERE topic_id = ?"

        for line in cur.execute(sql, [topic_id]):
            yield line[0]


    # USERS

    def _load_user(self, user):

        return self._load_object("users", user, "id = ?", [user.get("id")])

    def _save_user(self, user):

        return self._save_object("users", user)

    def users(self, private=False):

        cur = self.db.cursor()

        if private is True:
            sql = "SELECT id FROM users WHERE xdate = '' OR xdate > ?"
            val = (self.today())
        else:
            sql = "SELECT id FROM users"
            val = ()

        for line in cur.execute(sql, val):
            yield line[0]



    # FOLLOWERS

    def _load_follower(self, follower):

        return self._load_object("followers", follower, "id = ?", [id])

    def _save_follower(self, follower):

        return self._save_object("followers", follower)
        pass

    def followers(self, user_id):

        cur = self.db.cursor()
        sql = "SELECT id FROM followers WHERE user_id = ?"

        for line in cur.execute(sql, [user_id]):
            yield line[0]

    def delete_follower(self, follower):

        cur = self.db.cursor()
        sql = "DELETE FROM followers WHERE user_id = ? AND id = ?"

        cur.execute(sql, [follower.get("user_id"), follower.get("id")])



    # TEMPLATES

    def template(self, id):

        cur = self.db.cursor()
        sql = "SELECT content FROM templates where id = ?";

        try:
            cur.execute(sql, [id])
            content = cur.fetchall()[0][0]
        except:
            content = ""

        return content


    def save_template(self, id, content):

        cur = self.db.cursor()
        sql = "REPLACE INTO templates (id, content) VALUES (?, ?)"
        cur.execute(sql, (id, content))


    def templates(self):

        cur = self.db.cursor()
        sql = "SELECT id FROM templates"

        for line in cur.execute(sql):
            yield line[0]


    # IMAGES

    def image(self, id):

        cur = self.db.cursor()
        sql = "SELECT content FROM images where id = ?";

        try:
            cur.execute(sql, [id])
            content = cur.fetchall()[0][0]

            # convert from base64 to binary
            content = base64.b64decode(content)
        except:
            content = ""

        return content


    def save_image(self, id, content):

        ok = False

        if self.valid_image_id(id):
            # convert to base64
            content = base64.b64encode(content).decode()

            cur = self.db.cursor()
            sql = "REPLACE INTO images (id, content) VALUES (?, ?)"
            cur.execute(sql, (id, content))


    def images(self):

        cur = self.db.cursor()
        sql = "SELECT id FROM images"

        for line in cur.execute(sql):
            yield line[0]


    # create

    def _create(self):

        cur = self.db.cursor()

        o = self.new_topic()
        sql = "CREATE TABLE topics (" + ", ".join(o.fields) + ", PRIMARY KEY (id))"
        cur.execute(sql)

        o = self.new_story()
        sql = "CREATE TABLE stories (" + ", ".join(o.fields) + ", PRIMARY KEY (topic_id, id))"
        cur.execute(sql)

        o = self.new_user()
        sql = "CREATE TABLE users (" + ", ".join(o.fields) + ", PRIMARY KEY (id))"
        cur.execute(sql)

        o = self.new_follower()
        sql = "CREATE TABLE followers (" + ", ".join(o.fields) + ", PRIMARY KEY (user_id, id))"
        cur.execute(sql)

        cur.execute("CREATE TABLE templates (id, content, PRIMARY KEY (id))")
        cur.execute("CREATE TABLE images (id, content, PRIMARY KEY (id))")
        cur.execute("CREATE TABLE tags (id, topic_id, tag)")

        cur.execute("CREATE INDEX stories_by_date ON stories (date)")
        cur.execute("CREATE INDEX stories_by_title ON stories (title)")
        cur.execute("CREATE INDEX tags_by_tag ON tags (tag)")
        cur.execute("CREATE INDEX tags_by_fullid ON tags (topic_id, id)")

        # finally commit
        self.db.commit()


    # STORY SET

    def story_set(self, topics=None, tags=None, content=None, order="date",
                  d_from=None, d_to=None, num=None, offset=0, private=False,
                  timeout=None):

        cond  = []
        args  = []

        if tags is not None:
            sql = "SELECT DISTINCT tags.topic_id, tags.id, date, tags, udate FROM tags, stories"

            cond.append("tags.topic_id = stories.topic_id")
            cond.append("tags.id = stories.id")

            a = []
            for t in tags:
                a.append("tag = ?")
                args.append(t)

            cond.append("(" + " OR ".join(a) + ")")
        else:
            sql = "SELECT topic_id, id, date, tags, udate FROM stories"

        if topics is not None:
            a = []
            for t in topics:
                a.append("stories.topic_id = ?")
                args.append(t)

            cond.append("(" + " OR ".join(a) + ")")

        if private is False:
            cond.append("date <= ?")
            args.append(self.today())

            cond.append("(udate == '' OR udate > ?)")
            args.append(self.today())

        if d_from is not None:
            cond.append("date > ?")
            args.append(d_from)

        if d_to is not None:
            cond.append("date < ?")
            args.append(d_to)

        if content is not None:
            cond.append("content like ?")
            args.append("%" + content + "%")

        if len(cond):
            sql += " WHERE " + " AND ".join(cond)

        if tags is not None:
            sql += " GROUP BY tags.topic_id, tags.id HAVING count(tags.id) = ?"
            args.append(len(tags))

        if order == "date":
            sql += " ORDER by date DESC"
        else:
            sql += " ORDER by " + order

        if num is not None:
            sql += " LIMIT ?"
            args.append(num)

            if offset:
                sql += " OFFSET ?"
                args.append(offset)

        self.log("DEBUG", "SQLite.story_set (sql): " + sql)
        self.log("DEBUG", "SQLite.story_set (args): " + str(args))

        cur = self.db.cursor()
        for line in cur.execute(sql, args):
            (s_topic, s_id, s_date, s_tags, s_udate) = line

            s_tags = s_tags.split(",")

            yield (s_topic, s_id, s_date, s_tags, s_udate)
